---
name: reference-library
description: Use the person's folder of saved reference videos to match a style or rebuild a specific element (a transition, type treatment, logo reveal, color grade, pacing, camera move). Use whenever someone says "use <video> for reference", "make it like <video>", "steal the <element> from <video>", "what references do I have for <thing>", or mentions their reference folder, mood board or swipe file of videos. Also use when a brief or editor note names a reference by file name.
---

# Reference library

Scripts are in `<base dir>/../../scripts` (call it `$MV`). The tool is
`$MV/references.py`. It needs Python and ffmpeg.

The library is a plain folder the person drops videos into whenever they see something
they like: `~/Documents/motion-references`, or wherever `MV_REFERENCES` points.
Subfolders are fine. A `.md` or `.txt` file with the same name as a video holds the
person's own notes on it. Claude's contact sheets and breakdowns live in `.index/`.

## When a reference is named

1. **Index first.** Run `$MV/references.py index`. It makes a contact sheet and a notes
   stub for every video added since last time, and skips the rest. Run `init` if the
   folder doesn't exist yet.
2. **Find it.** `$MV/references.py show <name>`. A partial name works ("spinny" finds
   `spinny-logo.mov`). If it matches several, ask which one. If the person describes it
   instead of naming it ("the one with the blue wipe"), try
   `$MV/references.py find "blue wipe"` and `list`.
3. **Read their notes first.** `show` prints them. If they say "the wipe at 0:04", that's
   the element, even if the rest of the video looks more interesting.
4. **Look at the whole video.** Read `sheet.png` from the path `show` prints. The top of
   `notes.md` lists each tile's time, left to right and top to bottom. Use those times to
   find where the element happens.
5. **Study the element up close.** For motion, a sparse sheet hides the easing. Make a
   dense sheet of just that stretch:

   ```bash
   $MV/references.py look spinny-logo --start 3.2 --end 4.4 --count 24 --cols 6
   ```

   It prints each frame's time. Twenty frames over one second shows the curve: big gaps between tiles mean fast,
   bunched tiles mean it's settling. Look at what moves first, what overlaps, and what
   overshoots.
6. **Write the breakdown** into the video's `notes.md` (path from `show`). Replace the
   stub's placeholder lines. Keep it to what you'd need to rebuild it:
   - **Elements:** time range, what happens, and how to build it in HyperFrames (GSAP
     ease name, durations, stagger, layering, masks, blur).
   - **Style:** hex colors sampled from the frames, type (serif, geometric sans, weight,
     case, tracking), pacing (average shot length, how long text holds).
   - **Tags:** a few plain words people would search for ("kinetic type", "mask wipe",
     "grain", "3d tilt").

   The next session reads this instead of looking again, so a reference only needs
   studying once. Update the notes when you learn something new about it.
7. **Say what you'll take.** Before building, tell the person in a line or two which
   parts you're borrowing and how ("the staggered word drop: 60ms stagger, back.out,
   about 0.5s per word"). Borrow the technique, not the content: never copy another
   brand's logo, footage, copy or music into a deliverable.
8. **Build it**, using the **motion-techniques** skill for the patterns, and check your
   version against the reference with a contact sheet of the same stretch of your render
   (`$MV/contact_sheet.py renders/draft.mp4 --times ...`). Put both sheets side by side in
   your head and name what's still different.

Record which references a project used under **References** in its `NOTES.md`, with the
element taken from each.

## Other requests

- **"What do I have for X?"** Run `find`, then read the matching `notes.md` files and
  answer from them. Videos still showing `indexed` in `list` have no breakdown yet; read
  their sheets if they might fit.
- **"Go through my references."** For each video `list` shows as `indexed`, read the
  sheet and fill in `notes.md`. Do a few at a time and say which ones you did.
- **Mood board for a brief.** Pull two to four references that fit the brief, and say
  which element comes from each.
