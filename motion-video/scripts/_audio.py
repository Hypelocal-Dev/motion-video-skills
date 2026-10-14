"""Shared helpers for the audio and video scripts. Stdlib only; shells out to ffmpeg/ffprobe."""

from __future__ import annotations

import array
import math
import shutil
import subprocess
import sys


def require(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"error: {tool} is not installed or not on PATH. Run scripts/doctor.sh for help.")


def duration(path: str) -> float:
    require("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def read_mono(path: str, rate: int = 16000) -> array.array:
    """Decode any audio/video file to mono signed 16-bit samples."""
    require("ffmpeg")
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return array.array("h", raw)


def db_frames(samples: array.array, rate: int, hop_s: float) -> list[float]:
    """RMS level in dBFS for each hop-sized frame."""
    hop = max(1, int(rate * hop_s))
    out = []
    for k in range(0, len(samples) - hop + 1, hop):
        seg = samples[k:k + hop]
        rms = math.sqrt(sum(v * v for v in seg) / hop)
        out.append(20 * math.log10(rms / 32768 + 1e-9))
    return out
