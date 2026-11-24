#!/usr/bin/env python3
"""Who's talking when, for two people on camera, from mouth movement.

Usage:
  clips_speakers.py VIDEO --left x,y,w,h --right x,y,w,h [--start S --end E] [--min 1.0] -o speakers.json

Boxes are in the video's own pixels and should cover each person's mouth and chin
(not hands or a mic). Sample a frame, eyeball the boxes, and check them once by drawing
them on the frame. Motion is measured by frame differencing in each box; the louder
mover is the speaker, with a 15% margin so it doesn't flicker. Switches shorter than
--min seconds merge into the previous speaker.

Output: [{"start", "end", "speaker": "left" | "right"}], times relative to --start.

Adapted from clipify's analyze.py by Louise de Sadeleer (MIT License). Copyright (c)
2026 Louise de Sadeleer. Permission is granted under the MIT License; see the clips
skill for the full notice.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

from _audio import require


def motion(video: str, box: str, start: float | None, end: float | None) -> tuple[list[float], list[float]]:
    x, y, w, h = box.split(",")
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    cmd += ["-i", video, "-vf",
            f"crop={w}:{h}:{x}:{y},format=gray,tblend=all_mode=difference,signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG",
            "-an", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    times, vals, cur = [], [], None
    for line in err.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            cur = float(m.group(1))
            continue
        m = re.search(r"lavfi\.signalstats\.YAVG=([0-9.]+)", line)
        if m and cur is not None:
            times.append(cur)
            vals.append(float(m.group(1)))
            cur = None
    return times, vals


def smooth(v: list[float], win: int = 15) -> list[float]:
    m = sum(v) / max(1, len(v)) or 1
    v = [x / m for x in v]
    out = []
    for i in range(len(v)):
        window = v[max(0, i - win // 2):i + win // 2 + 1]
        out.append(sum(window) / len(window))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--min", type=float, default=1.0, help="shortest speaker turn kept (s)")
    ap.add_argument("-o", "--out", default="-")
    a = ap.parse_args()
    require("ffmpeg")
    t_l, v_l = motion(a.video, a.left, a.start, a.end)
    _, v_r = motion(a.video, a.right, a.start, a.end)
    n = min(len(v_l), len(v_r))
    if n == 0:
        sys.exit("error: no frames measured; check the boxes and times")
    s_l, s_r = smooth(v_l[:n]), smooth(v_r[:n])
    cur = 0 if s_l[0] >= s_r[0] else 1
    who = []
    for i in range(n):
        if cur == 0 and s_r[i] > s_l[i] * 1.15:
            cur = 1
        elif cur == 1 and s_l[i] > s_r[i] * 1.15:
            cur = 0
        who.append(cur)
    t = t_l[:n] + [t_l[n - 1] + (t_l[1] - t_l[0] if n > 1 else 1 / 30)]
    segs: list[dict] = []
    for i, s in enumerate(who):
        if segs and segs[-1]["speaker"] == ("left" if s == 0 else "right"):
            segs[-1]["end"] = round(t[i + 1], 3)
        else:
            segs.append({"start": round(t[i], 3), "end": round(t[i + 1], 3), "speaker": "left" if s == 0 else "right"})
    merged: list[dict] = []
    for seg in segs:
        if merged and seg["end"] - seg["start"] < a.min:
            merged[-1]["end"] = seg["end"]
        elif merged and merged[-1]["speaker"] == seg["speaker"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)
    text = json.dumps(merged, indent=1)
    if a.out == "-":
        print(text)
    else:
        open(a.out, "w").write(text)
    print(f"{len(merged)} turns over {merged[-1]['end']:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
