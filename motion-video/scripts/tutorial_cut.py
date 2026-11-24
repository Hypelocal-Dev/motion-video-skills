#!/usr/bin/env python3
"""Cut a long screen recording into a tight tutorial "spine" from a JSON cut list.

The spine is the edited picture and voice. Graphics go on top of it later
(tutorial_gen.py), so every graphic time is spine time.

Subcommands (PROJECT is the tutorial folder that holds work/cut.json):

  silences PROJECT          find pauses in the source voice -> work/silences.json
  build PROJECT             render edit/assets/spine.mp4 and work/spine_map.json
  sweep VIDEO [--every 3]   contact sheets for a privacy sweep (one tile per N seconds)
  find PROJECT PHRASE...    spine time of each phrase, from work/spine_words.json
  map PROJECT SECONDS...    raw-recording seconds -> spine seconds

work/cut.json:
  {
    "source": "../footage/recording.mp4",       # relative to work/
    "crop": "auto",                             # or [w, h, x, y]; auto = centered 16:9
    "segments": [
      {"kind": "speech", "from": 0.0, "to": 11.5, "tag": "intro"},
      {"kind": "hold",   "from": 56.4, "dur": 2.0, "tag": "ch1"},
      {"kind": "speed",  "from": 452.6, "to": 616.0, "rate": 14, "tag": "skip-1"}
    ]
  }

speech: plays at 1x with sound; pauses longer than tighten.min_gap are cut out.
hold:   muted footage under a full-screen card (chapter cards, end card).
speed:  muted and sped up (the agent or a render working). Keep rate 8-16.
Optional keys: "tighten": {"min_gap": 0.55, "pad": 0.14}, "level": true, "fps": 30.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from _audio import duration, require

LEVEL = ("highpass=f=70,acompressor=threshold=-22dB:ratio=3:attack=5:release=150:makeup=2,"
         "loudnorm=I=-14.5:TP=-1.5:LRA=11")


def paths(project: str) -> dict[str, str]:
    work = os.path.join(project, "work")
    return {
        "work": work,
        "cut": os.path.join(work, "cut.json"),
        "silences": os.path.join(work, "silences.json"),
        "map": os.path.join(work, "spine_map.json"),
        "words": os.path.join(work, "spine_words.json"),
        "spine": os.path.join(project, "edit", "assets", "spine.mp4"),
    }


def load_cut(project: str) -> dict:
    p = paths(project)["cut"]
    if not os.path.exists(p):
        sys.exit(f"error: {p} not found. Write the cut list first (see the tutorial-edit skill).")
    cut = json.load(open(p))
    cut["source"] = os.path.normpath(os.path.join(paths(project)["work"], cut["source"]))
    return cut


def detect_silences(path: str, noise_db: float = -36, min_s: float = 0.45) -> list[list[float]]:
    require("ffmpeg")
    err = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", path, "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_s}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return [[round(a, 3), round(b, 3)] for a, b in zip(starts, ends)]


def cmd_silences(args: argparse.Namespace) -> None:
    cut = load_cut(args.project)
    sil = detect_silences(cut["source"])
    json.dump(sil, open(paths(args.project)["silences"], "w"))
    long_ones = [s for s in sil if s[1] - s[0] >= 8]
    print(f"{len(sil)} pauses, {sum(b - a for a, b in sil):.0f}s total. Pauses of 8s or more (agent working?):")
    for a, b in long_ones:
        print(f"  {a:8.1f} - {b:8.1f}  ({b - a:.0f}s)")


def crop_filter(cut: dict, src: str) -> str:
    crop = cut.get("crop", "auto")
    if crop == "auto":
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip().split(",")
        w, h = int(out[0]), int(out[1])
        if abs(w / h - 16 / 9) < 0.01:
            return "scale=1920:1080"
        if w / h < 16 / 9:  # too tall: trim top and bottom equally
            ch = round(w * 9 / 16 / 2) * 2
            return f"crop={w}:{ch}:0:{(h - ch) // 2},scale=1920:1080"
        cw = round(h * 16 / 9 / 2) * 2
        return f"crop={cw}:{h}:{(w - cw) // 2}:0,scale=1920:1080"
    w, h, x, y = crop
    return f"crop={w}:{h}:{x}:{y},scale=1920:1080"


def plan_pieces(cut: dict, silences: list[list[float]]) -> list[dict]:
    t = cut.get("tighten", {})
    min_gap, pad = t.get("min_gap", 0.55), t.get("pad", 0.14)
    fps = cut.get("fps", 30)

    def snap(x: float) -> float:
        return round(x * fps) / fps

    pieces = []
    for seg in cut["segments"]:
        kind, tag = seg["kind"], seg.get("tag", "")
        if kind == "speech":
            a, b = seg["from"], seg["to"]
            ranges, cur = [], a
            if seg.get("tighten", True):
                for s, e in silences:
                    if e - s < min_gap:
                        continue
                    cs, ce = max(s + pad, a), min(e - pad, b)
                    if ce - cs > 0.15:
                        if cs > cur:
                            ranges.append((cur, cs))
                        cur = max(cur, ce)
            ranges.append((cur, b))
            for x, y in ranges:
                if y - x >= 0.2:
                    pieces.append({"kind": "speech", "tag": tag, "src_start": snap(x), "src_end": snap(y), "rate": 1})
        elif kind == "speed":
            pieces.append({"kind": "speed", "tag": tag, "src_start": snap(seg["from"]), "src_end": snap(seg["to"]),
                           "rate": seg.get("rate", 12)})
        elif kind == "hold":
            pieces.append({"kind": "hold", "tag": tag, "src_start": snap(seg["from"]),
                           "src_end": snap(seg["from"] + seg["dur"]), "rate": 1})
        else:
            sys.exit(f"error: unknown segment kind {kind!r}")
    t0 = 0.0
    for i, p in enumerate(pieces):
        p["i"] = i
        p["dur"] = snap((p["src_end"] - p["src_start"]) / p["rate"])
        p["start"], p["end"] = round(t0, 3), round(t0 + p["dur"], 3)
        t0 += p["dur"]
    return pieces


def cmd_build(args: argparse.Namespace) -> None:
    require("ffmpeg")
    p = paths(args.project)
    cut = load_cut(args.project)
    if not os.path.exists(p["silences"]):
        json.dump(detect_silences(cut["source"]), open(p["silences"], "w"))
    pieces = plan_pieces(cut, json.load(open(p["silences"])))
    total = pieces[-1]["end"] if pieces else 0
    json.dump(pieces, open(p["map"], "w"), indent=1)
    by_tag: dict[str, list[float]] = {}
    for q in pieces:
        by_tag.setdefault(q["tag"], [q["start"], q["end"]])[1] = q["end"]
    for tag, (a, b) in by_tag.items():
        print(f"  {a:7.1f}-{b:7.1f}  {b - a:5.1f}s  {tag}")
    print(f"{len(pieces)} pieces, spine {total:.1f}s ({total / 60:.2f} min)")
    if args.dry:
        return
    vf = crop_filter(cut, cut["source"]) + f",fps={cut.get('fps', 30)},format=yuv420p"
    tmp = tempfile.mkdtemp(prefix="spine-")

    def render(q: dict) -> str:
        out = os.path.join(tmp, f"p{q['i']:04d}.mp4")
        a, b, dur = q["src_start"], q["src_end"], q["dur"]
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", cut["source"]]
        if q["kind"] == "speech":
            fades = f"aresample=48000,afade=t=in:d=0.02,afade=t=out:st={max(0, b - a - 0.03):.3f}:d=0.03"
            cmd += ["-vf", vf, "-af", fades,
                    "-ac", "2"]
        else:
            speed = f"setpts=PTS/{q['rate']}," if q["rate"] != 1 else ""
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
                    "-map", "0:v", "-map", "1:a", "-vf", speed + vf]
        cmd += ["-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-g", "30",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out]
        subprocess.run(cmd, check=True)
        return out

    with ThreadPoolExecutor(max(2, (os.cpu_count() or 4) // 2)) as ex:
        outs = list(ex.map(render, pieces))
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{o}'\n" for o in outs))
    os.makedirs(os.path.dirname(p["spine"]), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p"]
    if cut.get("level", True):
        cmd += ["-af", LEVEL]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", p["spine"]]
    subprocess.run(cmd, check=True)
    print(f"wrote {p['spine']} ({duration(p['spine']):.1f}s). Transcribe it next:")
    print(f"  npx hyperframes transcribe {p['spine']} -d {p['work']} && "
          f"python3 {os.path.abspath(__file__)} words {args.project}")


def cmd_words(args: argparse.Namespace) -> None:
    """Normalize HyperFrames' transcript.json into work/spine_words.json: [[start, end, text], ...]."""
    p = paths(args.project)
    src = os.path.join(p["work"], "transcript.json")
    data = json.load(open(src))
    words = data if isinstance(data, list) else data.get("words", [])
    out = [[round(w["start"], 2), round(w["end"], 2), w["text"].strip()] for w in words if w.get("text", "").strip()]
    json.dump(out, open(p["words"], "w"))
    print(f"{len(out)} words -> {p['words']}")


def cmd_find(args: argparse.Namespace) -> None:
    words = json.load(open(paths(args.project)["words"]))
    norm = [re.sub(r"\W", "", w[2].lower()) for w in words]
    for phrase in args.phrases:
        toks = [re.sub(r"\W", "", t.lower()) for t in phrase.split()]
        hits = [words[i][0] for i in range(len(norm) - len(toks) + 1) if norm[i:i + len(toks)] == toks]
        print(f"{phrase!r}: {hits}")


def cmd_map(args: argparse.Namespace) -> None:
    pieces = json.load(open(paths(args.project)["map"]))
    for t in args.seconds:
        hit = next((q for q in pieces if q["kind"] != "hold" and q["src_start"] <= t <= q["src_end"]), None)
        if hit:
            print(f"{t}: {hit['start'] + (t - hit['src_start']) / hit['rate']:.2f}  ({hit['tag']})")
        else:
            nxt = next((q for q in pieces if q["kind"] != "hold" and q["src_start"] > t), None)
            print(f"{t}: cut out" + (f"; next kept piece starts at spine {nxt['start']:.2f}" if nxt else ""))


def cmd_sweep(args: argparse.Namespace) -> None:
    require("ffmpeg")
    d = duration(args.video)
    per = args.cols * args.rows
    out_dir = args.out or os.path.splitext(args.video)[0] + "-sweep"
    os.makedirs(out_dir, exist_ok=True)
    sheets = math.ceil(d / args.every / per)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", args.video, "-vf",
                    f"fps=1/{args.every},scale=300:-1,tile={args.cols}x{args.rows}",
                    os.path.join(out_dir, "sheet-%02d.jpg")], check=True)
    for s in range(sheets):
        a = s * per * args.every
        print(f"sheet-{s + 1:02d}.jpg: {a:.0f}s to {min(d, a + per * args.every):.0f}s, "
              f"tile n (0-based, row-major) = {a:.0f} + n*{args.every}s")
    print(f"Look at every sheet for desktops, other apps, chats, passwords or other clients' work: {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("silences")
    s.add_argument("project")
    s.set_defaults(fn=cmd_silences)
    s = sub.add_parser("build")
    s.add_argument("project")
    s.add_argument("--dry", action="store_true", help="print the cut and length without rendering")
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser("words")
    s.add_argument("project")
    s.set_defaults(fn=cmd_words)
    s = sub.add_parser("find")
    s.add_argument("project")
    s.add_argument("phrases", nargs="+")
    s.set_defaults(fn=cmd_find)
    s = sub.add_parser("map")
    s.add_argument("project")
    s.add_argument("seconds", nargs="+", type=float)
    s.set_defaults(fn=cmd_map)
    s = sub.add_parser("sweep")
    s.add_argument("video")
    s.add_argument("--every", type=float, default=3)
    s.add_argument("--cols", type=int, default=8)
    s.add_argument("--rows", type=int, default=7)
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_sweep)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
