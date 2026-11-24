#!/usr/bin/env python3
"""Synthesize an original lo-fi music bed and three UI sound effects (no third-party rights).

Runs with the plugin's voice environment, which has numpy:
  "$MV_VENV/bin/python" tutorial_bed.py PROJECT [--seconds N] [--bpm 76] [--seed 7]

Writes PROJECT/edit/assets/audio/music.m4a (or .wav without ffmpeg) and sfx-whoosh.wav,
sfx-tick.wav, sfx-pop.wav. Length defaults to the spine length in work/spine_map.json.
The bed is soft electric-piano chords, a sine bass, brushed drums and a little vinyl
noise. It is a good default under a talking voice; a licensed track is better when
the brand has one. You can measure it, not hear it: ask the person to listen.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave

try:
    import numpy as np
except ImportError:
    sys.exit("error: numpy is missing. Run this with the voice environment's Python: "
             "$MV_VENV/bin/python (see setup.sh).")

SR = 44100
rng = np.random.default_rng(7)


def band(x, lo=None, hi=None):
    """Zero-phase FFT band filter with soft edges. Fine for offline synthesis."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec = np.fft.rfft(x)
    gain = np.ones_like(f)
    if hi:
        gain *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo:
        gain *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(spec * gain, n)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


PROG_A = [[53, 57, 60, 64, 67], [52, 55, 59, 62, 67], [50, 53, 57, 60, 64], [48, 52, 55, 59, 62]]
PROG_B = [[46, 50, 53, 57, 62], [45, 48, 52, 55, 60], [43, 46, 50, 53, 57], [48, 52, 57, 62, 64]]
ROOTS_A, ROOTS_B = [41, 40, 38, 36], [46, 45, 43, 36]


def ep(f, dur, vel):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 1.6) * (1 - np.exp(-t * 180))
    tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3)
            + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 6)
            + 0.06 * np.sin(2 * np.pi * 7.1 * f * t) * np.exp(-t * 25))
    return tone * env * (1 + 0.08 * np.sin(2 * np.pi * 4.2 * t)) * vel


def add(buf, sig, at):
    i = int(at * SR)
    if i < len(buf):
        j = min(len(buf), i + len(sig))
        buf[i:j] += sig[: j - i]


def bed(seconds, bpm):
    beat = 60 / bpm
    bar = 4 * beat
    n = int((seconds + 1) * SR)
    keys, bass, drums = np.zeros(n), np.zeros(n), np.zeros(n)
    t = np.arange(int(0.45 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
    t = np.arange(int(0.3 * SR)) / SR
    snare = (0.6 * band(rng.standard_normal(len(t)), 900, 5000) * np.exp(-t * 22)
             + 0.35 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30))
    t = np.arange(int(0.08 * SR)) / SR
    hat = band(rng.standard_normal(len(t)), 7000) * np.exp(-t * 70)
    for b in range(int(seconds / bar) + 1):
        t0 = b * bar
        prog, roots = (PROG_B, ROOTS_B) if (b // 16) % 3 == 1 else (PROG_A, ROOTS_A)
        chord, root = prog[b % 4], roots[b % 4]
        vel = 0.9 + 0.1 * rng.random()
        for k, m in enumerate(chord):
            add(keys, ep(midi(m), bar * 0.9, 0.16 * vel), t0 + k * 0.012)
        for k, m in enumerate(chord[1:]):
            add(keys, ep(midi(m), bar * 0.45, 0.07 * vel), t0 + 1.5 * beat + k * 0.01)
        bt = np.arange(int(bar * 0.95 * SR)) / SR
        add(bass, 0.28 * np.sin(2 * np.pi * midi(root - 12) * bt) * np.exp(-bt * 0.9) * (1 - np.exp(-bt * 60)), t0)
        if b >= 2:
            for k in range(4):
                bt0 = t0 + k * beat
                if k in (0, 2) or (k == 3 and b % 2):
                    add(drums, 0.55 * kick, bt0 + (0.5 * beat if k == 3 else 0))
                if k in (1, 3):
                    add(drums, 0.32 * snare, bt0)
                add(drums, 0.10 * hat, bt0)
                add(drums, 0.065 * hat, bt0 + 0.58 * beat)
    mix = band(keys, hi=3200) + bass + band(drums, hi=6000)
    crackle = np.zeros(n)
    idx = rng.choice(n, size=int(seconds * 6), replace=False)
    crackle[idx] = rng.uniform(-1, 1, len(idx)) * 0.05
    mix += band(crackle, hi=5000) + 0.004 * band(rng.standard_normal(n), hi=1800)
    mix *= 1 + 0.015 * np.sin(2 * np.pi * 0.23 * np.arange(n) / SR)
    mix = mix[: int(seconds * SR)]
    mix[: int(1.5 * SR)] *= np.linspace(0, 1, int(1.5 * SR))
    mix[-int(2.5 * SR):] *= np.linspace(1, 0, int(2.5 * SR))
    d = int(0.012 * SR)
    right = np.concatenate([np.zeros(d), mix[:-d]]) * 0.96 + mix * 0.04
    return np.stack([mix, right], 1)


def write_wav(path, x):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = x / max(1e-9, float(np.max(np.abs(x)))) * 0.7
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def sfx(out):
    t = np.arange(int(0.7 * SR)) / SR
    noise = rng.standard_normal(len(t))
    sweep = np.zeros_like(noise)
    for i, seg in enumerate(np.array_split(np.arange(len(t)), 14)):
        lo = 300 * 1.25 ** i
        sweep[seg] = band(noise, lo, lo * 2.2)[seg]
    write_wav(os.path.join(out, "sfx-whoosh.wav"), sweep * np.sin(np.pi * t / 0.7) ** 2)
    t = np.arange(int(0.05 * SR)) / SR
    write_wav(os.path.join(out, "sfx-tick.wav"),
              (0.6 * np.sin(2 * np.pi * 2100 * t) + 0.4 * band(rng.standard_normal(len(t)), 3000)) * np.exp(-t * 120))
    t = np.arange(int(0.12 * SR)) / SR
    write_wav(os.path.join(out, "sfx-pop.wav"),
              np.sin(2 * np.pi * np.cumsum(700 + 700 * t / 0.12) / SR) * np.exp(-t * 32) * (1 - np.exp(-t * 900)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--bpm", type=float, default=76)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    global rng
    rng = np.random.default_rng(a.seed)
    seconds = a.seconds or json.load(open(os.path.join(a.project, "work", "spine_map.json")))[-1]["end"] + 0.5
    out = os.path.join(a.project, "edit", "assets", "audio")
    os.makedirs(out, exist_ok=True)
    wav = os.path.join(out, "music.wav")
    write_wav(wav, bed(seconds, a.bpm))
    sfx(out)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-c:a", "aac", "-b:a", "192k",
                        os.path.join(out, "music.m4a")], check=True)
        os.remove(wav)
        print(f"wrote {out}/music.m4a ({seconds:.0f}s) and three sfx")
    except (OSError, subprocess.CalledProcessError):
        print(f"wrote {wav} ({seconds:.0f}s); set plan.music.bed to assets/audio/music.wav")


if __name__ == "__main__":
    main()
