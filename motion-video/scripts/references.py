#!/usr/bin/env python3
"""Keep a folder of reference videos and pull frames from them on request.

Drop any video into the library folder (default ~/Documents/motion-references, or set
MV_REFERENCES). Subfolders are fine. To add your own notes on a video, put a text or
Markdown file with the same name next to it (`spinny-logo.mov` + `spinny-logo.md`).

`index` makes a contact sheet of each new video and a notes file for Claude's
breakdown, both under the library's `.index/` folder. `look` makes a denser sheet of
one stretch of a video, for studying a single move.

Examples:
  references.py init
  references.py index                       # sheet + notes stub for every new video
  references.py list
  references.py find "kinetic type"         # match names and notes
  references.py show spinny-logo            # paths, length, notes
  references.py look spinny-logo --start 3 --end 5 --count 16
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from _audio import duration, require

SCRIPTS = Path(__file__).resolve().parent
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".gif"}
NOTE_EXTS = (".md", ".txt")
README = """# Motion references

Drop videos here that have something worth borrowing: a transition, a type treatment, a
color grade, pacing, a camera move. Subfolders are fine.

Then tell Claude something like "use spinny-logo for the logo reveal" and it will find
the video, study the frames and build that element.

Optional: put your own notes next to a video in a file with the same name
(`spinny-logo.md`), e.g. "the text wipe at 0:04". Claude reads them first.

Claude keeps its contact sheets and breakdowns in `.index/`. Leave that folder alone.
"""
NOTES_STUB = """# {name}

Source: `{rel}`. Length: {length}.
`sheet.png` frames, left to right, top to bottom: {times}.

<!-- Claude fills this in after reading sheet.png. Keep entries short. -->

## Elements

- (time range): what happens, and how it's built (easing, timing, layering)

## Style

- Palette:
- Type:
- Pacing:

## Tags

"""


def library() -> Path:
    return Path(os.environ.get("MV_REFERENCES", "~/Documents/motion-references")).expanduser()


def videos(lib: Path) -> list[Path]:
    found = []
    for root, dirs, files in os.walk(lib):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [Path(root) / f for f in sorted(files)
                  if Path(f).suffix.lower() in VIDEO_EXTS and not f.startswith(".")]
    return found


def key(lib: Path, video: Path) -> str:
    """Unique name for a video: its path in the library without the extension."""
    return str(video.relative_to(lib).with_suffix("")).replace(os.sep, "__")


def index_dir(lib: Path, video: Path) -> Path:
    return lib / ".index" / key(lib, video)


def user_notes(video: Path) -> Path | None:
    for ext in NOTE_EXTS:
        p = video.with_suffix(ext)
        if p.exists():
            return p
    return None


def fmt_len(s: float) -> str:
    return f"{int(s // 60)}:{s % 60:04.1f}"


def resolve(lib: Path, name: str) -> Path:
    """Find one video by exact name, then by a match on any part of its path."""
    vids = videos(lib)
    q = name.lower()
    for test in (lambda v: key(lib, v).lower() == q or v.stem.lower() == q,
                 lambda v: q in str(v.relative_to(lib)).lower()):
        hits = [v for v in vids if test(v)]
        if len(hits) == 1:
            return hits[0]
        if hits:
            names = "\n  ".join(str(v.relative_to(lib)) for v in hits)
            raise SystemExit(f"'{name}' matches more than one video:\n  {names}")
    raise SystemExit(f"no video matching '{name}' in {lib}. Run `references.py list`.")


def seekable(lib: Path, video: Path) -> Path:
    """ffmpeg can't seek reliably in a GIF, so sheets come from a cached MP4 copy."""
    if video.suffix.lower() != ".gif":
        return video
    mp4 = index_dir(lib, video) / "gif.mp4"
    if not mp4.exists() or mp4.stat().st_mtime < video.stat().st_mtime:
        mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-movflags", "faststart",
                        "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(mp4)], check=True)
    return mp4


def sheet(video: Path, out: Path, *, count: int, cols: int, start: float = 0, end: float | None = None) -> str:
    """Write a contact sheet and return its frame times."""
    d = duration(str(video)) - 0.1  # the container often runs past the last frame
    end = d if end is None else min(end, d)
    if end <= start:
        raise SystemExit(f"nothing between {start}s and {end}s; the video is {d:.1f}s long")
    span = end - start
    times = [start + (i + 0.5) * span / count for i in range(count)]
    subprocess.run([sys.executable, str(SCRIPTS / "contact_sheet.py"), str(video),
                    "--times", ",".join(f"{t:.2f}" for t in times), "--cols", str(cols), "-o", str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    return ", ".join(f"{t:.2f}s" for t in times)


def cmd_init(lib: Path, _args) -> None:
    lib.mkdir(parents=True, exist_ok=True)
    readme = lib / "README.md"
    if not readme.exists():
        readme.write_text(README)
    print(f"library: {lib}")


def cmd_index(lib: Path, args) -> None:
    require("ffmpeg")
    cmd_init(lib, args)
    new = 0
    for v in videos(lib):
        idx = index_dir(lib, v)
        if (idx / "sheet.png").exists() and not args.force:
            continue
        idx.mkdir(parents=True, exist_ok=True)
        try:
            times = sheet(seekable(lib, v), idx / "sheet.png", count=args.count, cols=args.cols)
        except (subprocess.CalledProcessError, SystemExit):
            print(f"skipped {v.relative_to(lib)}: ffmpeg couldn't read it", file=sys.stderr)
            continue
        notes = idx / "notes.md"
        if not notes.exists():
            notes.write_text(NOTES_STUB.format(name=key(lib, v), rel=v.relative_to(lib),
                                               length=fmt_len(duration(str(v))), times=times))
        new += 1
        print(f"indexed {v.relative_to(lib)} -> {idx.relative_to(lib)}/sheet.png")
    print(f"{new} new" if new else "nothing new to index")


def cmd_list(lib: Path, _args) -> None:
    vids = videos(lib)
    if not vids:
        print(f"no videos in {lib}")
        return
    for v in vids:
        idx = index_dir(lib, v)
        state = "new" if not (idx / "sheet.png").exists() else (
            "described" if "(time range)" not in _read(idx / "notes.md") else "indexed")
        mine = " +your notes" if user_notes(v) else ""
        print(f"{key(lib, v):40} {fmt_len(duration(str(v))):>8}  {state}{mine}")


def cmd_find(lib: Path, args) -> None:
    words = args.query.lower().split()
    hits = 0
    for v in videos(lib):
        mine = user_notes(v)
        text = " ".join([str(v.relative_to(lib)), _read(index_dir(lib, v) / "notes.md"),
                         _read(mine) if mine else ""]).lower()
        if all(w in text for w in words):
            hits += 1
            print(key(lib, v))
    if not hits:
        print("no matches. Try fewer words, or `references.py list`.")


def cmd_show(lib: Path, args) -> None:
    v = resolve(lib, args.name)
    idx = index_dir(lib, v)
    mine = user_notes(v)
    print(f"video:  {v}")
    print(f"length: {fmt_len(duration(str(v)))}")
    print(f"sheet:  {idx / 'sheet.png' if (idx / 'sheet.png').exists() else '(not indexed; run index)'}")
    print(f"notes:  {idx / 'notes.md'}")
    if mine:
        print(f"\n--- your notes ({mine.name}) ---\n{_read(mine).strip()}")
    if (idx / "notes.md").exists():
        print(f"\n--- breakdown ---\n{_read(idx / 'notes.md').strip()}")


def cmd_look(lib: Path, args) -> None:
    require("ffmpeg")
    v = resolve(lib, args.name)
    idx = index_dir(lib, v)
    idx.mkdir(parents=True, exist_ok=True)
    end = f"{args.end:g}" if args.end is not None else "end"
    out = idx / f"look-{args.start:g}-{end}.png"
    try:
        times = sheet(seekable(lib, v), out, count=args.count, cols=args.cols, start=args.start, end=args.end)
    except subprocess.CalledProcessError:
        raise SystemExit(f"ffmpeg couldn't read {v}") from None
    print(f"wrote {out}")
    print(f"frames at: {times}")


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create the library folder")
    s = sub.add_parser("index", help="contact sheet and notes stub for each new video")
    s.add_argument("--count", type=int, default=24)
    s.add_argument("--cols", type=int, default=6)
    s.add_argument("--force", action="store_true", help="rebuild sheets that already exist")
    sub.add_parser("list", help="every video, its length and whether it's been described")
    s = sub.add_parser("find", help="videos whose name or notes contain every word")
    s.add_argument("query")
    s = sub.add_parser("show", help="paths and notes for one video")
    s.add_argument("name")
    s = sub.add_parser("look", help="dense contact sheet of one stretch of a video")
    s.add_argument("name")
    s.add_argument("--start", type=float, default=0)
    s.add_argument("--end", type=float)
    s.add_argument("--count", type=int, default=16)
    s.add_argument("--cols", type=int, default=4)
    args = p.parse_args()
    lib = library()
    if args.cmd != "init" and args.cmd != "index" and not lib.exists():
        raise SystemExit(f"{lib} doesn't exist yet. Run `references.py init`.")
    {"init": cmd_init, "index": cmd_index, "list": cmd_list, "find": cmd_find,
     "show": cmd_show, "look": cmd_look}[args.cmd](lib, args)


if __name__ == "__main__":
    main()
