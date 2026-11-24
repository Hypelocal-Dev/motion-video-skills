#!/usr/bin/env python3
"""Set up a tutorial-edit project, and save or reuse brand kits.

  tutorial_new.py new FOLDER [--brand NAME] [--footage FILE]
      Make the folder layout, scaffold the HyperFrames project in edit/, copy a saved
      brand kit in when --brand names one, move or copy the recording into footage/,
      and print what the person still needs to drop in.

  tutorial_new.py status FOLDER
      Say what's in footage/, inspo/ and brand/ and what's missing.

  tutorial_new.py brand-save NAME FOLDER
      Save FOLDER/brand/ (theme.json, logo files, fonts, the guidelines PDF) as a kit
      in $MOTION_VIDEO_HOME/brands/NAME so the next project for that brand starts on-brand.

  tutorial_new.py brand-list
      List saved kits.

Kits live on this machine only, never in the plugin repo, so client brands stay private.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

HOME = os.environ.get("MOTION_VIDEO_HOME", os.path.expanduser("~/.motion-video"))
BRANDS = os.path.join(HOME, "brands")
CAVEAT = "https://fonts.gstatic.com/s/caveat/v23/Wnz6HAc5bAfYB2Q7ZjYYiAzcPA.woff2"
VIDEO = (".mp4", ".mov", ".m4v", ".mkv", ".webm")

README = """# {name}

Tutorial edit. Drop your files in the folders below, then tell Claude "let's edit this".

| Folder     | What goes in it |
| ---------- | --------------- |
| `footage/` | The raw screen recording (and any camera footage). Never edited in place. |
| `inspo/`   | 2-3 videos whose look you like: captions, motion, pacing. Add `name.md` next to one \
to say what to borrow ("the text pop at 0:04"). Links work too: paste them in chat. |
| `brand/`   | The brand guidelines PDF, logo files (SVG or PNG) and brand fonts. Claude turns them into `theme.json`. |
| `work/`    | Claude's working files: cut list, plan, transcripts. |
| `edit/`    | The HyperFrames project. Open it in the preview to scrub and tweak. |
| `renders/` | Finished drafts and finals. |

Status and decisions live in `NOTES.md`.
"""

NOTES = """# Notes

## Status
- {date}: project set up.

## Brief
- Audience:
- Where it will be posted:
- Target length:

## Decisions

## Privacy
- Anything that must never show (other clients, chats, passwords, personal tabs):
"""


def checklist(folder: str) -> list[str]:
    def has(sub: str, exts: tuple[str, ...] | None = None) -> list[str]:
        d = os.path.join(folder, sub)
        if not os.path.isdir(d):
            return []
        return [f for f in os.listdir(d) if not f.startswith(".") and (exts is None or f.lower().endswith(exts))]

    lines = []
    footage = has("footage", VIDEO)
    found = ", ".join(footage) or "drop the raw recording here (required)"
    lines.append(("ok  " if footage else "TODO") + f" footage/: {found}")
    inspo = has("inspo")
    lines.append(("ok  " if inspo else "ask ") + f" inspo/: {len(inspo)} file(s)" + ("" if inspo else
                 " - ask for 2-3 videos whose style they like. Without them the edit uses the plugin's default look."))
    brand = has("brand")
    theme = os.path.exists(os.path.join(folder, "brand", "theme.json"))
    if theme:
        lines.append(f"ok   brand/: theme.json ready ({len(brand)} file(s))")
    elif brand:
        lines.append(f"todo brand/: {len(brand)} file(s), no theme.json yet - extract colors, fonts and logo from them")
    else:
        lines.append("ask  brand/: empty - ask for the brand guidelines PDF, logo and fonts. "
                     "Without them the edit uses neutral colors.")
    return lines


def cmd_new(a: argparse.Namespace) -> None:
    folder = os.path.abspath(a.folder)
    if os.path.exists(os.path.join(folder, "work", "cut.json")):
        sys.exit(f"error: {folder} already has a tutorial project. Use `status`.")
    for sub in ("footage", "inspo", "brand", "work", "renders"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    name = os.path.basename(folder)
    if not os.path.exists(os.path.join(folder, "README.md")):
        open(os.path.join(folder, "README.md"), "w").write(README.format(name=name))
    if not os.path.exists(os.path.join(folder, "NOTES.md")):
        import datetime
        open(os.path.join(folder, "NOTES.md"), "w").write(NOTES.format(date=datetime.date.today().isoformat()))
    if a.brand:
        kit = os.path.join(BRANDS, a.brand)
        if not os.path.isdir(kit):
            saved = ", ".join(sorted(os.listdir(BRANDS))) if os.path.isdir(BRANDS) else "none"
            sys.exit(f"error: no saved brand kit {a.brand!r}. Saved kits: {saved}")
        shutil.copytree(kit, os.path.join(folder, "brand"), dirs_exist_ok=True)
        print(f"copied brand kit {a.brand!r} into brand/")
    if a.footage:
        dest = os.path.join(folder, "footage", os.path.basename(a.footage))
        (shutil.move if a.move else shutil.copy2)(a.footage, dest)
        print(f"{'moved' if a.move else 'copied'} {a.footage} -> footage/")
    edit = os.path.join(folder, "edit")
    if not os.path.exists(os.path.join(edit, "hyperframes.json")):
        version = os.environ.get("MV_HYPERFRAMES_VERSION", "latest")
        subprocess.run(["npx", "--yes", f"hyperframes@{version}", "init", edit, "--non-interactive", "--example=blank"],
                       check=True, stdout=subprocess.DEVNULL)
        os.makedirs(os.path.join(edit, "assets", "fonts"), exist_ok=True)
    font = os.path.join(edit, "assets", "fonts", "caveat-latin.woff2")
    if not os.path.exists(font):  # handwriting font for notes (SIL Open Font License)
        try:
            urllib.request.urlretrieve(CAVEAT, font)
        except OSError as e:
            print(f"warning: couldn't download the note font ({e}); notes fall back to a system script font")
    print(f"\nProject ready: {folder}\n")
    print("\n".join(checklist(folder)))


def cmd_status(a: argparse.Namespace) -> None:
    print("\n".join(checklist(os.path.abspath(a.folder))))


def cmd_brand_save(a: argparse.Namespace) -> None:
    src = os.path.join(os.path.abspath(a.folder), "brand")
    if not os.path.exists(os.path.join(src, "theme.json")):
        sys.exit(f"error: {src}/theme.json is missing. Extract the brand first (see the tutorial-edit skill).")
    json.load(open(os.path.join(src, "theme.json")))  # fail early on bad JSON
    dest = os.path.join(BRANDS, a.name)
    os.makedirs(BRANDS, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    print(f"saved brand kit {a.name!r} -> {dest}. Next time: tutorial_new.py new <folder> --brand {a.name}")


def cmd_brand_list(_a: argparse.Namespace) -> None:
    kits = sorted(os.listdir(BRANDS)) if os.path.isdir(BRANDS) else []
    print("\n".join(kits) if kits else "no saved brand kits yet")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new")
    s.add_argument("folder")
    s.add_argument("--brand")
    s.add_argument("--footage", help="recording to put in footage/")
    s.add_argument("--move", action="store_true", help="move --footage instead of copying it")
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("status")
    s.add_argument("folder")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("brand-save")
    s.add_argument("name")
    s.add_argument("folder")
    s.set_defaults(fn=cmd_brand_save)
    s = sub.add_parser("brand-list")
    s.set_defaults(fn=cmd_brand_list)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
