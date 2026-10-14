---
description: Start a new motion video project from a template and walk through the brief
argument-hint: "[template] [folder]"
---

Start a new motion video.

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.sh"`. If anything fails, offer to run
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh"` and stop until it passes.
2. If no template was given in "$ARGUMENTS", run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_video.py" --list`
   and ask which one fits, recommending one from the brief.
3. Create the project with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_video.py" <template> <folder>`.
4. Follow the motion-video skill from step 1 (read the brief). Read the new project's
   TEMPLATE.md before editing anything.
