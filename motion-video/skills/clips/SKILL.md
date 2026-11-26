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

- **Source video.** After a tutorial edit, use the cut spine (`edit/assets/spine.mp4`),
  not the raw recording, so the pauses are already gone. Run
  `python3 $MV/clips_find.py prep <project>` first: it re-transcribes the spine when its
  word timings are missing or older than the spine (a re-cut makes old timings wrong),
  and writes a `clips.json` skeleton with the brand theme, caption names and privacy
  covers. Otherwise any video works.
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
2. **Privacy covers.** `prep` copies the tutorial's covers. For other sources, add any
   you need.
3. `python3 $MV/clips_find.py frames clips.json` makes a sheet per clip, 8 frames large
   enough to read screen text. Look at every one. Drop or move a clip when:
   - the moment isn't on screen (audio finds the sound, not the picture), or the subject
     is out of frame;
   - anything private shows. Tutorial covers only protect what the tutorial showed: a
     clip can expose a stretch the tutorial hid under a full-screen card. Add a cover
     or move the clip edge.

## 5. Choose a layout per clip

- **Screen recordings of chat, docs or long text** (the usual tutorial): `focus` at zoom
  0.75-0.9, centered on the text column. It shows the whole column at a size a phone can
  read and leaves a band at the top for the title. Measure the column's center and width
  on a full-size frame; the window is about 607/zoom source pixels wide.
- **Screen recordings where one small area matters** (a button, a setting, a chart):
  `focus` with keyframes that follow it, zoom 1.2-1.6.
- **Screen recordings where the whole layout matters:** `stack`. Its text is small on a
  phone, so use it only when the layout is the point.
- Never plain `center` on a screen recording: it crops the middle of the UI.
- **One person on camera:** `center`. Check the face sits in the middle third.
- **Two people:** `pan` (hard cuts to whoever talks) or `split` (both visible, the active
  speaker on top). Get speaker turns first: sample a frame, put a box over each mouth
  and chin, check the boxes by drawing them on the frame (at most two tries), then
  `python3 $MV/clips_speakers.py <video> --left x,y,w,h --right x,y,w,h --start S --end E -o work/speakers-<name>.json`.
- **Wide event or sports footage with a broadcast score bar** (fight nights, games,
  races): `event`. The whole shot sits in a band over a blurred copy of itself, so nothing
  is cropped and 720p stays sharp. The score bar is cut out and pinned under the band
  (spec `scorebar: [x, y, w, h]`; measure it on a full-size frame) so names and the clock
  are always readable. Add `punch` windows on the big moves (zoom 1.3-1.6; more looks soft
  on 720p). Multi-camera broadcasts switch angles, so aim each punch at a full-size frame
  from inside its window, not at a guess.
  - **Tighter on the action:** set `band_aspect` (1.25 suits 9:16 stories) to show a
    window that follows the athletes instead of the full width. Get the path with
    `"$MV_VENV/bin/python" $MV/clips_track.py <video> --start S --end E -o work/follow-<name>.json --sheet work/sheets/<name>.jpg`
    and point the clip's `follow` at the JSON. Look at the sheet: the yellow box should
    hold the athletes in every frame. It finds them as the densest non-floor cluster on
    the mat (`--floor blue|green|red`), ignores floor logos, and marks camera cuts.
    With a following window, `punch` can be `[from, to, zoom]`; skip punches on close
    camera angles, which are already tight.
  - **`upscale: 1.5`** pre-scales the source with lanczos and light sharpening, which
    holds up better than browser scaling when a 720p window is blown up.
  - **Montages and multi-part clips:** give `segments: [[a, b], ...]` instead of
    `start`/`end`. They're joined with a quick flash, and `punch`, `follow` and
    `callouts` times run on the joined timeline (`clips_track.py --segments a-b,c-d`
    matches). Score bars update 2-3 s after the move, so end each segment a few seconds
    after the score change you want on screen.
  - A clip can take its own `source` when one project pulls from several files.
  - **Music under a clip** (`music`, `music_volume`, `source_volume`, on the spec or a
    clip): use it when the source has no usable sound, such as a stream audio dropout.
    Rights-cleared sources: a public-domain 78 from the **archive-media** skill (cut,
    then high-pass 60 Hz and low-pass 8 kHz), or an original lo-fi bed from
    `"$MV_VENV/bin/python" $MV/tutorial_bed.py <dir> --seconds N`. Credit the source in
    the project's notes.
  - Stories: 9:16 event clips keep clear of Instagram's top bar and reply box (`safe`:
    [top, bottom] in px). Keep story clips under 60 s including the end card.
- **A slow stretch inside a good clip:** speed the whole clip a little with `"rate": 1.1`
  to `1.25`, or end it earlier. Above 1.25 speech sounds rushed.

## Finding moments in event footage

Hit detection doesn't work on grappling or most sports. Use these instead:

- **The score bar.** Tile a crop of it every 5 s (`ffmpeg ... crop=...,fps=1/5,tile=4x30`)
  and read when points, advantages, the clock or a winner tag change. A frozen clock with
  a winner tag means a finish.
- **Crowd loudness.** Per-second RMS (see `clips_find.py` or a short numpy pass) shows
  where the room erupts. Silence usually means a full-screen card between matches.
- Then look at 1 frame per second around each change to see the move, and name callouts
  only for what you can see. If you can't tell the technique (heel hook or ankle lock?),
  use the general word ("SUBMISSION").

Extras for highlight clips: `tag` (matchup pill), `callouts` (`[t, "TAKEDOWN", "+2"]`,
land them on the move, not on the score update), spec `sponsor` and `endcard`, and
`loudness: -14` when the room audio is quiet. Formats can be any `WxH`, such as `1200x1200`.

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
