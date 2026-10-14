#!/usr/bin/env python3
"""Print a loudness map and the hit (onset) times of a music track.

Use it before building a sound bed: the map shows quiet stretches you can use as
padding, and the onsets show where the track's hits and swells land.

Example:
  envelope.py music.wav
"""

from __future__ import annotations

import argparse

from _audio import db_frames, read_mono

BARS = " ▁▂▃▄▅▆▇█"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("track")
    p.add_argument("--jump", type=float, default=5.0, help="dB rise between 0.1s frames that counts as a hit")
    args = p.parse_args()

    db = db_frames(read_mono(args.track, 8000), 8000, 0.1)
    rows = []
    for second in range(0, len(db), 10):
        chunk = db[second:second + 10]
        rows.append(f"{second // 10:>3}s " + "".join(BARS[max(0, min(8, int((d + 50) / 4)))] for d in chunk))
    print("\n".join(rows))
    hits = [
        (i / 10, round(db[i] - db[i - 1], 1), round(db[i], 1))
        for i in range(1, len(db))
        if db[i] - db[i - 1] > args.jump
    ]
    print("\nhits (time s, rise dB, level dBFS):")
    for t, rise, level in hits:
        marker = "  BIG" if level > -20 else ""
        print(f"  {t:6.1f}  +{rise:<5} {level}{marker}")


if __name__ == "__main__":
    main()
