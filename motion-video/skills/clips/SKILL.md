---
name: clips
description: Cut short social clips (vertical 9:16, square or wide) out of any longer video, such as a tutorial edit, podcast, interview, talking head, webinar, demo or action footage, with reframing, big word-by-word captions, a title tag and brand colors. Use when someone says "make clips from this", "cut shorts", "find the best moments", "make vertical versions", "reels from this video", "clipify", "cut on each hit/chop/beat", or after a tutorial edit when they want social cuts of it.
---

# Clips

Find the moments worth posting in a longer video, cut each one as a standalone clip,
reframe it for the feed, add captions and a title, and render. Each clip is its own small
HyperFrames project under `clips/<name>/`, so any one can be tweaked and re-rendered.

Scripts are in `<base dir>/../../scripts` (call it `$MV`). `clips_transients.py` needs
numpy: run it with `$MV_VENV/bin/python`. Read `references/finding-moments.md` before
picking moments.

## 1. Inputs

- **Source video.** After a tutorial edit, use the cut spine (`edit/assets/spine.mp4`)
  and its words (`work/spine_words.json`), not the raw recording, so the pauses are
  already gone. Otherwise any video works.
- **Word timings.** If there's no transcript yet: `npx hyperframes transcribe <video> -d <dir>`.
- **Brand.** Use the project's `brand/theme.json` if there is one. If not, ask for brand
  colors or a saved kit (`tutorial_new.py brand-list`), the same as tutorial-edit.
- **Format.** Default 9:16. Ask only if the destination isn't clear.

## 2. Pick the mode

- **Dialogue** (default: tutorials, podcasts, interviews, talking heads): find moments
  in the transcript.
- **Action** (chopping, sports, drumming, anything with repeated impacts and no
  talking): find each hit with
  `"$MV_VENV/bin/python" $MV/clips_transients.py <video>` and cut a beat around each
  (about 0.4 s before the hit to 0.5 s after). Skip captions.
- **Hybrid:** dialogue for the talking, action for the rest.

## 3. Find the moments

1. `python3 $MV/clips_find.py lines <words.json>` prints the transcript as timed lines.
   Read all of it.
2. Pick 3-8 candidates using `references/finding-moments.md`. For each, write the start,
   end, why it works and a title (2-7 words, the hook in plain words).
3. Show the list and let the person pick, unless they said to go ahead.

## 4. Write clips.json and check every frame

1. Write `clips.json` next to the source project (format in `$MV/clips_make.py --help`).
   Start and end on sentence boundaries: use the word times, never a guess.
2. **Privacy covers.** When cutting from a tutorial edit, copy `work/plan.json`
   `covers` into `clips.json` `covers`.
3. `python3 $MV/clips_find.py frames clips.json` makes a sheet per clip. Look at every
   one. Drop or move a clip when:
   - the moment isn't on screen (audio finds the sound, not the picture), or the subject
     is out of frame;
   - anything private shows. Tutorial covers only protect what the tutorial showed: a
     clip can expose a stretch the tutorial hid under a full-screen card. Add a cover
     or move the clip edge.

## 5. Choose a layout per clip

- **Screen recordings:** `stack` (the whole frame, title above, captions below) when the
  viewer needs to see the UI; `focus` with keyframes when one area matters (follow the
  cursor or the panel being discussed; zoom 1.2-1.6). Never plain `center` on a screen
  recording: it crops the middle of the UI.
- **One person on camera:** `center`. Check the face sits in the middle third.
- **Two people:** `pan` (hard cuts to whoever talks) or `split` (both visible, the active
  speaker on top). Get speaker turns first: sample a frame, put a box over each mouth
  and chin, check the boxes by drawing them on the frame (at most two tries), then
  `python3 $MV/clips_speakers.py <video> --left x,y,w,h --right x,y,w,h --start S --end E -o work/speakers-<name>.json`.
- **A slow stretch inside a good clip:** speed the whole clip a little with `"rate": 1.1`
  to `1.25`, or end it earlier. Above 1.25 speech sounds rushed.

## 6. Build, look, render

1. `python3 $MV/clips_make.py clips.json` builds every clip project and lints it.
2. Snapshot each (`npx hyperframes snapshot --at 1,5,10 --no-end -o snap` in its folder)
   and look: title readable, captions never cover the subject, nothing private.
3. `python3 $MV/clips_make.py clips.json --render` renders to `clips/renders/`. Use
   `--only <name>` to redo one, and `--quality draft` while iterating.
4. Check each file: duration, `$MV/loudness.py`, and a contact sheet.

## 7. Deliver

List each clip: name, length, the hook, and its path. Say which you'd post first and
why. Note anything you couldn't check by ear.

## Credits

Moment-finding signals, the speaker-pan method and the transient detector are adapted
from [clipify](https://github.com/louisedesadeleer/clipify) by Louise de Sadeleer,
MIT License, Copyright (c) 2026 Louise de Sadeleer. The license text is in
`references/clipify-license.txt`.
