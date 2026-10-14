#!/usr/bin/env python3
"""Tile frames from a render into one image so you can check a whole video at a glance.

Examples:
  contact_sheet.py renders/draft.mp4                    # 12 evenly spaced frames
  contact_sheet.py renders/draft.mp4 --times 2,5.5,9    # specific moments
  contact_sheet.py renders/draft.mp4 --count 20 --cols 5 -o sheet.png
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import tempfile

from _audio import duration, require


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--times", help="comma-separated timestamps in seconds")
    p.add_argument("--count", type=int, default=12)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--width", type=int, default=400, help="width of each tile in px")
    p.add_argument("-o", "--out", help="output PNG (default: <video>.contact.png)")
    args = p.parse_args()
    require("ffmpeg")

    d = duration(args.video)
    last = max(0.0, d - 0.05)  # seeking past the last frame yields no image
    if args.times:
        times = [min(float(t), last) for t in args.times.split(",")]
    else:
        times = [round((i + 0.5) * d / args.count, 2) for i in range(args.count)]
    out = args.out or os.path.splitext(args.video)[0] + ".contact.png"
    cols = min(args.cols, len(times))
    rows = math.ceil(len(times) / cols)

    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for i, t in enumerate(times):
            f = os.path.join(tmp, f"{i:03d}.png")
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(t), "-i", args.video, "-frames:v", "1",
                 "-vf", f"scale={args.width}:-2", f],
                check=True,
            )
            if not os.path.exists(f):
                raise SystemExit(f"no frame at {t}s")
            frames.append(f)
        while len(frames) < cols * rows:  # pad the grid with the last frame
            frames.append(frames[-1])
        inputs = sum((["-i", f] for f in frames), [])
        layout = "|".join(_cell(i, cols) for i in range(len(frames)))
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex",
             "".join(f"[{i}]" for i in range(len(frames))) + f"xstack=inputs={len(frames)}:layout={layout}",
             out],
            check=True,
        )
    print(f"wrote {out}")
    print("frames at: " + ", ".join(f"{t:g}s" for t in times))


def _cell(i: int, cols: int) -> str:
    x = "+".join(["w0"] * (i % cols)) or "0"
    y = "+".join(["h0"] * (i // cols)) or "0"
    return f"{x}_{y}"


if __name__ == "__main__":
    main()
