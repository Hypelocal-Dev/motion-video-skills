#!/usr/bin/env python3
"""Measure integrated loudness (LUFS) and true peak of a file.

Web and social video sits around -14 LUFS. Voiceover clips are normalized to -13.5.

Examples:
  loudness.py renders/final.mp4
  loudness.py renders/final.mp4 --target -14 --tolerance 1.5
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

from _audio import require


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--target", type=float, help="expected LUFS; exit 1 if outside tolerance")
    p.add_argument("--tolerance", type=float, default=1.5)
    args = p.parse_args()
    require("ffmpeg")

    res = subprocess.run(["ffmpeg", "-nostdin", "-i", args.file, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True)
    summary = res.stderr[res.stderr.rfind("Summary:"):]
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not lufs:
        sys.exit("no audio found")
    value = float(lufs.group(1))
    print(f"integrated {value:.1f} LUFS, true peak {peak.group(1) if peak else '?'} dBFS")
    if args.target is not None and abs(value - args.target) > args.tolerance:
        print(f"FAIL: more than {args.tolerance} LU from {args.target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
