#!/usr/bin/env python3
# ruff: noqa: E501  (inline HTML/CSS/JS templates)
"""Build (and optionally render) social clips from a longer video, one HyperFrames project per clip.

Usage: clips_make.py CLIPS_JSON [--only NAME ...] [--render] [--quality draft|looks]

clips.json (paths relative to the file):
  {
    "source": "edit/assets/spine.mp4",      # the video to cut from
    "words": "work/spine_words.json",       # word timings for that video (optional; no captions without it)
    "theme": "brand/theme.json",            # optional brand colors and fonts
    "format": "9:16",                       # 9:16 (1080x1920), 1:1 (1080x1080), 16:9 (1920x1080) or any "WxH" like "1200x1200"
    "loudness": -14,                        # optional: normalize each render to this LUFS (quiet event or room audio)
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
          eases between points (follow the cursor or the part of the UI being discussed).
          Zoom below 1 shows a wider window than 9:16 allows: the picture sits at the
          bottom and leaves a band above it for the title. 0.75-0.9 fits a whole chat or
          document column at a readable size.
  pan     "speakers": "path.json" from clips_speakers.py, "left": x, "right": x (source
          pixel centers of each face); hard cuts to whoever is talking
  split   "speakers" as above, "boxes": {"left": [x,y,w,h], "right": [x,y,w,h]} around
          each face; both on screen, active speaker on top
  event   wide event or sports footage with a broadcast score bar (fight nights, games,
          races). The full-width shot sits in a band over a blurred copy of itself, the
          score bar is cut out and pinned under the band so it's always readable, and
          "punch": [[from, to, x, y, zoom], ...] (clip-local seconds, source pixels,
          zoom 1.3-1.6 on 720p) punches in on big moves. Spec-level "scorebar":
          [x, y, w, h] in source pixels, optional "scorebar_scale" (default 1.35) and
          "margin" (px on every side; default 4.5% of the short side). Tag, title,
          picture and sponsor are spaced evenly down the frame; callouts pop in
          over the bottom of the picture.

Extras for any layout:
  "tag": "GAME 3 · HAWKS VS RAVENS"         small pill above the title
  "callouts": [[t, "TAKEDOWN", "+2"], ...]  pop-in labels at clip-local seconds
Spec-level extras:
  "sponsor": {"logo": "brand/logo.png", "label": "Presented by"}   small credit near the bottom
  "endcard": {"logo": "brand/logo.png", "line": "Tagline", "dur": 2.2}  added after the clip
  theme "font_files": {"Family": "brand/fonts/x.woff2"} (or {"Family": {"400": file, "900": file}}
  for static weights) are bundled so renders use the brand font.

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
    fmt = spec.get("format", "9:16")
    W, H = SIZES[fmt] if fmt in SIZES else tuple(int(n) for n in fmt.lower().split("x"))
    tall = H > W * 1.3
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

    def asset(rel):  # copy a brand file into the clip project and return its project path
        srcf = os.path.normpath(os.path.join(spec_dir, rel))
        dst = os.path.join(proj, "assets", "brand", os.path.basename(srcf))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(srcf):
            shutil.copy2(srcf, dst)
        return "assets/brand/" + os.path.basename(srcf)

    faces = ""  # a family maps to one file (any weight) or {"400": file, "900": file}
    for fam, f in t.get("font_files", {}).items():
        for wt, p in (f.items() if isinstance(f, dict) else [("100 900", f)]):
            faces += f"@font-face {{ font-family: '{fam}'; src: url('{asset(p)}') format('woff2'); font-weight: {wt}; }}\n      "
    ec = spec.get("endcard")
    clip_dur = dur
    if ec:
        dur = round(dur + float(ec.get("dur", 2.2)), 3)  # footage keeps rolling under the card
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
    elif layout == "event":
        # One column with the same margin on all four sides: header, picture + score bar,
        # a fixed callout slot and the sponsor credit, with equal gaps between them.
        sb = spec.get("scorebar")
        M = int(spec.get("margin", round(min(W, H) * 0.045)))
        BW = W - 2 * M
        k = BW / sw
        crop_b = sb[1] if sb else sh  # band shows the picture above the score bar
        bh = round(crop_b * k)
        ss = float(spec.get("scorebar_scale", 1.35))
        sbw, sbh = (sb[2] * k * ss, sb[3] * k * ss) if sb else (0, 0)
        cover = max(W / sw, H / sh) * 1.08
        mv = os.path.basename(media)
        fs_title, fs_tag, fs_co = (86, 34, 70) if tall else (76, 34, 58)
        body = (f'<video id="bg" class="clip" src="assets/{mv}" {vid} data-track-index="1" muted '
                f'style="position:absolute;left:{(W - sw * cover) / 2:.0f}px;top:{(H - sh * cover) / 2:.0f}px;width:{sw * cover:.0f}px;height:{sh * cover:.0f}px;filter:blur(34px) brightness(.5) saturate(1.2)"></video>'
                f'<div style="position:absolute;inset:0;background:linear-gradient(180deg,{t["dark"]}e6 0%,{t["deep"]}55 38%,{t["deep"]}55 62%,{t["dark"]}f2 100%)"></div>')
        items = []
        head = ""
        if clip.get("tag"):
            head += (f'<div id="tag" style="display:flex;justify-content:center"><span style="display:inline-block;padding:12px 26px 9px;border-radius:999px;background:{t["ink"]};color:#fff;'
                     f'font:800 {fs_tag}px/1 {t["head_font"]}, sans-serif;letter-spacing:.06em">{E(clip["tag"])}</span></div>')
            js.append('tl.fromTo("#tag", {opacity:0, y:-16}, {opacity:1, y:0, duration:.4, ease:"back.out(1.8)"}, .05);')
        if clip.get("title"):
            head += (f'<div id="ttl" style="margin-top:{round(fs_title * .22)}px;margin-bottom:-{round(fs_title * .18)}px;color:#fff;font:900 {fs_title}px/.92 {t["head_font"]}, sans-serif;'
                     f'text-transform:uppercase;letter-spacing:-.01em;text-shadow:0 6px 30px #0009">{E(clip["title"])}</div>')
            js.append('tl.fromTo("#ttl", {opacity:0, y:24}, {opacity:1, y:0, duration:.5, ease:"power3.out"}, .15);')
        if head:
            items.append(f'<div style="text-align:center">{head}</div>')
        media_html = (f'<div id="band" style="position:relative;width:{BW}px;height:{bh}px;overflow:hidden;box-shadow:0 24px 60px #0008">'
                      f'<div id="cam" style="position:absolute;left:0;top:0;width:{sw}px;height:{sh}px;transform-origin:0 0">'
                      f'<video id="v" class="clip" src="assets/{mv}" {vid} data-track-index="0" data-has-audio="true" style="width:{sw}px;height:{sh}px"></video>{covers}</div>'
                      f'<div id="flash" style="position:absolute;inset:0;background:#fff;opacity:0"></div></div>')
        if sb:
            sk = k * ss
            media_html += (f'<div style="position:relative;margin:0 auto;width:{sbw:.0f}px;height:{sbh:.0f}px;overflow:hidden">'
                           f'<video id="sb" class="clip" src="assets/{mv}" {vid} data-track-index="2" muted '
                           f'style="position:absolute;left:{-sb[0] * sk:.1f}px;top:{-sb[1] * sk:.1f}px;width:{sw * sk:.1f}px;height:{sh * sk:.1f}px"></video></div>')
        media_at = len(items)
        items.append(media_html)
        js.append(f'tl.set("#cam", {{x:0, y:0, scale:{k:.4f}}}, 0);')
        for a, b, cx, cy, z in clip.get("punch", []):
            K = k * z
            x = fit(BW / 2 - cx * K, BW - sw * K, 0)
            y = fit(bh / 2 - cy * K, bh - crop_b * K, 0)
            js.append(f'tl.to("#cam", {{x:{x:.1f}, y:{y:.1f}, scale:{K:.4f}, duration:.32, ease:"power3.out"}}, {a / rate:.3f});')
            js.append(f'tl.to("#cam", {{x:0, y:0, scale:{k:.4f}, duration:.5, ease:"power2.inOut"}}, {b / rate:.3f});')
        cos = ""
        for i, co in enumerate(clip.get("callouts", [])):
            ct, label = co[0] / rate, co[1]
            pts = co[2] if len(co) > 2 else ""
            chip = f'<span style="display:inline-block;margin-left:16px;padding:10px 18px 6px;border-radius:16px;background:#fff;color:{t["ink"]}">{E(pts)}</span>' if pts else ""
            cos += (f'<div id="co{i}" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0">'
                    f'<span style="display:inline-flex;align-items:center;padding:16px {20 if pts else 34}px 16px 34px;border-radius:26px;background:{t["ink"]};color:#fff;'
                    f'font:900 {fs_co}px/1 {t["head_font"]}, sans-serif;letter-spacing:.02em;box-shadow:0 18px 50px #0007">{E(label)}{chip}</span></div>')
            js.append(f'tl.fromTo("#co{i}", {{opacity:0, scale:.55}}, {{opacity:1, scale:1, duration:.38, ease:"back.out(2.2)"}}, {ct:.3f});')
            js.append(f'tl.to("#co{i}", {{opacity:0, y:-20, duration:.35, ease:"power2.in"}}, {ct + 2.2:.3f});')
            js.append(f'tl.set("#flash", {{opacity:.32}}, {ct:.3f}); tl.to("#flash", {{opacity:0, duration:.3, ease:"power2.out"}}, {ct + 0.01:.3f});')
        if cos:  # callouts sit on the picture, near its bottom edge, so no empty slot opens up in the column
            pill = fs_co + 48  # 16px padding + chip (font + 16)
            items[media_at] += f'<div style="position:absolute;left:0;top:{bh - pill - round(bh * .05)}px;width:{BW}px;height:{pill}px">{cos}</div>'
        items[media_at] = f'<div style="position:relative">{items[media_at]}</div>'
        sp = spec.get("sponsor")
        if sp:
            items.append(f'<div id="spn" style="display:flex;align-items:center;justify-content:center;gap:22px">'
                         f'<span style="font:700 {30 if not tall else 26}px/1 {t["head_font"]}, sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#ffffffcc">{E(sp.get("label", "Presented by"))}</span>'
                         f'<img src="{asset(sp["logo"])}" style="height:{sp.get("height", 96) * (1 if tall else .95):.0f}px"></div>')
            js.append('tl.fromTo("#spn", {opacity:0}, {opacity:.95, duration:.6}, .6);')
        body += (f'<div style="position:absolute;inset:{M}px;display:flex;flex-direction:column;align-items:center;justify-content:space-between">'
                 + "".join(items) + '</div>')
        clip = {**clip, "title": None, "callouts": []}
    else:
        sys.exit(f"error: unknown layout {layout!r}")

    for i, co in enumerate(clip.get("callouts", [])):
        ct, label = co[0] / rate, co[1]
        pts = co[2] if len(co) > 2 else ""
        chip = f'<span style="display:inline-block;margin-left:16px;padding:10px 18px 6px;border-radius:16px;background:#fff;color:{t["ink"]}">{E(pts)}</span>' if pts else ""
        body += (f'<div id="co{i}" style="position:absolute;left:0;right:0;top:{int(H * 0.62)}px;text-align:center;opacity:0">'
                 f'<span style="display:inline-flex;align-items:center;padding:16px 20px 16px 34px;border-radius:26px;background:{t["ink"]};color:#fff;'
                 f'font:900 {70 if tall else 58}px/1 {t["head_font"]}, sans-serif;letter-spacing:.02em;box-shadow:0 18px 50px #0007">{E(label)}{chip}</span></div>')
        js.append(f'tl.fromTo("#co{i}", {{opacity:0, scale:.55}}, {{opacity:1, scale:1, duration:.38, ease:"back.out(2.2)"}}, {ct:.3f});')
        js.append(f'tl.to("#co{i}", {{opacity:0, y:-20, duration:.35, ease:"power2.in"}}, {ct + 2.2:.3f});')

    sp = spec.get("sponsor")
    if sp and layout != "event":
        body += (f'<div id="spn" style="position:absolute;left:0;right:0;top:{int(H * 0.82)}px;display:flex;align-items:center;justify-content:center;gap:22px;opacity:.95">'
                 f'<span style="font:700 26px/1 {t["head_font"]}, sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#ffffffcc">{E(sp.get("label", "Presented by"))}</span>'
                 f'<img src="{asset(sp["logo"])}" style="height:{sp.get("height", 96)}px"></div>')
        js.append('tl.fromTo("#spn", {opacity:0}, {opacity:.95, duration:.6}, .6);')

    if ec:
        lg = f'<img src="{asset(ec["logo"])}" style="width:520px">' if ec.get("logo") else ""
        line = f'<div style="margin-top:46px;font:900 64px/1.05 {t["head_font"]}, sans-serif;color:#fff;text-transform:uppercase;letter-spacing:.02em">{E(ec.get("line", ""))}</div>' if ec.get("line") else ""
        body += (f'<div id="end" style="position:absolute;inset:0;background:{t["deep"]};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;opacity:0">{lg}{line}</div>')
        js.append(f'tl.to("#end", {{opacity:1, duration:.45, ease:"power2.out"}}, {clip_dur:.3f});')
        js.append(f'tl.fromTo("#end img, #end div", {{y:30}}, {{y:0, duration:.6, ease:"power3.out", stagger:.08}}, {clip_dur:.3f});')

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
      {faces}* {{ margin: 0; padding: 0; box-sizing: border-box; }}
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
            lufs = spec.get("loudness")
            if lufs is not None:  # quiet room or event audio: bring it up to a social-feed level
                tmp = out + ".tmp.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "copy", "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11",
                                "-c:a", "aac", "-b:a", "192k", tmp], check=True)
                os.replace(tmp, out)
            print(f"rendered {out}")


if __name__ == "__main__":
    main()
