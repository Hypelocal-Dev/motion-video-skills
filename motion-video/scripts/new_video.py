#!/usr/bin/env python3
"""Start a new video project from a template.

Copies the template into a new folder, sets the project id and leaves a NOTES.md
handoff to fill in as you go.

Examples:
  new_video.py --list
  new_video.py square-loop ~/videos/spring-launch
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("template", nargs="?")
    p.add_argument("dest", nargs="?")
    p.add_argument("--list", action="store_true", help="list templates")
    args = p.parse_args()

    names = sorted(d.name for d in TEMPLATES.iterdir() if (d / "index.html").exists())
    if args.list or not args.template:
        for n in names:
            about = (TEMPLATES / n / "TEMPLATE.md").read_text().splitlines()[0].lstrip("# ")
            print(f"{n:16} {about}")
        return
    if args.template not in names:
        sys.exit(f"unknown template '{args.template}'. Choose from: {', '.join(names)}")
    if not args.dest:
        sys.exit("give a destination folder")

    dest = Path(args.dest).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} already exists and is not empty")
    shutil.copytree(TEMPLATES / args.template, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("renders", "review", ".hyperframes", "*.mp4"))
    slug = re.sub(r"[^a-z0-9]+", "-", dest.name.lower()).strip("-") or "video"
    (dest / "meta.json").write_text(json.dumps(
        {"id": slug, "name": slug, "createdAt": f"{date.today()}T00:00:00.000Z"}, indent=2) + "\n")
    print(f"created {dest} from '{args.template}'")
    print("next: read TEMPLATE.md in that folder, then replace the demo copy, voiceover and assets")


if __name__ == "__main__":
    main()
