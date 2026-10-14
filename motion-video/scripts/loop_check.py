#!/usr/bin/env python3
"""Check that a looping video's last frame matches its first frame.

Autoplaying hero videos loop, so a mismatch shows as a visible jump. Prints the PSNR
between the two frames: 40 dB or more looks identical to the eye.

Example:
  loop_check.py renders/final.mp4
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile

from _audio import duration, require


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--min-db", type=float, default=40.0)
    args = p.parse_args()
    require("ffmpeg")

    last_t = max(0.0, duration(args.video) - 0.06)  # seeking past the last frame yields no image
    with tempfile.TemporaryDirectory() as tmp:
        first, last = os.path.join(tmp, "first.png"), os.path.join(tmp, "last.png")
        for t, f in ((0, first), (last_t, last)):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(t), "-i", args.video,
                            "-frames:v", "1", f], check=True)
            if not os.path.exists(f):
                sys.exit(f"could not grab a frame at {t:.2f}s")
        res = subprocess.run(["ffmpeg", "-nostdin", "-i", first, "-i", last, "-lavfi", "psnr", "-f", "null", "-"],
                             capture_output=True, text=True)
    m = re.search(r"average:(inf|[\d.]+)", res.stderr)
    if not m:
        sys.exit("could not measure PSNR")
    score = float("inf") if m.group(1) == "inf" else float(m.group(1))
    verdict = "PASS" if score >= args.min_db else "FAIL"
    print(f"{verdict}: first vs last frame PSNR {score:.1f} dB (need {args.min_db:g})")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
