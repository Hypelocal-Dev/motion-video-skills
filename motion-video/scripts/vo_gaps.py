#!/usr/bin/env python3
"""Find pauses inside a span of a voiceover take, and optionally cut one down.

TTS voices often leave a small silence inside a spoken number ("thirty five | hundred").
It reads as a stumble. Scan the span the number occupies (use the word timings from
transcribe), then shorten the gap so the number sounds like one word.

Examples:
  vo_gaps.py line.wav --start 0.55 --end 1.70
  vo_gaps.py line.wav --start 0.55 --end 1.70 --fix fixed.wav --keep 0.035
"""

from __future__ import annotations

import argparse
import subprocess

from _audio import db_frames, read_mono, require

RATE = 16000
HOP = 0.002


def find_gaps(path: str, start: float, end: float, threshold: float, min_gap: float):
    frames = db_frames(read_mono(path, RATE), RATE, HOP)
    gaps, run_start = [], None
    for i, level in enumerate(frames):
        t = i * HOP
        if not (start <= t <= end):
            continue
        if level < threshold:
            run_start = t if run_start is None else run_start
        else:
            if run_start is not None and t - run_start >= min_gap:
                gaps.append((round(run_start, 3), round(t, 3)))
            run_start = None
    return gaps


def splice(path: str, out: str, gap: tuple[float, float], keep: float, fade: float = 0.008) -> None:
    """Remove the middle of a gap, leaving `keep` seconds, joined with a short crossfade."""
    require("ffmpeg")
    a, b = gap
    cut = (b - a) - keep
    if cut <= fade * 2:
        raise SystemExit(f"gap {a}-{b} is already {b - a:.3f}s; nothing worth cutting")
    left_end = a + keep / 2 + fade / 2
    right_start = left_end + cut
    graph = (
        f"[0]atrim=0:{left_end:.4f},asetpts=PTS-STARTPTS[l];"
        f"[0]atrim={right_start:.4f},asetpts=PTS-STARTPTS[r];"
        f"[l][r]acrossfade=d={fade}:c1=tri:c2=tri"
    )
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-filter_complex", graph, out], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav")
    p.add_argument("--start", type=float, required=True, help="span start, seconds")
    p.add_argument("--end", type=float, required=True, help="span end, seconds")
    p.add_argument("--threshold", type=float, default=-38.0, help="silence level in dBFS (default -38)")
    p.add_argument("--min-gap", type=float, default=0.04, help="ignore gaps shorter than this (default 0.04s)")
    p.add_argument("--fix", metavar="OUT", help="write a copy with the longest gap shortened")
    p.add_argument("--keep", type=float, default=0.035, help="silence to keep when fixing (default 0.035s)")
    args = p.parse_args()

    gaps = find_gaps(args.wav, args.start, args.end, args.threshold, args.min_gap)
    if not gaps:
        print("no gaps found in span")
        return
    for a, b in gaps:
        print(f"gap {a:.3f}-{b:.3f}  ({(b - a) * 1000:.0f} ms)")
    if args.fix:
        # The first gap is usually the word boundary before the number; the longest
        # gap after it is the stumble. Let the user check the printout above.
        inner = gaps[1:] or gaps
        target = max(inner, key=lambda g: g[1] - g[0])
        splice(args.wav, args.fix, target, args.keep)
        print(f"cut gap {target[0]:.3f}-{target[1]:.3f} down to {args.keep * 1000:.0f} ms -> {args.fix}")


if __name__ == "__main__":
    main()
