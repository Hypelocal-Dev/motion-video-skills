#!/usr/bin/env python3
"""Find and fetch archival b-roll and period music from the Internet Archive.

Two collections: Prelinger (ephemeral films: ads, educational and industrial films,
home movies) and the 78rpm collection (shellac records digitized by the Great 78
Project). `get` saves the file, or a trimmed clip of it, into the project's
assets/archive/ and adds a credit line to NOTES.md.

78s: a US recording enters the public domain 100 years after the end of its publication
year, so `search 78` only returns records from that cutoff or earlier, and `get` refuses
later ones unless you pass --allow-later.

Examples:
  archive_media.py search prelinger "traffic safety" --years 1940-1960
  archive_media.py search 78 charleston
  archive_media.py files WeDriver1936
  archive_media.py get WeDriver1936 ~/videos/spring-launch --start 42 --end 48
  archive_media.py get 78_charleston-cabin_..._gbia3004806b ~/videos/spring-launch
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlencode

API = "https://archive.org"
UA = {"User-Agent": "motion-video-skills (archive_media.py)"}
COLLECTIONS = {"prelinger": "prelinger", "78": "georgeblood"}
FIELDS = ["identifier", "title", "date", "year", "creator", "runtime", "licenseurl", "mediatype"]
# Best file format first. Original FLAC beats the MP3 derivative; h.264 MP4 plays everywhere.
VIDEO_FORMATS = ["h.264", "h.264 IA", "MPEG4", "512Kb MPEG4", "Ogg Video", "MPEG2"]
AUDIO_FORMATS = ["24bit Flac", "Flac", "VBR MP3", "128Kbps MP3", "Ogg Vorbis"]


def last_public_year() -> int:
    return date.today().year - 101


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def first(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:3])
    return "" if value is None else str(value)


def year_of(meta: dict) -> int | None:
    m = re.match(r"\d{4}", first(meta.get("date")) or first(meta.get("year")))
    return int(m.group()) if m else None


def seconds(length) -> float | None:
    if length in (None, ""):
        return None
    try:
        parts = [float(p) for p in str(length).split(":")]
    except ValueError:
        return None
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def fmt_len(s: float | None) -> str:
    return "" if s is None else f"{int(s // 60)}:{int(s % 60):02d}"


def is_78(meta: dict) -> bool:
    cols = meta.get("collection") or []
    cols = [cols] if isinstance(cols, str) else cols
    return "78rpm" in cols or "georgeblood" in cols


def rights(meta: dict) -> str:
    if is_78(meta):
        y = year_of(meta)
        if y is None:
            return "date unknown, check before use"
        return "public domain (US)" if y <= last_public_year() else f"not public domain until {y + 101}"
    lic = meta.get("licenseurl")
    if not lic:
        return "no license listed, check before use"
    if "publicdomain" in lic:
        return "public domain"
    return lic


# ---------------------------------------------------------------- commands

def cmd_search(args) -> None:
    q = f"collection:{COLLECTIONS[args.collection]} AND ({args.query})"
    lo, hi = None, None
    if args.years:
        lo, _, hi = args.years.partition("-")
        hi = hi or lo
    if args.collection == "78" and not args.allow_later:
        hi = str(min(int(hi), last_public_year())) if hi else str(last_public_year())
    if lo or hi:
        q += f" AND date:[{lo or '1800'}-01-01 TO {hi or '2100'}-12-31]"
    params = [("q", q), ("rows", args.rows), ("output", "json"), ("sort[]", args.sort)]
    params += [("fl[]", f) for f in FIELDS]
    docs = fetch_json(f"{API}/advancedsearch.php?{urlencode(params)}")["response"]["docs"]
    if not docs:
        print("Nothing found. Try broader words or a wider --years range.")
        return
    if args.collection == "78" and not args.allow_later:
        print(f"Records from {last_public_year()} or earlier (US public domain).\n")
    for d in docs:
        if args.collection == "78":
            d["collection"] = ["georgeblood"]
        line = f"{first(d.get('date'))[:10] or first(d.get('year')) or '????'}  {first(d.get('title'))}"
        if d.get("creator"):
            line += f"  ({first(d['creator'])})"
        if d.get("runtime"):
            line += f"  {d['runtime']}"
        print(line)
        print(f"    {d['identifier']}  [{rights(d)}]")
        print(f"    {API}/details/{d['identifier']}")


def item(identifier: str) -> dict:
    data = fetch_json(f"{API}/metadata/{quote(identifier)}")
    if not data.get("metadata"):
        sys.exit(f"No item called {identifier} on archive.org")
    return data


def media_files(data: dict) -> list[dict]:
    order = VIDEO_FORMATS + AUDIO_FORMATS
    files = [f for f in data["files"] if f.get("format") in order]
    return sorted(files, key=lambda f: order.index(f["format"]))


def cmd_files(args) -> None:
    data = item(args.identifier)
    meta = data["metadata"]
    print(f"{first(meta.get('title'))}  ({first(meta.get('date')) or first(meta.get('year'))})")
    print(f"Rights: {rights(meta)}\n")
    for f in media_files(data):
        size = int(f.get("size") or 0) / 1e6
        print(f"  {f['format']:<12} {fmt_len(seconds(f.get('length'))):>6}  {size:7.1f} MB  {f['name']}")
    thumbs = [f["name"] for f in data["files"] if f.get("format") == "Thumbnail"]
    if thumbs:
        print(f"\n{len(thumbs)} thumbnails, e.g. {API}/download/{quote(args.identifier)}/{quote(thumbs[0])}")


def download(url: str, dest: Path, tries: int = 3) -> None:
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as fh:
                shutil.copyfileobj(r, fh)
            return
        except (urllib.error.URLError, TimeoutError) as e:
            # archive.org's file servers return the odd 5xx; a retry usually lands.
            if attempt == tries:
                sys.exit(f"Download failed after {tries} tries: {e}")
            time.sleep(2 * attempt)


def convert(src: str, out: Path, is_video: bool, start: float | None, end: float | None) -> bool:
    cmd = ["ffmpeg", "-v", "error", "-y", "-user_agent", UA["User-Agent"]] if src.startswith("http") \
        else ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    if is_video:
        # Re-encode so the cut lands on the exact frame. Archival sound is usually noise, so drop it.
        cmd += ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)]
    else:
        cmd += ["-ar", "48000", "-ac", "2", str(out)]
    return subprocess.run(cmd).returncode == 0 and out.exists() and out.stat().st_size > 0


def cmd_get(args) -> None:
    root = Path(args.project).expanduser().resolve()
    if not (root / "index.html").exists():
        sys.exit(f"{root} is not a video project (no index.html)")
    data = item(args.identifier)
    meta = data["metadata"]
    status = rights(meta)
    if is_78(meta) and not status.startswith("public domain") and not args.allow_later:
        sys.exit(f"{args.identifier}: {status}. Pick an earlier record, or pass --allow-later if you have a license.")

    files = media_files(data)
    if args.file:
        files = [f for f in data["files"] if f["name"] == args.file]
    if not files:
        sys.exit(f"No playable file in {args.identifier}. Run `files` to see what's there.")
    src = files[0]

    out_dir = root / "assets" / "archive"
    out_dir.mkdir(parents=True, exist_ok=True)
    is_video = src["format"] in VIDEO_FORMATS
    ext = ".mp4" if is_video else ".wav"
    name = args.name or re.sub(r"[^a-z0-9]+", "-", args.identifier.lower()).strip("-")[:60]
    out = out_dir / f"{name}{ext}"

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Run the video-doctor command.")
    url = f"{API}/download/{quote(args.identifier)}/{quote(src['name'])}"
    trimmed = args.start is not None or args.end is not None
    # A clip is cut straight from the URL, which reads only the part it needs. If the
    # server won't seek, or for whole files, download first.
    if not (trimmed and convert(url, out, is_video, args.start, args.end)):
        raw = out_dir / f".{name}.download{Path(src['name']).suffix}"
        print(f"Downloading {src['name']} ({int(src.get('size') or 0) / 1e6:.0f} MB)...", file=sys.stderr)
        try:
            download(url, raw)
            if not convert(str(raw), out, is_video, args.start, args.end):
                sys.exit(f"ffmpeg couldn't read {src['name']}. Try another file with --file.")
        finally:
            raw.unlink(missing_ok=True)

    span = ""
    if args.start is not None or args.end is not None:
        span = f", {args.start or 0}s to {args.end if args.end is not None else 'end'}s of the source"
    credit = (f"- `assets/archive/{out.name}`: {first(meta.get('title'))}"
              f" ({first(meta.get('date')) or first(meta.get('year')) or 'undated'})"
              f"{', ' + first(meta.get('creator')) if meta.get('creator') else ''}{span}."
              f" {API}/details/{args.identifier}. Rights: {status}.\n")
    notes = root / "NOTES.md"
    text = notes.read_text() if notes.exists() else ""
    if "## Archival sources" not in text:
        text += ("\n" if text and not text.endswith("\n\n") else "") + "## Archival sources\n\n"
    notes.write_text(text + credit)
    print(f"Saved {out.relative_to(root)}  [{status}]")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="search Prelinger films or 78rpm records")
    s.add_argument("collection", choices=COLLECTIONS)
    s.add_argument("query", help="words to search for, or an archive.org query like 'subject:automobiles'")
    s.add_argument("--years", help="a year or range, e.g. 1950 or 1940-1960")
    s.add_argument("--rows", type=int, default=10)
    s.add_argument("--sort", default="downloads desc", help="e.g. 'downloads desc' or 'date asc'")
    s.add_argument("--allow-later", action="store_true", help="78s: include records still under copyright")
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("files", help="list an item's video and audio files and its rights")
    f.add_argument("identifier")
    f.set_defaults(func=cmd_files)

    g = sub.add_parser("get", help="download an item, or a clip of it, into the project's assets/archive/")
    g.add_argument("identifier")
    g.add_argument("project")
    g.add_argument("--start", type=float, help="clip start in source seconds")
    g.add_argument("--end", type=float, help="clip end in source seconds")
    g.add_argument("--file", help="a specific file name from `files` (default: the best one)")
    g.add_argument("--name", help="output name without extension")
    g.add_argument("--allow-later", action="store_true", help="78s: fetch a record still under copyright")
    g.set_defaults(func=cmd_get)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
