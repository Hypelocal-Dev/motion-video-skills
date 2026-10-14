#!/usr/bin/env python3
"""Validate the plugin structure. Runs in CI and before every pull request.

Checks:
  - marketplace.json and every plugin.json parse and have the required fields
  - each marketplace entry points at a folder with a matching plugin.json
  - plugin.json version is semver and matches version.txt
  - every skill has front matter whose name matches its folder and a description
  - every command has front matter with a description
  - every template has index.html, TEMPLATE.md and meta.json
  - no absolute home-directory paths leak into shipped files
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def front_matter(path: Path) -> dict[str, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        err(f"{path.relative_to(ROOT)}: missing front matter")
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        err(f"{path.relative_to(ROOT)}: front matter is not closed")
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
    return fields


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        err(f"{path.relative_to(ROOT)}: {e}")
        return {}


def check_plugin(folder: Path, name: str) -> None:
    manifest = folder / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        err(f"{folder.relative_to(ROOT)}: no .claude-plugin/plugin.json")
        return
    plugin = load_json(manifest)
    for key in ("name", "version", "description"):
        if not plugin.get(key):
            err(f"{manifest.relative_to(ROOT)}: missing '{key}'")
    if plugin.get("name") != name:
        err(f"{manifest.relative_to(ROOT)}: name '{plugin.get('name')}' does not match marketplace entry '{name}'")
    version = plugin.get("version", "")
    if not SEMVER.match(version):
        err(f"{manifest.relative_to(ROOT)}: version '{version}' is not semver")
    expected = (ROOT / "version.txt").read_text().strip()
    if version != expected:
        err(f"{manifest.relative_to(ROOT)}: version {version} does not match version.txt ({expected})")

    for skill in sorted((folder / "skills").glob("*/SKILL.md")):
        fm = front_matter(skill)
        if fm.get("name") != skill.parent.name:
            err(f"{skill.relative_to(ROOT)}: name '{fm.get('name')}' should be '{skill.parent.name}'")
        desc = fm.get("description", "")
        if not desc:
            err(f"{skill.relative_to(ROOT)}: missing description")
        elif len(desc) > 1024:
            err(f"{skill.relative_to(ROOT)}: description is {len(desc)} chars (max 1024)")

    for cmd in sorted((folder / "commands").glob("*.md")):
        if not front_matter(cmd).get("description"):
            err(f"{cmd.relative_to(ROOT)}: missing description")

    for tpl in sorted(p for p in (folder / "templates").iterdir() if p.is_dir()):
        for required in ("index.html", "TEMPLATE.md", "meta.json"):
            if not (tpl / required).exists():
                err(f"{tpl.relative_to(ROOT)}: missing {required}")


def check_no_home_paths() -> None:
    pattern = re.compile(r"/(Users|home)/[A-Za-z0-9_.-]+/")
    # Only files git would ship: tracked plus untracked-but-not-ignored.
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    for rel in listed:
        path = ROOT / rel
        if path.suffix not in {".md", ".py", ".sh", ".json", ".html", ".yml"} or not path.exists():
            continue
        for n, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if pattern.search(line) and "validate.py" not in path.name:
                err(f"{path.relative_to(ROOT)}:{n}: absolute home path")


def main() -> int:
    market = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    for key in ("name", "owner", "plugins"):
        if not market.get(key):
            err(f".claude-plugin/marketplace.json: missing '{key}'")
    for entry in market.get("plugins", []):
        source = entry.get("source", "")
        folder = (ROOT / source).resolve()
        if not folder.is_dir():
            err(f"marketplace entry '{entry.get('name')}': source {source} is not a folder")
            continue
        check_plugin(folder, entry.get("name", ""))
    check_no_home_paths()

    if errors:
        print("validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
