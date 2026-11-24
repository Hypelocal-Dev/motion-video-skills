#!/usr/bin/env python3
"""Helpers for picking clips out of a longer video.

  clips_find.py lines WORDS [--gap 0.6]
      Print the transcript as timed sentence lines, with pauses marked, so you can read
      a long video quickly and pick moments. WORDS is a word-timing JSON: HyperFrames'
      transcript.json ([{text, start, end}]) or tutorial_cut.py's spine_words.json.

  clips_find.py prep PROJECT
      For a tutorial-edit project: make sure the spine has current word timings
      (transcribes it when they're missing or older than the spine) and write a
      clips.json skeleton with the brand theme, caption names and privacy covers.

  clips_find.py frames CLIPS_JSON [--per 8 --cols 4 --width 640]
      Contact sheet per planned clip (start, middle, end and between) in clips/check/,
      so you can confirm each moment is on screen, framed and free of private screens
      before rendering.

Moment-finding signals adapted from clipify by Louise de Sadeleer (MIT License).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from _audio import require


def load_words(path: str) -> list[tuple[float, float, str]]:
    data = json.load(open(path))
    if isinstance(data, dict):
        data = data.get("words", [])
    out = []
    for w in data:
        if isinstance(w, list):
            out.append((float(w[0]), float(w[1]), str(w[2])))
        else:
            out.append((float(w["start"]), float(w["end"]), w["text"].strip()))
    return [w for w in out if w[2]]


def cmd_lines(a: argparse.Namespace) -> None:
    words = load_words(a.words)
    line, start, prev_end = [], None, None
    for s, e, t in words:
        gap = s - prev_end if prev_end is not None else 0
        if gap > a.gap and line:
            print(f"[{start:7.1f}] {' '.join(line)}")
            line, start = [], None
        if gap > 2:
            print(f"          (pause {gap:.1f}s)")
        if start is None:
            start = s
        line.append(t)
        prev_end = e
        if t.endswith((".", "?", "!")) and len(line) > 3:
            print(f"[{start:7.1f}] {' '.join(line)}")
            line, start = [], None
    if line:
        print(f"[{start:7.1f}] {' '.join(line)}")


def cmd_frames(a: argparse.Namespace) -> None:
    require("ffmpeg")
    spec = json.load(open(a.clips))
    base = os.path.dirname(os.path.abspath(a.clips))
    src = os.path.normpath(os.path.join(base, spec["source"]))
    out_dir = os.path.join(base, "clips", "check")
    os.makedirs(out_dir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    for c in spec["clips"]:
        n = max(2, a.per)
        times = [round(c["start"] + (c["end"] - c["start"]) * i / (n - 1), 2) for i in range(n)]
        times[-1] = round(c["end"] - 0.1, 2)
        out = os.path.join(out_dir, f"{c['name']}.png")
        subprocess.run(["python3", os.path.join(here, "contact_sheet.py"), src, "--times", ",".join(map(str, times)),
                        "--cols", str(min(n, a.cols)), "--width", str(a.width), "-o", out],
                       check=True, stdout=subprocess.DEVNULL)
        print(f"{c['name']}: {out}  ({c['start']}-{c['end']}s)")
    print("Look at each sheet: is the moment on screen, is the subject in frame, and is anything private showing?")


def transcribe(video: str, out_dir: str) -> str:
    """Word timings for VIDEO via HyperFrames, normalized to [[start, end, text], ...]."""
    os.makedirs(out_dir, exist_ok=True)
    version = os.environ.get("MV_HYPERFRAMES_VERSION", "latest")
    subprocess.run(["npx", "--yes", f"hyperframes@{version}", "transcribe", os.path.abspath(video), "-d", out_dir],
                   check=True, stdout=subprocess.DEVNULL)
    words = load_words(os.path.join(out_dir, "transcript.json"))
    path = os.path.join(out_dir, "spine_words.json")
    json.dump([[round(s, 2), round(e, 2), t] for s, e, t in words], open(path, "w"))
    return path


def cmd_prep(a: argparse.Namespace) -> None:
    """Get a tutorial-edit project ready to clip: fresh word timings and a clips.json skeleton."""
    proj = os.path.abspath(a.project)
    spine = os.path.join(proj, "edit", "assets", "spine.mp4")
    if not os.path.exists(spine):
        sys.exit(f"error: {spine} not found. For a plain video, write clips.json by hand (see clips_make.py --help).")
    words = os.path.join(proj, "work", "spine_words.json")
    if os.path.exists(words) and os.path.getmtime(words) >= os.path.getmtime(spine) and not a.retranscribe:
        print(f"word timings are current: {words}")
    else:
        # Stale words (the spine was re-cut after transcribing) put captions and cut points in the wrong place.
        why = "missing" if not os.path.exists(words) else "older than the spine"
        print(f"word timings {why}; transcribing the spine (a few minutes for a long video)...")
        words = transcribe(spine, os.path.join(proj, "work", "clips-src"))
        print(f"wrote {words}")
    out = os.path.join(proj, "clips.json")
    if os.path.exists(out) and not a.force:
        spec = json.load(open(out))
        rel = os.path.relpath(words, proj)
        if spec.get("words") != rel:  # keep the clips, point them at the fresh timings
            spec["words"] = rel
            json.dump(spec, open(out, "w"), indent=1, ensure_ascii=False)
            print(f"{out}: words now {rel}; everything else left as is")
        else:
            print(f"{out} already exists; left as is (--force to rewrite the skeleton)")
        return
    plan_path = os.path.join(proj, "work", "plan.json")
    plan = json.load(open(plan_path)) if os.path.exists(plan_path) else {}
    spec = {
        "source": "edit/assets/spine.mp4",
        "words": os.path.relpath(words, proj),
        "format": "9:16",
        "out": "clips",
        "captions": {"proper": plan.get("captions", {}).get("proper", {})},
        "covers": plan.get("covers", []),
        "clips": [],
    }
    if os.path.exists(os.path.join(proj, "brand", "theme.json")):
        spec["theme"] = "brand/theme.json"
    json.dump(spec, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {out}: {len(spec['covers'])} privacy covers, theme {'yes' if 'theme' in spec else 'none'}. "
          "Add the clips, then run the frame check.")
    if not plan:
        print("warning: no work/plan.json, so no privacy covers were copied. Sweep the clips by eye.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lines")
    s.add_argument("words")
    s.add_argument("--gap", type=float, default=0.6, help="pause (s) that ends a line")
    s.set_defaults(fn=cmd_lines)
    s = sub.add_parser("prep")
    s.add_argument("project", help="a tutorial-edit project folder")
    s.add_argument("--retranscribe", action="store_true", help="transcribe even if the words look current")
    s.add_argument("--force", action="store_true", help="rewrite an existing clips.json skeleton")
    s.set_defaults(fn=cmd_prep)
    s = sub.add_parser("frames")
    s.add_argument("clips")
    s.add_argument("--per", type=int, default=8, help="frames per clip")
    s.add_argument("--cols", type=int, default=4, help="tiles per row")
    s.add_argument("--width", type=int, default=640, help="tile width in px; large enough to read screen text")
    s.set_defaults(fn=cmd_frames)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
