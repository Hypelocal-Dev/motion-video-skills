---
description: Index new videos in your reference folder and list what's there, or study one
argument-hint: "[video name or what to look for]"
---

Follow the reference-library skill. Run the tool as
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/references.py"`.

Run `index`, then:

- With no arguments, run `list` and say where the folder is, how many videos it holds,
  and which ones have no breakdown yet.
- If "$ARGUMENTS" names a video, run `show` on it and give its breakdown, writing one
  first if it has none.
- Otherwise treat "$ARGUMENTS" as a search: run `find` and summarize the matches from
  their notes.
