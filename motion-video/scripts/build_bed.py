#!/usr/bin/env python3
"""Rebuild a music track so its hits land on your video's cuts.

Takes a source track and a JSON list of segments. Each segment copies a range of the
source to a start time in the output, with short fades so the joins don't click.

segments.json:
  {
    "duration": 41.0,
    "segments": [
      {"src": [0.0, 3.0],  "at": 0.0},
      {"src": [7.6, 10.3], "at": 3.0},
      {"src": [3.0, 24.6], "at": 5.7}
    ]
  }

Example:
  build_bed.py source.wav segments.json music.wav
"""

from __future__ import annotations

import argparse
import json
import subprocess

from _audio import duration, require


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source")
    p.add_argument("plan", help="segments JSON")
    p.add_argument("out")
    p.add_argument("--fade", type=float, default=0.04, help="fade at each join, seconds")
    p.add_argument("--tail", type=float, default=0.6, help="fade-out at the end, seconds")
    args = p.parse_args()
    require("ffmpeg")

    plan = json.load(open(args.plan))
    total = float(plan["duration"])
    graph, labels = [], []
    for i, seg in enumerate(plan["segments"]):
        a, b = seg["src"]
        at = float(seg["at"])
        length = b - a
        fade_in = 0.15 if i == 0 and a > 0 else args.fade
        ms = int(at * 1000)
        graph.append(
            f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d={fade_in},"
            f"afade=t=out:st={length - args.fade:.3f}:d={args.fade},adelay={ms}|{ms}[s{i}]"
        )
        labels.append(f"[s{i}]")
    graph.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_dur={total},atrim=0:{total},"
        + f"afade=t=out:st={total - args.tail:.3f}:d={args.tail}[out]"
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", args.source, "-filter_complex", ";".join(graph),
         "-map", "[out]", "-ar", "48000", args.out],
        check=True,
    )
    print(f"wrote {args.out} ({duration(args.out):.2f}s)")
    joins = sorted(float(s["at"]) for s in plan["segments"])[1:]
    print("check these seams by ear: " + ", ".join(f"{t:.1f}s" for t in joins))


if __name__ == "__main__":
    main()
