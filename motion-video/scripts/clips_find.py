#!/usr/bin/env python3
"""Helpers for picking clips out of a longer video.

  clips_find.py lines WORDS [--gap 0.6]
      Print the transcript as timed sentence lines, with pauses marked, so you can read
      a long video quickly and pick moments. WORDS is a word-timing JSON: HyperFrames'
      transcript.json ([{text, start, end}]) or tutorial_cut.py's spine_words.json.

  clips_find.py frames CLIPS_JSON [--per 5]
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
                        "--cols", str(n), "--width", "360", "-o", out], check=True, stdout=subprocess.DEVNULL)
        print(f"{c['name']}: {out}  ({c['start']}-{c['end']}s)")
    print("Look at each sheet: is the moment on screen, is the subject in frame, and is anything private showing?")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lines")
    s.add_argument("words")
    s.add_argument("--gap", type=float, default=0.6, help="pause (s) that ends a line")
    s.set_defaults(fn=cmd_lines)
    s = sub.add_parser("frames")
    s.add_argument("clips")
    s.add_argument("--per", type=int, default=5, help="frames per clip")
    s.set_defaults(fn=cmd_frames)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
