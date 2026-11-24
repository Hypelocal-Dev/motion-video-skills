---
name: tutorial-edit
description: Edit a long screen recording (a tutorial, walkthrough, how-to or demo, often 10-60 minutes with someone narrating) into a tight, branded landscape video with an agenda opener, chapter cards, captions, zooms, side panels, sketch diagrams and a music bed. Use when someone drops a long recording and says "edit this", "turn this into a tutorial", "make this watchable", "cut this down", "set up a video editing project for this recording", or asks for a how-to or walkthrough video from footage they recorded. Also use to set up the project folders for one. For short clips from a long video, use the clips skill afterward.
---

# Tutorial edit

Turn a long, raw screen recording into a 5-12 minute tutorial people finish. The voice
and picture come from the recording. You cut it down, then lay designed graphics over
it with HyperFrames.

Scripts are in `<base dir>/../../scripts` (call it `$MV`). Python scripts are stdlib
unless they say otherwise; `tutorial_bed.py` needs numpy, so run it with
`$MV_VENV/bin/python` (setup.sh makes that environment). HyperFrames renders. Its
skills (`/hyperframes`) own the composition contract; this skill is the edit on top.

Read these when you reach their step:

- `references/craft.md`: the creative calls that make these videos work. Read it before
  you write the cut list and again before the plan.
- `references/plan-format.md`: the `cut.json` and `plan.json` formats.
- `references/brand.md`: turning brand guidelines into `brand/theme.json`.

## 1. Set up the project and ask for the inputs

1. `python3 $MV/tutorial_new.py new <folder> [--footage <recording>] [--brand <kit>]`.
   It makes `footage/ inspo/ brand/ work/ edit/ renders/`, scaffolds HyperFrames in
   `edit/`, fetches the note font and prints a checklist. `--brand` copies a saved
   brand kit (`tutorial_new.py brand-list` shows them). Ask before moving a file; use
   `--move` only when the person says so.
2. Ask for whatever the checklist marks, in one message:
   - **Footage** (required): the raw recording in `footage/`.
   - **Inspo**: 2-3 videos whose captions, motion or pacing they like, dropped in
     `inspo/` or pasted as links. A note file beside a video (`clip.md`) says what to
     borrow. Inspo is the biggest lever on style, so always ask.
   - **Brand**: the guidelines PDF, logo files and fonts in `brand/`, or the name of a
     saved kit. Always ask, so the whole video is on brand.
   If they skip inspo or brand, say what you'll fall back to (the default look, neutral
   colors) and carry on.
3. Run `tutorial_new.py status <folder>` whenever they say they've added something.

## 2. Brand

Follow `references/brand.md`: read the guidelines, write `brand/theme.json` (colors,
fonts, wordmark, logo), show the person the palette in one line, then offer to save it:
`tutorial_new.py brand-save <name> <folder>`. Saved kits live on this machine only.

## 3. Study the inspo

- Links: download with `yt-dlp -o "inspo/%(uploader_id)s-%(id)s.%(ext)s" <url>` (ask
  before installing it). Keep a list of sources in `NOTES.md`.
- For each video: `$MV/contact_sheet.py <video> --count 24 --cols 8`, then look. Note
  the caption style, the kinds of motion elements, pacing and palette.
- Borrow the vibe, caption type and kinds of motion. Never recreate a video: nobody
  should be able to name the source. Write what you'll borrow in `NOTES.md`.

## 4. Understand the recording

1. Transcribe the raw footage: `npx hyperframes transcribe footage/<file> -d work`.
   Read it all. Note the narrator's name if it shows on screen, the example, the steps.
2. `python3 $MV/tutorial_cut.py silences <folder>` lists long pauses. Long ones are
   usually the tool working; they become fast-forwards.
3. Contact sheet of the raw recording (`contact_sheet.py --count 36 --cols 6`) to see
   what's on screen across the whole thing.

## 5. Confirm the brief (one round of questions)

Ask only what you can't infer, as options with a recommendation first:

- **Length**: a third to a half of the raw length is typical (25 min raw to 8-10 min).
- **Look**: which inspo leads, or a mix.
- **Captions**: full, small and clean (recommended for muted feeds), key phrases only, or none.
- **Review**: plan and stills first (recommended for anything long), or straight to a draft.

Then state what you're assuming (frame size and crop, opener, chapters, music, end card)
in a short list so they can correct it. If they say "use your judgment", make the calls
in `references/craft.md` and keep going.

## 6. Cut

1. Write `work/cut.json` (format: `references/plan-format.md`; rules: `references/craft.md`).
2. `python3 $MV/tutorial_cut.py build <folder> --dry` prints each tagged section and the
   total. Adjust until the length is right, then run it without `--dry`. It renders
   `edit/assets/spine.mp4`, levels the voice to about -14 LUFS and writes
   `work/spine_map.json`.
3. Transcribe the spine and normalize the words:
   `npx hyperframes transcribe edit/assets/spine.mp4 -d work && python3 $MV/tutorial_cut.py words <folder>`.
4. Check every edit point by reading the spine transcript around each cut. A clipped
   last word means the cut sits inside speech: move the segment end to the next pause
   (`tutorial_cut.py map` and the pauses in `work/silences.json` help), rebuild.

## 7. Privacy sweep (never skip)

`python3 $MV/tutorial_cut.py sweep edit/assets/spine.mp4` makes contact sheets every 3
seconds. Look at every tile for desktops, other apps, Slack, email, password managers,
other chats or projects, other clients' work and personal tabs. For each hit, look
second by second (`contact_sheet.py --times`), then cover it: add
`[start, end, clean_media_start]` to `plan.covers`. A cover plays muted spine footage
from a clean moment over the bad stretch while the voice keeps going. Customer names
in the product being demoed are the person's call; ask once.

## 8. Plan the graphics

1. Read `references/craft.md` again. Write `work/plan.json`: agenda, chapters, panels,
   chips, notes, diagrams, a quote, outro, end card, zooms, covers.
2. Find times with `tutorial_cut.py find <folder> "phrase"` (spine seconds). Put a
   graphic a beat after the word it proves.
3. Zoom targets: grab spine frames (`contact_sheet.py edit/assets/spine.mp4 --times ...
   --width 960`) and read the UI position in 1920x1080 pixels.
4. Caption fixes: list brand and product names under `captions.proper`, and mishearings
   under `captions.fixes` with a time window.

## 9. Build, review, render

1. Music and effects: `"$MV_VENV/bin/python" $MV/tutorial_bed.py <folder>` (an original
   synthesized lo-fi bed; use a licensed track instead when the brand has one, saved as
   `edit/assets/audio/music.m4a`). For the carve, install core once in `edit/`:
   `npm i -D @hyperframes/core`.
2. `bash $MV/tutorial_build.sh <folder>`: generates the composition, carves the bed
   under the voice, lints. Run it after every plan change. Never hand-edit the
   generated HTML.
3. Stills: `npx hyperframes snapshot --at <key moments> --no-end -o boards/stills` in
   `edit/`, and look at every one. If review was requested, write the storyboard board
   (`/hyperframes` storyboard recipe) and stop for a go.
4. `npx hyperframes check` must pass. Long stretches with no graphic motion (12 s or
   more) get a slow punch-in.
5. Open the preview (`npx hyperframes preview --background`) and ask: render now or
   changes? Render with
   `npx hyperframes render -o ../renders/<Name>-v<N>.mp4 --video-frame-format png`
   (png keeps UI text sharp). Never overwrite an earlier render.
6. Verify the file: duration, `$MV/loudness.py`, and a contact sheet across it.

## 10. Deliver

Report the path, length and what changed. Say plainly what you couldn't check (you
can't hear the music). Update `NOTES.md` with status and decisions. Offer the clips
skill for vertical cuts.
