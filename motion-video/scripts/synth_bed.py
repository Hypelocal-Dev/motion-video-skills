#!/usr/bin/env python3
"""Generate a soft placeholder music bed with whoosh hits at given times.

Use it when you have no licensed track yet, or for drafts. The output is generated
from sine tones and filtered noise, so it carries no third-party rights.

Example:
  synth_bed.py --duration 24 --hits 4.5,9.5,14.5,19 music.wav
"""

from __future__ import annotations

import argparse
import subprocess

from _audio import require

# A soft major-seventh pad. Frequencies in Hz.
CHORD = [130.81, 196.00, 246.94, 329.63]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out")
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--hits", default="", help="comma-separated hit times in seconds")
    p.add_argument("--level", type=float, default=-30.0, help="pad level in dBFS (default -30)")
    args = p.parse_args()
    require("ffmpeg")

    d = args.duration
    pad = "+".join(f"0.25*sin(2*PI*{f}*t)" for f in CHORD)
    inputs = ["-f", "lavfi", "-i", f"aevalsrc='{pad}':s=48000:d={d}"]
    graph = [f"[0]tremolo=f=0.25:d=0.35,volume={args.level}dB,afade=t=in:d=1.0,afade=t=out:st={d - 1.2}:d=1.2[pad]"]
    labels = ["[pad]"]
    hits = [float(h) for h in args.hits.split(",") if h.strip()]
    for i, h in enumerate(hits):
        inputs += ["-f", "lavfi", "-i", "anoisesrc=color=pink:d=0.9:a=0.5:r=48000"]
        start = max(0.0, h - 0.45)
        ms = int(start * 1000)
        graph.append(
            f"[{i + 1}]bandpass=f=900:width_type=o:w=2,afade=t=in:d=0.4:curve=exp,afade=t=out:st=0.45:d=0.45,"
            f"volume=-20dB,adelay={ms}|{ms}[h{i}]"
        )
        labels.append(f"[h{i}]")
    graph.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,atrim=0:{d}[out]")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph),
         "-map", "[out]", "-ac", "2", args.out],
        check=True,
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
