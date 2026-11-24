---
description: Set up a tutorial-edit project for a long screen recording and ask for the footage, inspo and brand files
argument-hint: "[folder] [recording] [--brand kit]"
---

Start a tutorial edit.

1. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.sh"`. If anything fails, offer to run
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh"` and stop until it passes.
2. Work out the folder and recording from "$ARGUMENTS" or the conversation. If the
   person named a brand, check `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tutorial_new.py" brand-list`.
   Ask before moving a recording; copy by default.
3. Create the project with
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tutorial_new.py" new <folder> [--footage <file>] [--brand <kit>]`.
4. Tell the person, in one short message, where the folder is and what to drop in:
   footage (required), 2-3 inspo videos or links, and the brand guidelines, logo and
   fonts. Say why inspo and brand matter: they set the style and keep it on brand.
5. Follow the tutorial-edit skill from step 1.
