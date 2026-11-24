#!/usr/bin/env python3
"""Find sharp impact sounds (a chop, hit, clap, drum, ball strike) to cut a montage on.

Run with the voice environment's Python (needs numpy):
  "$MV_VENV/bin/python" clips_transients.py VIDEO_OR_AUDIO [--band 1000:6000] [--min-flux 30] [--min-gap 0.6] [--top N]

Prints JSON: [{"time", "flux", "db"}] sorted by time. Real impacts usually score 50-300;
room tone and wind sit at 5-15. Too many hits: raise --min-flux to 40-50 or move the
band. Too few: drop it to 20. Bands: 1000:6000 wood, metal, glass; 200:2000 heavy thuds
(kick drum, body shots); 4000:10000 clinks, whistles, snare cracks. Drumming may need
--min-gap 0.2. Audio finds the sound, not the picture: check each hit on a frame.

Adapted from clipify's detect_transients.py by Louise de Sadeleer (MIT License).
Copyright (c) 2026 Louise de Sadeleer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("error: numpy is missing. Run with $MV_VENV/bin/python (see setup.sh).")

SR = 16000


def load(path: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def detect(data: np.ndarray, lo: int, hi: int, min_flux: float, min_gap: float) -> list[dict]:
    win, hop = int(SR * 0.025), int(SR * 0.01)
    n = (len(data) - win) // hop
    if n < 4:
        return []
    frames = np.lib.stride_tricks.as_strided(data, shape=(n, win), strides=(data.strides[0] * hop, data.strides[0]))
    spec = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    b_lo, b_hi = max(1, int(lo * win / SR)), min(spec.shape[1], int(hi * win / SR))
    flux = np.sum(np.maximum(np.diff(spec[:, b_lo:b_hi], axis=0), 0), axis=1)
    times = (np.arange(len(flux)) + 1) * hop / SR
    db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1) + 1e-10) + 1e-10)
    gap = max(1, int(min_gap * SR / hop))
    peaks, last = [], -gap
    for i in range(2, len(flux) - 2):
        if flux[i] < min_flux or flux[i] != np.max(flux[max(0, i - 3):i + 4]):
            continue
        rec = {"time": round(float(times[i]), 3), "flux": round(float(flux[i]), 1), "db": round(float(db[i]), 1)}
        if i - last < gap:
            if peaks and rec["flux"] > peaks[-1]["flux"]:
                peaks[-1], last = rec, i
            continue
        peaks.append(rec)
        last = i
    return peaks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--band", default="1000:6000")
    ap.add_argument("--min-flux", type=float, default=30.0)
    ap.add_argument("--min-gap", type=float, default=0.6)
    ap.add_argument("--top", type=int, default=0)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.band.split(":"))
    peaks = detect(load(a.input), lo, hi, a.min_flux, a.min_gap)
    if a.top:
        peaks = sorted(sorted(peaks, key=lambda p: -p["flux"])[:a.top], key=lambda p: p["time"])
    print(json.dumps(peaks, indent=1))


if __name__ == "__main__":
    main()
