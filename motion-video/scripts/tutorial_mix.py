#!/usr/bin/env python3
"""Mix the music bed under the voice in a tutorial edit. Run after tutorial_gen.py.

Usage: tutorial_mix.py PROJECT

1. If the HyperFrames audio skill is installed, run its voiceover carve on #music against
   the spine voice. Carve dips only the bands the voice uses, so the bed stays musical.
   carve.mjs needs @hyperframes/core in the project: `npm i -D @hyperframes/core` in edit/.
2. Merge tutorial_gen's volume lane (fade in/out and lifts on cards) into the same
   data-automation attribute. Two data-automation attributes would make the browser keep
   only the first one.
3. Without carve, fall back to a plain duck: the bed drops wherever the spine has speech.
"""

from __future__ import annotations

import glob
import html
import json
import os
import re
import subprocess
import sys


def find_carve() -> str | None:
    pats = [os.path.expanduser("~/.claude/plugins/cache/*/hyperframes/*/skills/hyperframes-audio/scripts/carve.mjs"),
            os.path.expanduser("~/.claude/plugins/marketplaces/*/skills/hyperframes-audio/scripts/carve.mjs")]
    hits = sorted(h for p in pats for h in glob.glob(p))
    return hits[-1] if hits else None


def duck_lane(work: str, level: float) -> dict:
    pieces = json.load(open(os.path.join(work, "spine_map.json")))
    pts = []
    for p in pieces:
        if p["kind"] == "speech":
            pts += [(p["start"] - 0.2, 1.0), (p["start"], 0.45), (p["end"], 0.45), (p["end"] + 0.4, 1.0)]
    merged = sorted({round(t, 2): v for t, v in pts if t >= 0}.items())
    return {"target": "gain", "points": [{"t": t, "v": round(v * level, 3)} for t, v in merged]}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    project = sys.argv[1]
    edit, work = os.path.join(project, "edit"), os.path.join(project, "work")
    index = os.path.join(edit, "index.html")
    s = open(index).read()
    if 'id="music"' not in s:
        print("no #music track; nothing to mix")
        return
    carve, carved = find_carve(), False
    if carve:
        r = subprocess.run(["node", carve, "--comp", index, "--bed", "music", "--voice", "spine"],
                           capture_output=True, text=True)
        carved = r.returncode == 0
        print(r.stdout.strip().splitlines()[-1] if carved and r.stdout.strip() else r.stderr.strip()[-400:])
        s = open(index).read()
    i = s.find('<audio id="music"')
    j = s.find(">", i)
    el = s[i:j]
    lanes = []
    for a in re.findall(r"data-automation=(\"[^\"]*\"|'[^']*')", el):
        lanes += json.loads(html.unescape(a[1:-1]))["lanes"]
    lanes = [ln for ln in lanes if ln["target"] != "volume"]
    vol = json.load(open(os.path.join(work, "bed_lane.json")))
    if not carved:
        print("carve unavailable; using a plain duck under speech")
        lanes = []
        # Fold the duck into the volume lane by sampling both on one grid.
        duck = duck_lane(work, 1.0)["points"]

        def at(points: list[dict], t: float) -> float:
            prev = points[0]
            for p in points:
                if p["t"] >= t:
                    if p["t"] == prev["t"]:
                        return p["v"]
                    return prev["v"] + (p["v"] - prev["v"]) * (t - prev["t"]) / (p["t"] - prev["t"])
                prev = p
            return points[-1]["v"]

        grid = sorted({p["t"] for p in vol["points"]} | {p["t"] for p in duck})
        points = [{"t": t, "v": round(at(vol["points"], t) * at(duck, t), 3)} for t in grid]
        vol = {"target": "volume", "points": points}
    lanes.insert(0, vol)
    el = re.sub(r"\s*data-automation=(\"[^\"]*\"|'[^']*')", "", el)
    el += " data-automation='" + json.dumps({"version": 1, "lanes": lanes}).replace("'", "&#39;") + "'"
    open(index, "w").write(s[:i] + el + s[j:])
    print("music lanes:", ", ".join(ln["target"] for ln in lanes))


if __name__ == "__main__":
    main()
