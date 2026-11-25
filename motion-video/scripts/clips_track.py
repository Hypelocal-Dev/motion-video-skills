#!/usr/bin/env python3
"""Follow the action in event footage shot on a plain-colored floor (mats, courts, rings).

Usage:
  clips_track.py VIDEO --start S --end E [-o follow.json]
  clips_track.py VIDEO --segments 120-150,300-322 [-o follow.json]   # montage: times run on

Writes [[t, x, y, cut], ...] for the clips "follow" field: clip-local seconds, source pixels,
cut = 1 where the broadcast cuts to another camera (the band jumps instead of gliding).

How it works: the floor is found by its color (default: blue mat). The athletes are the
non-floor pixels inside the floor area, and the densest cluster of them wins, so two
tangled grapplers beat a standing referee. The path is median-filtered and smoothed
within each shot. Check the result with --sheet, which draws the window on frames.

Needs numpy (run with $MV_VENV/bin/python).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

import numpy as np

FPS = 4
SW = 320  # analysis width


def frames(video, a, b, top):
    w, h = SW, round(SW * 9 / 16)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{b - a}", "-i", video, "-vf",
           f"fps={FPS},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    arr = np.frombuffer(raw[: n * w * h * 3], np.uint8).reshape(n, h, w, 3).astype(np.int16)
    return arr[:, :top]


def box(m, r):
    """Mean over a (2r+1)^2 box, via an integral image."""
    p = np.pad(m.astype(np.float32), r + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    d = 2 * r + 1
    s = c[d:, d:] - c[:-d, d:] - c[d:, :-d] + c[:-d, :-d]
    return s[: m.shape[0], : m.shape[1]] / (2 * r + 1) ** 2


def track(arr, floor):
    pts, cuts, prev = [], [], None
    for f in arr:
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        if floor == "blue":
            mat = (b > r + 35) & (b > g + 5)
        elif floor == "green":
            mat = (g > r + 25) & (g > b + 10)
        else:
            mat = (r > g + 25) & (r > b + 25)
        zone = box(mat, 18) > 0.35  # the floor area, with holes where people are
        lo, hi = np.minimum(np.minimum(r, g), b), np.maximum(np.maximum(r, g), b)
        logo = (lo > 170) & (hi - lo < 45)
        cand = (~mat) & zone & ~logo  # near-white, unsaturated pixels are usually logos printed on the floor
        dens = box(cand, 14)
        y, x = np.unravel_index(np.argmax(dens), dens.shape)
        pts.append((x, y, dens[y, x]))
        # camera cut: big change in a blurred thumbnail (motion alone stays under ~30)
        sm = f[::6, ::6].astype(np.float32)
        hh, ww = sm.shape[0] // 4 * 4, sm.shape[1] // 4 * 4
        sm = sm[:hh, :ww].reshape(hh // 4, 4, ww // 4, 4, 3).mean((1, 3))
        cuts.append(prev is not None and float(np.abs(sm - prev).mean()) > 33)
        prev = sm
    return pts, cuts


def smooth(vals, shots):
    out = np.array(vals, float)
    for a, b in shots:
        seg = out[a:b]
        if len(seg) >= 5:  # median of 5, then a short gaussian
            med = np.array([np.median(seg[max(0, i - 2): i + 3]) for i in range(len(seg))])
            k = np.exp(-0.5 * (np.arange(-4, 5) / 2.0) ** 2)
            k /= k.sum()
            pad = np.pad(med, 4, mode="edge")
            seg = np.convolve(pad, k, "valid")
        out[a:b] = seg
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--segments", help="a-b,c-d in source seconds (montage)")
    ap.add_argument("--floor", default="blue", choices=["blue", "green", "red"])
    ap.add_argument("--top", type=int, default=541, help="ignore source rows below this (a score bar), source px")
    ap.add_argument("-o", "--out", default="-")
    ap.add_argument("--sheet", help="write a contact sheet with the follow window drawn (needs --window W)")
    ap.add_argument("--window", type=int, default=676, help="window width in source pixels for --sheet")
    a = ap.parse_args()
    segs = [tuple(map(float, s.split("-"))) for s in a.segments.split(",")] if a.segments else [(a.start, a.end)]
    sw = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                             "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip())
    scale = sw / SW
    top = int(a.top / scale)
    xs, ys, cut, ts, off = [], [], [], [], 0.0
    for sa, sb in segs:
        arr = frames(a.video, sa, sb, top)
        pts, c = track(arr, a.floor)
        if c:
            c[0] = bool(ts)  # a montage join is a cut too
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
        cut += c
        ts += [off + i / FPS for i in range(len(pts))]
        off += sb - sa
    starts = [i for i, c in enumerate(cut) if c] + [len(cut)]
    shots, s0 = [], 0
    for s in starts:
        if s > s0:
            shots.append((s0, s))
        s0 = s
    sx, sy = smooth(xs, shots), smooth(ys, shots)
    out = [[round(t, 2), round(x * scale), round(y * scale), int(c)] for t, x, y, c in zip(ts, sx, sy, cut)]
    js = json.dumps(out)
    if a.out == "-":
        print(js)
    else:
        open(a.out, "w").write(js)
        print(f"wrote {a.out}: {len(out)} points, {sum(cut)} camera cuts", file=sys.stderr)
    if a.sheet:
        sheet(a.video, segs, out, a.window, a.top, a.sheet)


def sheet(video, segs, out, win, top, path):
    """Every 2 s: the frame with the follow window drawn, tiled 6 wide."""
    filt, ins, n = [], [], 0
    acc = 0.0
    for sa, sb in segs:
        for p in out:
            if acc <= p[0] < acc + (sb - sa) and abs(p[0] * 2 - round(p[0] * 2)) < 1e-6 and round(p[0] * 2) % 4 == 0:
                x0 = max(0, min(p[1] - win // 2, 1280 - win))
                ins += ["-ss", f"{sa + p[0] - acc}", "-i", video]
                box_ = f"drawbox=x={x0}:y=0:w={win}:h={top}:color=yellow@0.9:t=6"
                filt.append(f"[{n}:v]trim=end_frame=1,{box_},scale=320:-2[f{n}]")
                n += 1
        acc += sb - sa
    if not n:
        return
    cols = 6
    rows = -(-n // cols)
    while n < rows * cols:  # pad with black tiles
        ins += ["-f", "lavfi", "-i", "color=black:s=320x180:d=0.1"]
        filt.append(f"[{n}:v]trim=end_frame=1[f{n}]")
        n += 1
    tiles = "".join(f"[f{i}]" for i in range(n))
    filt.append(f"{tiles}xstack=inputs={n}:grid={cols}x{rows}[o]" if n > 1 else "[f0]copy[o]")
    cmd = ["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(filt),
           "-map", "[o]", "-frames:v", "1", path]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
