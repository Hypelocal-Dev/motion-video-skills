#!/usr/bin/env python3
# ruff: noqa: E501  (inline HTML/CSS/JS templates)
"""Build (and optionally render) social clips from a longer video, one HyperFrames project per clip.

Usage: clips_make.py CLIPS_JSON [--only NAME ...] [--render] [--quality draft|looks]

clips.json (paths relative to the file):
  {
    "source": "edit/assets/spine.mp4",      # the video to cut from
    "words": "work/spine_words.json",       # word timings for that video (optional; no captions without it)
    "theme": "brand/theme.json",            # optional brand colors and fonts
    "format": "9:16",                       # 9:16 (1080x1920), 1:1 (1080x1080) or 16:9 (1920x1080)
    "out": "clips",                         # projects go in out/<name>/, renders in out/renders/
    "captions": {"proper": {}, "fixes": [[from, to, heard, replacement]], "lowercase": true},
    "covers": [[start, end, clean_media_start]],   # privacy covers in source seconds (copy plan.covers)
    "clips": [
      {"name": "audit-loop", "start": 384.2, "end": 421.5, "title": "Make the AI audit its own work",
       "layout": "stack"}
    ]
  }

Per clip: name, start, end (source seconds), and optional title, layout, rate (constant
speed, e.g. 1.15), captions (false to turn off), and layout fields:
  center  crop the middle (talking head, single subject)
  stack   whole 16:9 frame in the middle, title above, captions below (screen recordings)
  focus   "focus": [[t, x, y, zoom], ...] clip-local seconds, source pixels; the window
          eases between points (follow the cursor or the part of the UI being discussed)
  pan     "speakers": "path.json" from clips_speakers.py, "left": x, "right": x (source
          pixel centers of each face); hard cuts to whoever is talking
  split   "speakers" as above, "boxes": {"left": [x,y,w,h], "right": [x,y,w,h]} around
          each face; both on screen, active speaker on top

Reframing and caption approach adapted from clipify by Louise de Sadeleer (MIT License).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys

from _audio import require

SIZES = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}
THEME = {"ink": "#455CFF", "paper": "#F6F8FF", "dark": "#1F1F2B", "soft": "#9696AE", "head_font": "Poppins", "body_font": "Inter"}
E = html.escape


def probe(path: str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(out[0]), int(out[1])


def load_words(path: str) -> list[tuple[float, float, str]]:
    data = json.load(open(path))
    if isinstance(data, dict):
        data = data.get("words", [])
    return [((w[0], w[1], w[2]) if isinstance(w, list) else (w["start"], w["end"], w["text"].strip())) for w in data]


def caption_chunks(words, clip, cfg, rate):
    a, b = clip["start"], clip["end"]
    proper = {k.lower(): v for k, v in cfg.get("proper", {}).items()}
    fixes = cfg.get("fixes", [])
    picked = []
    for s, e, tok in words:
        if s < a - 0.05 or s >= b:
            continue
        if re.fullmatch(r"\d+\.\d+[.,]?", tok):
            w = tok.rstrip(".,")
        else:
            key = re.sub(r"[^\w'\-:]", "", tok.lower())
            w = next((r for fa, fb, heard, r in fixes if fa <= s <= fb and key == heard.lower()), None)
            if w is None:
                w = "" if key in ("um", "uh") else proper.get(key, key if cfg.get("lowercase", True) else tok.strip(".,!"))
        if w:
            picked.append({"t": round((s - a) / rate, 2), "e": round((min(e, b) - a) / rate, 2), "w": w, "brk": tok[-1:] in ".?,!"})
    chunks, cur = [], []
    for w in picked:
        if cur and (w["t"] - cur[-1]["e"] > 0.3 or len(cur) >= cfg.get("max_words", 3)
                    or len(" ".join(x["w"] for x in cur + [w])) > cfg.get("max_chars", 18) or cur[-1]["brk"]):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def fit(x, lo, hi):
    return max(lo, min(hi, x))


def build(spec_dir: str, spec: dict, clip: dict, theme: dict, words) -> str:
    W, H = SIZES[spec.get("format", "9:16")]
    src = os.path.normpath(os.path.join(spec_dir, spec["source"]))
    sw, sh = probe(src)
    rate = float(clip.get("rate", 1))
    dur = round((clip["end"] - clip["start"]) / rate, 3)
    layout = clip.get("layout", "center")
    out_root = os.path.join(spec_dir, spec.get("out", "clips"))
    proj = os.path.join(out_root, clip["name"])
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
    media = os.path.join(proj, "assets", "source" + os.path.splitext(src)[1])
    if not os.path.exists(media):
        try:
            os.link(src, media)
        except OSError:
            shutil.copy2(src, media)
    t = theme
    rate_attr = f' data-playback-rate="{rate}"' if rate != 1 else ""
    vid = f'data-start="0" data-duration="{dur}" data-media-start="{clip["start"]}"{rate_attr} playsinline'
    js, body, cap_top = [], "", int(H * 0.68)
    covers = ""
    for i, (ca, cb, cm) in enumerate(spec.get("covers", [])):
        lo, hi = max(ca, clip["start"]), min(cb, clip["end"])
        if hi - lo > 0.05:  # muted clean footage over a private stretch, same framing as the main video
            covers += (f'<video id="cov{i}" class="clip" src="assets/{os.path.basename(media)}" data-start="{(lo - clip["start"]) / rate:.3f}" '
                       f'data-duration="{(hi - lo) / rate:.3f}" data-media-start="{cm + (lo - ca):.3f}"{rate_attr} playsinline muted '
                       f'data-track-index="{5 + i}" style="position:absolute;left:0;top:0;width:100%;height:100%"></video>')

    def place(sel, k, cx, cy):
        x = fit(W / 2 - cx * k, W - sw * k, 0)
        y = fit(H / 2 - cy * k, H - sh * k, 0)
        return x, y

    if layout in ("center", "focus", "pan"):
        base = max(W / sw, H / sh)
        body = f'<div id="cam" style="position:absolute;left:0;top:0;width:{sw}px;height:{sh}px;transform-origin:0 0"><video id="v" class="clip" src="assets/{os.path.basename(media)}" {vid} data-track-index="0" data-has-audio="true" style="width:{sw}px;height:{sh}px"></video>{covers}</div>'
        if layout == "center":
            x, y = place("#cam", base, sw / 2, sh / 2)
            js.append(f'tl.set("#cam", {{x:{x:.1f}, y:{y:.1f}, scale:{base:.4f}}}, 0);')
        elif layout == "focus":
            for i, (ft, cx, cy, z) in enumerate(clip["focus"]):
                k = base * z
                x, y = place("#cam", k, cx, cy)
                if i == 0:
                    js.append(f'tl.set("#cam", {{x:{x:.1f}, y:{y:.1f}, scale:{k:.4f}}}, 0);')
                else:
                    js.append(f'tl.to("#cam", {{x:{x:.1f}, y:{y:.1f}, scale:{k:.4f}, duration:.6, ease:"power2.inOut"}}, {max(0, ft - 0.3) / rate:.3f});')
        else:
            segs = json.load(open(os.path.join(spec_dir, clip["speakers"])))
            for s in segs:
                x, y = place("#cam", base, clip[s["speaker"]], sh / 2)
                js.append(f'tl.set("#cam", {{x:{x:.1f}, y:{y:.1f}, scale:{base:.4f}}}, {s["start"] / rate:.3f});')
    elif layout == "stack":
        k = W / sw
        vh = sh * k
        top = round(H * 0.5 - vh / 2 - (60 if H > W else 0))
        cap_top = int(top + vh + 70)
        body = (f'<div style="position:absolute;inset:0;background:{t["dark"]}"></div>'
                f'<div style="position:absolute;left:-200px;top:{top - 400}px;width:1500px;height:1500px;border-radius:50%;background:radial-gradient(circle,{t["ink"]}55,{t["ink"]}00 65%)"></div>'
                f'<video id="v" class="clip" src="assets/{os.path.basename(media)}" {vid} data-track-index="0" data-has-audio="true" '
                f'style="position:absolute;left:0;top:{top}px;width:{W}px;height:{vh:.0f}px;border-radius:0"></video>'
                f'<div style="position:absolute;left:0;top:{top}px;width:{W}px;height:{vh:.0f}px">{covers}</div>')
        clip.setdefault("_title_top", max(60, top - 330))
    elif layout == "split":
        segs = json.load(open(os.path.join(spec_dir, clip["speakers"])))
        th = H // 2
        tiles = ""
        for side in ("left", "right"):
            bx, by, bw, bh = clip["boxes"][side]
            k = max(W / bw, th / bh)
            x = W / 2 - (bx + bw / 2) * k
            y = th / 2 - (by + bh / 2) * k
            audio = 'data-has-audio="true"' if side == "left" else "muted"
            tiles += (f'<div id="tile-{side}" style="position:absolute;left:0;top:0;width:{W}px;height:{th}px;overflow:hidden">'
                      f'<video id="v-{side}" class="clip" src="assets/{os.path.basename(media)}" {vid} data-track-index="{0 if side == "left" else 1}" {audio} '
                      f'style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{sw * k:.1f}px;height:{sh * k:.1f}px"></video></div>')
        body = tiles
        cap_top = th - 60
        for s in segs:
            top_side = s["speaker"]
            other = "right" if top_side == "left" else "left"
            js.append(f'tl.set("#tile-{top_side}", {{y:0}}, {s["start"] / rate:.3f}); tl.set("#tile-{other}", {{y:{th}}}, {s["start"] / rate:.3f});')
    else:
        sys.exit(f"error: unknown layout {layout!r}")

    if clip.get("title"):
        tt = clip.get("_title_top", 110)
        body += (f'<div id="ttl" style="position:absolute;left:70px;right:70px;top:{tt}px;text-align:center">'
                 f'<span style="display:inline;padding:10px 22px;line-height:1.45;border-radius:14px;background:{t["paper"]};color:{t["dark"]};'
                 f'font:600 {58 if H > W else 50}px {t["head_font"]};box-decoration-break:clone;-webkit-box-decoration-break:clone">{E(clip["title"])}</span></div>')
        js.append('tl.fromTo("#ttl", {opacity:0, y:-20}, {opacity:1, y:0, duration:.45, ease:"back.out(1.6)"}, .1);')

    if words is not None and clip.get("captions", True):
        caps = ""
        chunks = caption_chunks(words, clip, spec.get("captions", {}), rate)
        for i, c in enumerate(chunks):
            s0 = c[0]["t"]
            e0 = min(c[-1]["e"] + 0.35, chunks[i + 1][0]["t"] if i + 1 < len(chunks) else dur)
            ws = " ".join(f'<span class="w" id="w{i}_{j}">{E(w["w"])}</span>' for j, w in enumerate(c))
            caps += f'<div class="cap" id="c{i}">{ws}</div>'
            js.append(f'tl.set("#c{i}",{{autoAlpha:1}},{s0});tl.set("#c{i}",{{autoAlpha:0}},{min(e0, dur)});')
            for j, w in enumerate(c):
                js.append(f'tl.set("#w{i}_{j}",{{className:"w on"}},{w["t"]});tl.set("#w{i}_{j}",{{className:"w"}},{w["e"]});')
        body += caps

    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {t['dark']}; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      .cap {{ position: absolute; left: 50%; top: {cap_top}px; transform: translateX(-50%); visibility: hidden; opacity: 0; white-space: nowrap;
        font: 800 {72 if H > W else 58}px/1.15 {t['body_font']}, sans-serif; color: #fff;
        {"" if layout == "stack" else f"padding: 12px 22px 16px; border-radius: 24px; background: {t['dark']}e6;"} }}
      .w {{ display: inline-block; padding: 0 10px; border-radius: 14px; }}
      .w.on {{ background: {t['ink']}; text-shadow: none; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}">
      {body}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join('      ' + j for j in js)}
      tl.set({{}}, {{}}, {dur});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    open(os.path.join(proj, "index.html"), "w").write(index)
    for name, data in (("hyperframes.json", {"paths": {"assets": "assets"}}), ("meta.json", {"id": clip["name"], "name": clip["name"]})):
        if not os.path.exists(os.path.join(proj, name)):
            json.dump(data, open(os.path.join(proj, name), "w"), indent=2)
    return proj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips")
    ap.add_argument("--only", nargs="*", help="build only these clip names")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--quality", default="looks", choices=["draft", "looks", "delivery"])
    a = ap.parse_args()
    require("ffprobe")
    spec_dir = os.path.dirname(os.path.abspath(a.clips))
    spec = json.load(open(a.clips))
    theme = dict(THEME)
    if spec.get("theme") and os.path.exists(os.path.join(spec_dir, spec["theme"])):
        theme.update(json.load(open(os.path.join(spec_dir, spec["theme"]))))
    words = load_words(os.path.join(spec_dir, spec["words"])) if spec.get("words") else None
    version = os.environ.get("MV_HYPERFRAMES_VERSION", "latest")
    renders = os.path.join(spec_dir, spec.get("out", "clips"), "renders")
    for clip in spec["clips"]:
        if a.only and clip["name"] not in a.only:
            continue
        proj = build(spec_dir, spec, clip, theme, words)
        print(f"built {proj}")
        subprocess.run(["npx", "--yes", f"hyperframes@{version}", "lint"], cwd=proj, check=False)
        if a.render:
            os.makedirs(renders, exist_ok=True)
            out = os.path.join(renders, f"{clip['name']}.mp4")
            subprocess.run(["npx", "--yes", f"hyperframes@{version}", "render", "-o", out, "-q", a.quality,
                            "--video-frame-format", "png"], cwd=proj, check=True)
            print(f"rendered {out}")


if __name__ == "__main__":
    main()
