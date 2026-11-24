#!/usr/bin/env python3
# ruff: noqa: E501  (this file is mostly inline HTML/CSS/JS templates; wrapping them hurts more than it helps)
"""Build the HyperFrames composition for a tutorial edit from work/plan.json.

Writes edit/index.html and one sub-composition per overlay in edit/compositions/.
Never hand-edit those files: change plan.json and run this again.

Usage: tutorial_gen.py PROJECT

All times in plan.json are spine seconds (see tutorial_cut.py). The format is in the
tutorial-edit skill: references/plan-format.md. Derived automatically from the overlays:
  - side panels push the screen into a framed card on the left
  - the music lifts on chapter cards, fast-forwards and the end card
  - captions hide under the quote, kinetic and end cards
  - whoosh / pop / tick sound effects on entrances
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys

THEME = {  # neutral defaults; override any key in plan["theme"] (e.g. from the client's brand guide)
    "ink": "#455CFF", "deep": "#1A33AF", "paper": "#F6F8FF", "line": "#D9E8FF", "dark": "#1F1F2B",
    "soft": "#9696AE", "warn": "#E5484D", "bg": "#E9EEFF", "chip_label": "#8FA0FF",
    "head_font": "Poppins", "body_font": "Inter", "note_font_file": "assets/fonts/caveat-latin.woff2",
    "wordmark": "", "logo": "",
}
E = html.escape


class Build:
    def __init__(self, project: str):
        self.project = project
        self.edit = os.path.join(project, "edit")
        self.work = os.path.join(project, "work")
        self.comp = os.path.join(self.edit, "compositions")
        os.makedirs(self.comp, exist_ok=True)
        self.plan = json.load(open(os.path.join(self.work, "plan.json")))
        brand_file = os.path.join(project, "brand", "theme.json")
        brand = json.load(open(brand_file)) if os.path.exists(brand_file) else {}
        self.t = {**THEME, **brand, **self.plan.get("theme", {})}
        logo = self.t.get("logo", "")
        if logo and not logo.startswith("assets/"):  # brand/logo.svg -> edit/assets/brand/logo.svg
            src = os.path.join(project, logo)
            if os.path.exists(src):
                os.makedirs(os.path.join(self.edit, "assets", "brand"), exist_ok=True)
                shutil.copy2(src, os.path.join(self.edit, "assets", "brand", os.path.basename(src)))
                self.t["logo"] = "assets/brand/" + os.path.basename(src)
            else:
                print(f"warning: logo {src} not found; using the wordmark text")
                self.t["logo"] = ""
        self.dur = round(json.load(open(os.path.join(self.work, "spine_map.json")))[-1]["end"], 3)
        self.hosts: list[str] = []
        self.sfx: list[tuple[float, str]] = []
        self.lifts: list[tuple[float, float]] = []
        self.push: list[tuple[float, float]] = []
        self.hide: list[tuple[float, float]] = [tuple(x) for x in self.plan.get("captions", {}).get("hide", [])]
        self.agenda = self.plan.get("agenda", [])

    # ------------------------------------------------------------------ plumbing
    def css_base(self) -> str:
        t = self.t
        faces = "".join(f"@font-face {{ font-family: '{fam}'; src: url('{src}') format('woff2'); }}\n"
                        for fam, src in t.get("font_files", {}).items())
        return f"""
{faces}@font-face {{ font-family: 'Hand'; src: url('{t['note_font_file']}') format('woff2'); font-weight: 400 700; }}
#root {{ position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: hidden; font-family: {t['body_font']}, sans-serif; color: {t['dark']}; }}
.paper {{ background: {t['paper']}; }}
.dots {{ background-image: radial-gradient({t['line']} 1.6px, transparent 1.6px); background-size: 34px 34px; }}
.head {{ font-family: {t['head_font']}, sans-serif; }}
.note {{ font-family: 'Hand', cursive; color: {t['ink']}; font-weight: 600; }}
.label {{ font-weight: 600; letter-spacing: .12em; text-transform: uppercase; font-size: 24px; color: {t['ink']}; }}
.card {{ position: absolute; background: {t['paper']}; border-radius: 28px; box-shadow: 0 30px 80px rgba(20,24,60,.28); }}
.chip {{ position: absolute; display: flex; align-items: center; gap: 18px; padding: 20px 30px; border-radius: 999px;
  background: {t['dark']}f0; color: {t['paper']}; font: 500 32px/1.2 {t['body_font']}, sans-serif; box-shadow: 0 16px 40px rgba(10,10,30,.35); }}
.chip b {{ font-weight: 700; letter-spacing: .1em; font-size: 22px; color: {t['chip_label']}; text-transform: uppercase; }}
.chip.warn b {{ color: {t['warn']}; }}
svg .ink {{ fill: none; stroke: {t['ink']}; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
svg .ink2 {{ fill: none; stroke: {t['soft']}; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
.d {{ stroke-dasharray: 1; stroke-dashoffset: 1; }}
"""

    def sub(self, cid: str, dur: float, body: str, script: str, css: str = "") -> None:
        # Selectors are scoped to this composition so overlays can reuse class names.
        script = re.sub(r'(tl\.(?:fromTo|to|set|from))\("([^"]+)"', r'\1(Q("\2")', script)
        doc = f"""<!doctype html>
<html>
  <head><meta charset="UTF-8" /></head>
  <body>
    <template>
      <style>{self.css_base()}{css}</style>
      <div id="root" data-composition-id="{cid}" data-width="1920" data-height="1080" data-duration="{dur}">
{body}
      </div>
      <script>
        (function () {{
          const tl = gsap.timeline({{ paused: true }});
          const D = {dur};
          const HOST = document.querySelector('[data-composition-id="{cid}"]');
          const Q = (s) => s === "#root" ? (HOST.querySelector("#root") || HOST) : HOST.querySelectorAll(s);
{script}
          window.__timelines["{cid}"] = tl;
        }})();
      </script>
    </template>
  </body>
</html>
"""
        open(os.path.join(self.comp, f"{cid}.html"), "w").write(doc)

    def mount(self, cid: str, start: float, dur: float, track: int, kind: str = "") -> None:
        extra = ' data-track-kind="captions"' if kind == "captions" else ""
        self.hosts.append(f'    <div id="{cid}" class="clip" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html"{extra} '
                          f'data-start="{start}" data-duration="{dur}" data-track-index="{track}" data-width="1920" data-height="1080"></div>')

    def wordmark(self, size: int, color: str) -> str:
        t = self.t
        if t["logo"]:
            return f'<img src="{E(t["logo"])}" style="height:{size * 1.3}px" alt="" />'
        return f'<span class="head" style="font-weight:600;font-size:{size}px;color:{color};letter-spacing:-.02em">{E(t["wordmark"])}</span>'

    # ------------------------------------------------------------------ agenda
    def agenda_list(self, current: int | None, left: int = 1060, top: int = 250) -> str:
        rows = ""
        for i, item in enumerate(self.agenda, 1):
            state = "todo" if current is None else ("done" if i < current else "now" if i == current else "next")
            mark = "&#10003;" if state == "done" else f"{i:02d}"
            rows += f'<div class="ar ar{i} {state}"><span class="an">{mark}</span><span class="at">{E(item)}</span></div>'
        return f'<div class="agl" style="position:absolute;left:{left}px;top:{top}px;width:720px">{rows}</div>'

    def agenda_css(self) -> str:
        t = self.t
        return f""".agl .ar{{display:flex;align-items:center;gap:26px;height:84px;padding:0 26px;border-radius:20px;margin-bottom:10px;font:600 36px {t['body_font']};color:{t['dark']}}}
.agl .an{{flex:none;width:58px;height:58px;border-radius:50%;border:3px solid {t['ink']};color:{t['ink']};font:600 24px {t['head_font']};display:flex;align-items:center;justify-content:center}}
.agl .ar.done,.agl .ar.next{{color:{t['soft']}}}.agl .ar.done .an{{background:{t['line']};border-color:{t['line']};font-size:28px}}
.agl .ar.next .an{{border-color:{t['line']};color:{t['soft']}}}
.agl .ar.now{{background:{t['ink']};color:#fff;box-shadow:0 16px 40px rgba(0,0,0,.18)}}.agl .ar.now .an{{background:#fff;border-color:#fff;color:{t['ink']}}}"""

    def o_agenda(self, cid: str, o: dict) -> None:
        start, dur = o["start"], o["dur"]
        body = f"""        <div class="paper dots" style="position:absolute;inset:0"></div>
        <div class="wrap" style="position:absolute;inset:0">
          <div class="kick label" style="position:absolute;left:150px;top:250px">{E(o.get('kicker', ''))}</div>
          <h1 class="t1 head" style="position:absolute;left:146px;top:300px;width:800px;margin:0;font-weight:600;font-size:86px;line-height:1.08;letter-spacing:-.02em">{E(o['title'])}</h1>
          <div class="t2 note" style="position:absolute;left:156px;top:610px;font-size:56px;transform:rotate(-2deg);transform-origin:left">{E(o.get('note', ''))}</div>
          <div class="wm" style="position:absolute;left:150px;top:860px">{self.wordmark(36, self.t['dark'])}</div>
          <div class="cov label" style="position:absolute;left:1086px;top:196px">{E(o.get('list_label', "What we'll cover"))}</div>
          {self.agenda_list(None)}
        </div>"""
        sc = ('          tl.fromTo(".wrap", {scale:1}, {scale:1.03, transformOrigin:"50% 50%", duration:D, ease:"none"}, 0);\n'
              '          tl.fromTo(".kick", {opacity:0, y:14}, {opacity:1, y:0, duration:.4, ease:"power3.out"}, .1);\n'
              '          tl.fromTo(".t1", {opacity:0, y:34}, {opacity:1, y:0, duration:.6, ease:"power3.out"}, .2);\n'
              '          tl.fromTo(".t2", {opacity:0, y:12}, {opacity:1, y:0, duration:.45}, .7);\n'
              '          tl.fromTo(".wm", {opacity:0}, {opacity:1, duration:.5}, .9);\n'
              '          tl.fromTo(".cov", {opacity:0, y:12}, {opacity:1, y:0, duration:.4}, 1.0);\n')
        for i in range(1, len(self.agenda) + 1):
            sc += f'          tl.fromTo(".ar{i}", {{opacity:0, x:40}}, {{opacity:1, x:0, duration:.45, ease:"power3.out"}}, {1.2 + (i - 1) * 0.45:.2f});\n'
            self.sfx.append((start + 1.2 + (i - 1) * 0.45, "tick"))
        sc += '          tl.to("#root", {clipPath:"inset(0 100% 0 0)", duration:.45, ease:"expo.in"}, D-.45);'
        self.sub(cid, dur, body, sc, self.agenda_css())
        self.mount(cid, start, dur, 20)
        self.sfx.append((start + 0.25, "whoosh"))

    def o_chapter(self, cid: str, o: dict) -> None:
        start, dur, step = o["start"], o.get("dur", 2.0), o["step"]
        has_list = bool(self.agenda)
        width = 820 if has_list else 1500
        body = f"""        <div class="paper dots" style="position:absolute;inset:0"></div>
        <div style="position:absolute;left:150px;top:0;bottom:0;width:{width}px;display:flex;flex-direction:column;justify-content:center">
          <div class="num head" style="font-weight:600;font-size:220px;line-height:1;color:{self.t['deep']};letter-spacing:-.04em">{step:02d}</div>
          <div class="bar" style="width:120px;height:8px;border-radius:4px;background:{self.t['ink']};margin:26px 0 30px 6px"></div>
          <h2 class="ttl head" style="margin:0;font-weight:600;font-size:88px;line-height:1.06;letter-spacing:-.02em">{E(o.get('title') or self.agenda[step - 1])}</h2>
          <div class="nt note" style="font-size:56px;margin-top:22px;transform:rotate(-2deg);transform-origin:left">{E(o.get('note', ''))}</div>
        </div>
        {self.agenda_list(step, 1060, 255) if has_list else ''}"""
        sc = """          tl.fromTo("#root", {clipPath:"inset(0 0 0 100%)"}, {clipPath:"inset(0 0 0 0%)", duration:.45, ease:"expo.out"}, 0);
          tl.fromTo(".num", {opacity:0, x:-40}, {opacity:1, x:0, duration:.5, ease:"power3.out"}, .12);
          tl.fromTo(".bar", {scaleX:0, transformOrigin:"left"}, {scaleX:1, duration:.45, ease:"power3.out"}, .25);
          tl.fromTo(".ttl", {opacity:0, y:30}, {opacity:1, y:0, duration:.5, ease:"power3.out"}, .3);
          tl.fromTo(".nt", {opacity:0, y:12}, {opacity:1, y:0, duration:.45, ease:"power2.out"}, .6);
          tl.fromTo(".agl .ar", {opacity:0, x:30}, {opacity:1, x:0, duration:.4, ease:"power3.out", stagger:.05}, .15);
          tl.fromTo(".agl .now", {scale:.94}, {scale:1, duration:.5, ease:"back.out(2)"}, .45);
          tl.to("#root", {clipPath:"inset(0 100% 0 0)", duration:.4, ease:"expo.in"}, D-.4);"""
        self.sub(cid, dur, body, sc, self.agenda_css())
        self.mount(cid, start, dur, 20)
        self.sfx.append((start, "whoosh"))
        self.lifts.append((start, start + dur))

    # ------------------------------------------------------------------ full-frame cards
    def o_quote(self, cid: str, o: dict) -> None:
        start, dur, t = o["start"], o["dur"], self.t
        lines = "".join(f'<div style="overflow:hidden"><div class="qi">{line}</div></div>' for line in o["lines"])  # may hold <span class="hl">
        body = f"""        <div style="position:absolute;inset:0;background:{t['dark']}"></div>
        <div class="glow" style="position:absolute;width:1300px;height:1300px;left:-300px;top:-200px;border-radius:50%;background:radial-gradient(circle,{t['ink']}73,{t['ink']}00 65%)"></div>
        <div class="qm head" style="position:absolute;left:150px;top:150px;font-size:220px;line-height:1;color:{t['ink']};font-weight:600">&ldquo;</div>
        <div class="head" style="position:absolute;left:150px;top:330px;width:1600px;font-weight:600;font-size:92px;line-height:1.12;color:{t['paper']};letter-spacing:-.02em">{lines}</div>
        <div class="nt note" style="position:absolute;left:156px;top:820px;font-size:56px;color:{t['chip_label']};transform:rotate(-2deg)">{E(o.get('note', ''))}</div>"""
        hi = o.get("hi_at", 1.5)
        sc = f"""          tl.fromTo("#root", {{opacity:0}}, {{opacity:1, duration:.35}}, 0);
          tl.fromTo(".glow", {{x:-80}}, {{x:80, duration:D, ease:"none"}}, 0);
          tl.fromTo(".qm", {{opacity:0, scale:.6}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(1.6)"}}, .1);
          tl.fromTo(".qi", {{yPercent:110}}, {{yPercent:0, duration:.6, ease:"power3.out", stagger:.12}}, .2);
          tl.fromTo(".hl", {{backgroundSize:"0% 100%"}}, {{backgroundSize:"100% 100%", duration:.6, ease:"power2.inOut"}}, {hi});
          tl.fromTo(".nt", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.45}}, {hi}+.4);
          tl.to("#root", {{opacity:0, duration:.35}}, D-.35);"""
        css = f".hl{{background:linear-gradient({t['ink']},{t['ink']}) no-repeat 0 100%;background-size:0% 100%;padding:0 .12em;border-radius:10px}}"
        self.sub(cid, dur, body, sc, css)
        self.mount(cid, start, dur, 20)
        self.sfx.append((start, "whoosh"))
        self.hide.append((start, start + dur))

    def o_kinetic(self, cid: str, o: dict) -> None:
        start, dur, t = o["start"], o["dur"], self.t
        lines = ""
        for i, b in enumerate(o["beats"]):
            size = b.get("size", 150)
            color = t["chip_label"] if b.get("accent") else t["paper"]
            lines += (f'<div class="k k{i} head" style="font-weight:600;font-size:{size}px;line-height:1.08;letter-spacing:-.02em;'
                      f'color:{color};margin-top:{b.get("gap", 0)}px">{E(b["text"])}</div>')
        body = f'        <div style="position:absolute;inset:0;background:{t["dark"]}"></div>\n        <div style="position:absolute;left:150px;top:300px;width:1600px">{lines}</div>'
        sc = '          tl.fromTo("#root", {opacity:0}, {opacity:1, duration:.25}, 0);\n'
        for i, b in enumerate(o["beats"]):
            sc += f'          tl.fromTo(".k{i}", {{opacity:0, y:50}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, {b["t"]});\n'
            self.sfx.append((start + b["t"], "pop"))
        sc += '          tl.to("#root", {opacity:0, duration:.35}, D-.35);'
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 20)
        self.sfx.append((start, "whoosh"))
        self.hide.append((start, start + dur))

    def o_end(self, cid: str, o: dict) -> None:
        start, t = o["start"], self.t
        dur = o.get("dur", round(self.dur - start, 3))
        body = f"""        <div style="position:absolute;inset:0;background:{t['dark']}"></div>
        <div class="glow" style="position:absolute;width:1500px;height:1500px;left:210px;top:-200px;border-radius:50%;background:radial-gradient(circle,{t['ink']}80,{t['ink']}00 62%)"></div>
        <div class="wm" style="position:absolute;left:0;right:0;top:470px;text-align:center">{self.wordmark(76, t['paper'])}</div>
        <div class="cta" style="position:absolute;left:0;right:0;top:620px;text-align:center;font:500 36px {t['body_font']};color:{t['soft']}">{E(o.get('cta', ''))}</div>"""
        sc = """          tl.fromTo("#root", {opacity:0}, {opacity:1, duration:.4}, 0);
          tl.fromTo(".wm", {opacity:0, y:20, scale:.9}, {opacity:1, y:0, scale:1, duration:.6, ease:"back.out(1.5)"}, .2);
          tl.fromTo(".cta", {opacity:0}, {opacity:1, duration:.5}, .8);
          tl.fromTo(".glow", {scale:.9}, {scale:1.05, duration:D, ease:"none"}, 0);"""
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 20)
        self.sfx.append((start, "whoosh"))
        self.lifts.append((start, self.dur))
        self.hide.append((start, self.dur + 1))

    # ------------------------------------------------------------------ side panels
    def o_panel(self, cid: str, o: dict) -> None:
        start, dur, t = o["start"], o["dur"], self.t
        alert = o.get("mark") == "alert"
        rows = ""
        for i, it in enumerate(o["items"]):
            at, text, subtext = (it + ["", ""])[:3] if isinstance(it, list) else (it["t"], it["text"], it.get("sub", ""))
            bg, fg, mark = (("#FFE7E8", t["warn"], "!") if alert else (t["ink"], "#fff", str(i + 1)))
            badge = (f'<div class="bd" style="flex:none;width:50px;height:50px;border-radius:50%;background:{bg};color:{fg};'
                     f'font:600 26px {t["head_font"]};display:flex;align-items:center;justify-content:center">{mark}</div>')
            sub_html = f'<div style="font:500 23px/1.35 {t["body_font"]};color:#5B5B73;margin-top:6px">{E(subtext)}</div>' if subtext else ""
            rows += (f'<div class="row r{i}" style="display:flex;gap:22px;align-items:flex-start;margin-top:26px">{badge}'
                     f'<div><div style="font:600 31px/1.25 {t["body_font"]}">{E(text)}</div>{sub_html}</div></div>')
        body = f"""        <div class="card pnl" style="left:1150px;top:90px;width:680px;height:860px;padding:56px 54px;box-sizing:border-box">
          <div class="label">{E(o.get('kicker', ''))}</div>
          <div class="head" style="font-weight:600;font-size:52px;line-height:1.1;margin-top:14px;letter-spacing:-.015em">{E(o['title'])}</div>
          <div style="height:2px;background:{t['line']};margin-top:28px"></div>
          {rows}
        </div>"""
        sc = ('          tl.fromTo(".pnl", {x:760}, {x:0, duration:.7, ease:"expo.out"}, 0);\n'
              '          tl.to(".pnl", {x:760, duration:.5, ease:"expo.in"}, D-.5);\n')
        for i, it in enumerate(o["items"]):
            at = it[0] if isinstance(it, list) else it["t"]
            sc += f'          tl.fromTo(".r{i}", {{opacity:0, x:30}}, {{opacity:1, x:0, duration:.45, ease:"power3.out"}}, {at});\n'
            sc += f'          tl.fromTo(".r{i} .bd", {{scale:0}}, {{scale:1, duration:.4, ease:"back.out(2)"}}, {at}+.05);\n'
            self.sfx.append((start + at, "tick"))
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 12)
        self.sfx.append((start, "whoosh"))
        self.push.append((start, start + dur))

    def o_stat(self, cid: str, o: dict) -> None:
        start, dur, t = o["start"], o["dur"], self.t
        rows = "".join(
            f'<div class="sr s{i}" style="display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-top:2px solid {t["line"]};font:600 30px {t["body_font"]}">'
            f'<span>{E(a)}</span><span style="color:{t["ink"]}">{E(b)}</span></div>' for i, (_, a, b) in enumerate(o.get("rows", [])))
        body = f"""        <div class="card pnl" style="left:1150px;top:90px;width:680px;height:860px;padding:56px 54px;box-sizing:border-box">
          <div class="label">{E(o.get('kicker', ''))}</div>
          <div style="display:flex;align-items:baseline;gap:18px;margin-top:20px">
            <div class="big head" style="font-weight:600;font-size:210px;line-height:.95;color:{t['deep']};letter-spacing:-.04em">{o['value']}</div>
            <div class="head" style="font-weight:600;font-size:46px">{E(o.get('unit', ''))}</div></div>
          <div class="note hlt" style="font-size:50px;margin:18px 0 26px;transform:rotate(-1.5deg)">{E(o.get('note', ''))}</div>
          {rows}
        </div>"""
        v = o["value"] if isinstance(o["value"], (int, float)) else 0
        sc = ('          tl.fromTo(".pnl", {x:760}, {x:0, duration:.7, ease:"expo.out"}, 0);\n'
              '          tl.to(".pnl", {x:760, duration:.5, ease:"expo.in"}, D-.5);\n'
              f'          tl.fromTo(".hlt", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.45}}, {o.get("note_at", 1.5)});\n')
        if v:
            sc += (f'          const n = {{v:0}}; tl.fromTo(n, {{v:0}}, {{v:{v}, duration:1.1, ease:"power2.out", '
                   'onUpdate:()=>{Q(".big")[0].textContent=Math.round(n.v)}}, .3);\n')
        for i, (at, *_r) in enumerate(o.get("rows", [])):
            sc += f'          tl.fromTo(".s{i}", {{opacity:0, x:30}}, {{opacity:1, x:0, duration:.4, ease:"power3.out"}}, {at});\n'
            self.sfx.append((start + at, "tick"))
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 12)
        self.sfx.append((start, "whoosh"))
        self.push.append((start, start + dur))

    # ------------------------------------------------------------------ small overlays
    def o_chip(self, cid: str, o: dict) -> None:
        pos = {"tl": "left:96px;top:84px", "tr": "right:96px;top:84px", "bl": "left:96px;bottom:150px"}[o.get("pos", "tl")]
        body = f'        <div class="chip{" warn" if o.get("warn") else ""} c" style="{pos}"><b>{E(o["label"])}</b><span>{E(o["text"])}</span></div>'
        sc = ('          tl.fromTo(".c", {opacity:0, y:-20, scale:.92}, {opacity:1, y:0, scale:1, duration:.5, ease:"back.out(1.5)"}, 0);\n'
              '          tl.to(".c", {opacity:0, y:-10, duration:.3, ease:"power2.in"}, D-.3);')
        self.sub(cid, o["dur"], body, sc)
        self.mount(cid, o["start"], o["dur"], 14)
        self.sfx.append((o["start"], "pop"))

    def o_skip(self, cid: str, o: dict) -> None:
        start, dur, t = o["start"], o["dur"], self.t
        body = f"""        <div class="chip c" style="right:96px;top:84px">
          <svg width="44" height="44" viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" fill="none" stroke="{t['chip_label']}" stroke-width="4"/>
            <line class="hand" x1="22" y1="22" x2="22" y2="9" stroke="{t['paper']}" stroke-width="4" stroke-linecap="round" style="transform-origin:22px 22px"/></svg>
          <b>{E(o.get('label', 'Fast-forward'))}</b><span>{E(o['text'])}</span></div>"""
        sc = ('          tl.fromTo(".c", {opacity:0, y:-20}, {opacity:1, y:0, duration:.45, ease:"back.out(1.5)"}, 0);\n'
              '          tl.fromTo(".hand", {rotation:0}, {rotation:360*Math.max(1,Math.round(D/1.5)), duration:D, ease:"none"}, 0);\n'
              '          tl.to(".c", {opacity:0, y:-10, duration:.3}, D-.3);')
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 14)
        self.sfx.append((start, "pop"))
        self.lifts.append((start, start + dur))

    def o_note(self, cid: str, o: dict) -> None:
        body = f"""        <div class="nt" style="position:absolute;left:{o.get('x', 120)}px;top:{o.get('y', 790)}px;padding:10px 26px 14px;background:{self.t['paper']};border-radius:16px;
             box-shadow:0 14px 34px rgba(20,24,60,.25);transform:rotate({o.get('rot', -2)}deg)"><span class="note" style="font-size:{o.get('size', 58)}px">{E(o['text'])}</span></div>"""
        sc = ('          tl.fromTo(".nt", {opacity:0, y:14}, {opacity:1, y:0, duration:.45, ease:"power3.out"}, 0);\n'
              '          tl.to("#root", {opacity:0, duration:.3}, D-.3);')
        self.sub(cid, o["dur"], body, sc)
        self.mount(cid, o["start"], o["dur"], 15)
        self.sfx.append((o["start"], "pop"))

    # ------------------------------------------------------------------ sketch diagrams
    ICONS = {
        "stack": '<rect class="ink d" pathLength="1" x="-90" y="-60" width="180" height="120" rx="18"/><path class="ink d" pathLength="1" d="M-70 -80 H70 M-50 -98 H50"/><path class="ink d" pathLength="1" d="M-55 -20 H55 M-55 10 H30"/>',
        "lens": '<circle class="ink d" pathLength="1" cx="-15" cy="-15" r="62"/><path class="ink d" pathLength="1" d="M30 30 L90 90"/><path class="ink d" pathLength="1" d="M-40 -15 H10 M-15 -40 V10"/>',
        "doc": '<path class="ink d" pathLength="1" d="M-70 -95 H40 L80 -55 V95 H-70 Z M40 -95 V-55 H80"/><path class="ink d" pathLength="1" d="M-40 -20 H50 M-40 15 H50 M-40 50 H20"/>',
        "build": '<rect class="ink d" pathLength="1" x="-80" y="-70" width="160" height="140" rx="22"/><path class="ink d" pathLength="1" d="M-30 -20 L-60 0 L-30 20 M30 -20 L60 0 L30 20"/>',
        "check": '<circle class="ink d" pathLength="1" cx="0" cy="0" r="85"/><path class="ink d" pathLength="1" d="M-40 0 L-10 30 L45 -30"/>',
        "loop": '<path class="ink d" pathLength="1" d="M70 -20 A75 75 0 1 0 60 45"/><path class="ink d" pathLength="1" d="M78 -70 L72 -18 L22 -30"/>',
        "inbox": '<rect class="ink d" pathLength="1" x="-90" y="-80" width="180" height="160" rx="26"/><path class="ink d" pathLength="1" d="M-90 10 H-35 L-20 40 H20 L35 10 H90"/>',
        "clock": '<circle class="ink d" pathLength="1" cx="0" cy="0" r="85"/><path class="ink d" pathLength="1" d="M0 -50 V0 L35 25"/>',
        "bot": '<rect class="ink d" pathLength="1" x="-100" y="-70" width="200" height="150" rx="34"/><circle class="ink d" pathLength="1" cx="-40" cy="0" r="14"/><circle class="ink d" pathLength="1" cx="40" cy="0" r="14"/><path class="ink d" pathLength="1" d="M-30 45 Q0 65 30 45 M0 -70 V-105"/>',
    }

    def o_steps(self, cid: str, o: dict) -> None:
        start, dur, steps, beats = o["start"], o["dur"], o["steps"], o["beats"]
        xs = [360, 960, 1560] if len(steps) == 3 else [480, 1440]
        g, labs = "", ""
        for i, ((lab, icon), x) in enumerate(zip(steps, xs)):
            g += f'<g class="s{i}" transform="translate({x},520)">{self.ICONS[icon]}</g>'
            if i < len(steps) - 1:
                gap = xs[i + 1] - x
                g += (f'<path class="ink d ar{i}" pathLength="1" d="M{x + 150} 520 C {x + gap * .4} 490, {x + gap * .6} 550, '
                      f'{x + gap - 160} 520 M{x + gap - 182} 500 L{x + gap - 158} 520 L{x + gap - 182} 542"/>')
            labs += f'<div class="lb lb{i}" style="position:absolute;left:{x - 260}px;width:520px;top:660px;text-align:center;font:600 40px/1.2 {self.t["body_font"]}">{E(lab)}</div>'
        body = f"""        <div class="paper dots" style="position:absolute;inset:0"></div>
        <div class="hd head" style="position:absolute;left:120px;top:110px;font-weight:600;font-size:70px;letter-spacing:-.02em">{E(o['head'])}</div>
        <div class="hn note" style="position:absolute;left:126px;top:200px;font-size:58px;transform:rotate(-1.5deg)">{E(o.get('note', ''))}</div>
        <svg style="position:absolute;left:0;top:0" width="1920" height="1080">{g}</svg>
        {labs}"""
        sc = ('          tl.fromTo("#root", {opacity:0}, {opacity:1, duration:.35}, 0);\n'
              '          tl.fromTo(".hd", {opacity:0, y:24}, {opacity:1, y:0, duration:.5, ease:"power3.out"}, .1);\n'
              '          tl.fromTo(".hn", {opacity:0, y:12}, {opacity:1, y:0, duration:.45}, .5);\n')
        for i, at in enumerate(beats):
            sc += f'          tl.to(".s{i} .d", {{strokeDashoffset:0, duration:.7, ease:"power2.inOut", stagger:.1}}, {at});\n'
            sc += f'          tl.fromTo(".lb{i}", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.4}}, {at}+.35);\n'
            if i < len(beats) - 1:
                sc += f'          tl.to(".ar{i}", {{strokeDashoffset:0, duration:.5}}, {beats[i + 1]}-.45);\n'
            self.sfx.append((start + at, "tick"))
        sc += '          tl.to("#root", {opacity:0, duration:.35}, D-.35);'
        self.sub(cid, dur, body, sc)
        self.mount(cid, start, dur, 18)
        self.sfx.append((start, "whoosh"))

    def o_sort(self, cid: str, o: dict) -> None:
        """Source -> agent -> buckets, with an optional skipped bucket struck out."""
        start, dur, t = o["start"], o["dur"], self.t
        buckets = o["buckets"]  # [[local_t, label], ...]
        skip = o.get("skip")    # [local_t, label] or None
        n = len(buckets) + (1 if skip else 0)
        ys = [300 + i * (620 / max(1, n - 1)) for i in range(n)]
        paths, boxes = "", ""
        for i, y in enumerate(ys):
            cls = "ink2" if (skip and i == n - 1) else "ink"
            paths += f'<path class="{cls} d a{i}" pathLength="1" d="M1040 580 C1120 {580 + (y - 580) * .4},1160 {y},1240 {y}"/>'
        for i, (_, label) in enumerate(buckets):
            boxes += f'<div class="bk k{i}" style="top:{ys[i] - 36}px">{E(label)}</div>'
        if skip:
            boxes += (f'<div class="bk sp k{n - 1}" style="top:{ys[-1] - 36}px">{E(skip[1])}<svg width="100%" height="40" style="position:absolute;left:0;top:22px" '
                      f'viewBox="0 0 150 40" preserveAspectRatio="none"><path class="ink d st" pathLength="1" d="M10 22 Q75 6 140 18" style="stroke:{t["warn"]}"/></svg></div>')
        body = f"""        <div class="paper dots" style="position:absolute;inset:0"></div>
        <div class="hd head" style="position:absolute;left:120px;top:96px;font-weight:600;font-size:70px;letter-spacing:-.02em">{E(o['head'])}</div>
        <svg style="position:absolute;left:0;top:0" width="1920" height="1080">
          <g class="g-src" transform="translate(320,580)">{self.ICONS[o.get('source_icon', 'inbox')]}</g>
          <path class="ink d a-in" pathLength="1" d="M520 580 C 600 560, 640 600, 720 580 M700 560 L724 580 L700 602"/>
          <g class="g-agent" transform="translate(880,580)">{self.ICONS[o.get('agent_icon', 'bot')]}</g>
          {paths}
        </svg>
        <div class="lb l-src note" style="position:absolute;left:120px;width:400px;text-align:center;top:690px;font-size:54px">{E(o.get('source', ''))}</div>
        <div class="lb l-agent note" style="position:absolute;left:680px;width:400px;text-align:center;top:690px;font-size:54px">{E(o.get('agent', ''))}</div>
        {boxes}"""
        css = (f".bk{{position:absolute;left:1260px;padding:16px 34px;border-radius:18px;background:#fff;border:3px solid {t['ink']};"
               f"font:600 38px {t['body_font']};box-shadow:0 10px 26px rgba(0,0,0,.08)}}.bk.sp{{border-color:{t['line']};color:{t['soft']};box-shadow:none}}")
        b0 = o.get("beats", {"source": 0.6, "agent": 1.6})
        sc = f"""          tl.fromTo("#root", {{opacity:0}}, {{opacity:1, duration:.35}}, 0);
          tl.fromTo(".hd", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, .1);
          tl.to(".g-src .d", {{strokeDashoffset:0, duration:.7, ease:"power2.inOut", stagger:.1}}, {b0['source']});
          tl.fromTo(".l-src", {{opacity:0, y:10}}, {{opacity:1, y:0, duration:.4}}, {b0['source']}+.4);
          tl.to(".a-in", {{strokeDashoffset:0, duration:.5}}, {b0['agent']}-.3);
          tl.to(".g-agent .d", {{strokeDashoffset:0, duration:.7, ease:"power2.inOut", stagger:.08}}, {b0['agent']});
          tl.fromTo(".l-agent", {{opacity:0, y:10}}, {{opacity:1, y:0, duration:.4}}, {b0['agent']}+.4);
"""
        timed = [b[0] for b in buckets] + ([skip[0]] if skip else [])
        for i, at in enumerate(timed):
            sc += f'          tl.to(".a{i}", {{strokeDashoffset:0, duration:.45, ease:"power2.out"}}, {at});\n'
            sc += f'          tl.fromTo(".k{i}", {{opacity:0, x:-20}}, {{opacity:1, x:0, duration:.4, ease:"back.out(1.6)"}}, {at}+.3);\n'
            self.sfx.append((start + at + 0.3, "tick"))
        if skip:
            sc += f'          tl.to(".st", {{strokeDashoffset:0, duration:.4}}, {skip[0]}+.8);\n'
        sc += '          tl.to("#root", {opacity:0, duration:.35}, D-.35);'
        self.sub(cid, dur, body, sc, css)
        self.mount(cid, start, dur, 18)
        self.sfx.append((start, "whoosh"))

    # ------------------------------------------------------------------ captions
    def captions(self) -> int:
        cfg = self.plan.get("captions", {})
        if cfg.get("enabled", True) is False:
            return 0
        words = json.load(open(os.path.join(self.work, "spine_words.json")))
        proper = {k.lower(): v for k, v in cfg.get("proper", {}).items()}
        fixes = cfg.get("fixes", [])  # [from, to, heard, replacement]
        drop = {w.lower() for w in cfg.get("drop", ["um", "uh"])}
        clean = []
        for a, b, tok in words:
            if re.fullmatch(r"\d+\.\d+[.,]?", tok):
                w = tok.rstrip(".,")
            else:
                key = re.sub(r"[^\w'\-:]", "", tok.lower())
                w = next((rep for fa, fb, heard, rep in fixes if fa <= a <= fb and key == heard.lower()), None)
                if w is None:
                    if key in drop:
                        w = ""
                    else:
                        w = proper.get(key, key if cfg.get("lowercase", True) else tok.strip(".,!"))
                        w += "?" if tok.endswith("?") else ""
            if w:
                clean.append({"t": round(a, 2), "e": round(max(b, a + 0.12), 2), "w": w, "brk": tok.rstrip()[-1:] in ".?,!"})
        chunks, cur = [], []
        for w in clean:
            if cur and (w["t"] - cur[-1]["e"] > 0.32 or len(cur) >= cfg.get("max_words", 4)
                        or len(" ".join(x["w"] for x in cur + [w])) > cfg.get("max_chars", 26) or cur[-1]["brk"]):
                chunks.append(cur)
                cur = []
            cur.append(w)
        if cur:
            chunks.append(cur)
        keep = []
        for i, c in enumerate(chunks):
            nxt = chunks[i + 1][0]["t"] if i + 1 < len(chunks) else c[-1]["e"] + 0.6
            s, e = c[0]["t"], min(c[-1]["e"] + 0.5, nxt)
            if not any(a - 0.05 <= s < b for a, b in self.hide):
                keep.append((s, e, c))
        t = self.t
        divs, sc = [], []
        for i, (s, e, c) in enumerate(keep):
            ws = " ".join(f'<span class="w" id="w{i}_{j}">{E(w["w"])}</span>' for j, w in enumerate(c))
            divs.append(f'<div class="cap" id="c{i}">{ws}</div>')
            sc.append(f'tl.set("#c{i}",{{autoAlpha:1}},{s});tl.set("#c{i}",{{autoAlpha:0}},{e});')
            for j, w in enumerate(c):
                sc.append(f'tl.set("#w{i}_{j}",{{className:"w on"}},{w["t"]});tl.set("#w{i}_{j}",{{className:"w"}},{min(w["e"], e)});')
        css = f""".cap{{position:absolute;left:50%;bottom:58px;transform:translateX(-50%);visibility:hidden;opacity:0;white-space:nowrap;
  padding:14px 26px 16px;border-radius:20px;background:{t['dark']}e0;font:500 40px/1.2 {t['body_font']};color:{t['paper']}}}
.w{{display:inline-block;padding:2px 8px;margin:0 -4px;border-radius:10px}}.w.on{{background:{t['ink']};color:#fff}}"""
        # Plain id selectors here; the scoping regex only touches tl calls with quoted selectors, which these are.
        self.sub("captions", self.dur, "        " + "\n        ".join(divs), "          " + "\n          ".join(sc), css)
        self.mount("captions", 0, self.dur, 30, kind="captions")
        return len(keep)

    # ------------------------------------------------------------------ root
    def root_js(self) -> str:
        out = []
        for z in self.plan.get("zooms", []):
            a, b, cx, cy, s = z
            tx = max(min(960 - cx * s, 0), 1920 - 1920 * s)
            ty = max(min(540 - cy * s, 0), 1080 - 1080 * s)
            if a <= 0:
                out.append(f'tl.set("#inner", {{x:{tx:.1f}, y:{ty:.1f}, scale:{s}}}, 0);')
            else:
                out.append(f'tl.to("#inner", {{x:{tx:.1f}, y:{ty:.1f}, scale:{s}, duration:.8, ease:"expo.inOut"}}, {a});')
            out.append(f'tl.to("#inner", {{x:0, y:0, scale:1, duration:.8, ease:"expo.inOut"}}, {round(b - 0.8, 3)});')
        for a, b in self.push:
            out.append(f'tl.to("#screen", {{x:70, y:0, scale:.555, borderRadius:36, boxShadow:"0 40px 110px rgba(20,24,70,.35)", duration:.8, ease:"expo.inOut"}}, {a});')
            out.append(f'tl.to("#screen", {{x:0, y:0, scale:1, borderRadius:0, boxShadow:"0 40px 110px rgba(20,24,70,0)", duration:.7, ease:"expo.inOut"}}, {round(b - 0.7, 3)});')
        for i, (a, b, *_r) in enumerate(self.plan.get("highlights", [])):
            out.append(f'tl.fromTo("#hl{i}", {{scaleX:0, opacity:1}}, {{scaleX:1, duration:.5, ease:"power2.inOut"}}, {a});')
            out.append(f'tl.to("#hl{i}", {{opacity:0, duration:.3}}, {b});')
        return "\n      ".join(out)

    def bed_lane(self, low: float, high: float) -> dict:
        pts = [(0, 0.0), (0.6, low)]
        for a, b in self.lifts:
            pts += [(a - 0.25, low), (a + 0.15, high), (b - 0.1, high), (b + 0.35, low if b < self.dur - 1 else high)]
        pts.append((self.dur, 0.0))
        pts = sorted({round(t, 2): v for t, v in pts if 0 <= t <= self.dur}.items())
        return {"target": "volume", "points": [{"t": t, "v": v} for t, v in pts]}

    def audio_html(self) -> str:
        m = self.plan.get("music", {})
        out = []
        bed = m.get("bed", "assets/audio/music.m4a")
        if os.path.exists(os.path.join(self.edit, bed)):
            out.append(f'      <audio id="music" src="{bed}" data-start="0" data-duration="{self.dur}" data-track-index="40" '
                       f'data-audio-group="music" data-volume="1"></audio>')
            json.dump(self.bed_lane(m.get("low", 0.55), m.get("high", 0.8)), open(os.path.join(self.work, "bed_lane.json"), "w"))
        vol = {"whoosh": 0.32, "pop": 0.22, "tick": 0.18}
        length = {"whoosh": 0.7, "pop": 0.12, "tick": 0.05}
        if m.get("sfx", True):
            seen = set()
            for i, (t, k) in enumerate(sorted(self.sfx)):
                t = round(max(0, t - (0.25 if k == "whoosh" else 0)), 2)
                f = f"assets/audio/sfx-{k}.wav"
                if (t, k) in seen or not os.path.exists(os.path.join(self.edit, f)):
                    continue
                seen.add((t, k))
                out.append(f'      <audio id="sfx{i}" src="{f}" data-start="{t}" data-duration="{length[k]}" '
                           f'data-track-index="{50 + i % 8}" data-audio-group="sfx" data-volume="{vol[k]}"></audio>')
        return "\n".join(out)

    def run(self) -> None:
        for n, o in enumerate(self.plan.get("overlays", [])):
            fn = getattr(self, "o_" + o["type"], None)
            if fn is None:
                sys.exit(f"error: unknown overlay type {o['type']!r}")
            fn(o.get("id") or f"{o['type']}{n}", o)
        ncap = self.captions()
        covers = "\n".join(
            f'        <video id="cov{i}" class="clip" src="assets/spine.mp4" data-start="{a}" data-duration="{round(b - a, 3)}" '
            f'data-media-start="{m}" data-track-index="{1 + i}" muted playsinline style="position:absolute;left:0;top:0;width:1920px;height:1080px"></video>'
            for i, (a, b, m) in enumerate(self.plan.get("covers", [])))
        hls = "\n".join(f'        <div id="hl{i}" class="hlr" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
                        for i, (_a, _b, x, y, w, h) in enumerate(self.plan.get("highlights", [])))
        t = self.t
        index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1920px; height: 1080px; overflow: hidden; background: {t['bg']}; }}
      #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: radial-gradient(1200px 800px at 30% 20%, {t['paper']}, {t['bg']} 60%, {t['line']}); }}
      #screen {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 50%; overflow: hidden; }}
      #inner {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }}
      #spine {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: cover; }}
      .hlr {{ position: absolute; background: {t['ink']}4d; border-radius: 6px; transform-origin: 0 50%; transform: scaleX(0); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{self.dur}" data-width="1920" data-height="1080">
      <div id="screen"><div id="inner" data-layout-allow-overflow>
        <video id="spine" class="clip" src="assets/spine.mp4" data-start="0" data-duration="{self.dur}" data-media-start="0"
          data-track-index="0" playsinline data-has-audio="true" data-audio-group="voiceover"></video>
{covers}
{hls}
      </div></div>
{chr(10).join(self.hosts)}
{self.audio_html()}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {self.root_js()}
      tl.set({{}}, {{}}, {self.dur});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
        open(os.path.join(self.edit, "index.html"), "w").write(index)
        print(f"wrote index.html: {len(self.hosts)} overlays, {ncap} caption chunks, {len(self.sfx)} sound cues, {self.dur}s")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    Build(sys.argv[1]).run()
