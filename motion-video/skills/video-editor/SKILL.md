---
name: video-editor
description: Open a local editor in the browser where the person watches the latest render and pins notes to exact frames, with an optional end time, a box dragged on the frame, and images or GIFs dropped in. Then work through the notes, render again and reply on each one. Use when someone working on a motion video says "let's edit this", "edit the video", "open the editor", "I want to make some tweaks", "let me leave notes" or "review the video", asks to put an image or GIF on screen at a moment, or says "check my notes". Also use after a draft render when the person wants to give feedback.
---

# Video editor

A page on the person's own machine where they watch the newest render and pin notes to
it. A note has a time or a stretch of time, the text, and optionally an area dragged on
the frame and files (images, GIFs, video, sound). You read the notes, change the
composition, render again and reply on each note in the page.

Scripts are in `<base dir>/../../scripts` (call it `$MV`). The editor is
`$MV/edit_video.py`. It serves on 127.0.0.1 only and needs nothing beyond Python and
ffprobe.

## When the person says "let's edit this"

1. **Find the project.** It's the folder with `index.html` you've been working on. If
   you can't tell which one, ask.
2. **Open the editor:** `$MV/edit_video.py open <project>`. It starts the server if it
   isn't running and opens the page in their browser. Run it again whenever they want
   the page back. It reuses the running server.
3. **Render if needed.** If `open` says there's no render, or that the composition changed
   after the newest one, draft-render to the path it prints:
   `npx hyperframes render -q draft -f 30 -o renders/edit-<n>.mp4`. The page picks up new
   renders by itself. Always render to a new `edit-<n>.mp4` so you never overwrite the
   file they're watching.
4. **Listen for notes.** Run `$MV/edit_video.py wait <project>` as a background command
   (`run_in_background`). When the person clicks **Send to Claude**, it prints the notes
   and exits, which wakes you. The page shows "Claude is listening" while it runs.
5. **Tell the person** in a few lines: the address `open` printed, how to leave a note
   (pause, type, ⌘↵), that dragging on the video marks an area, that they can drop or
   paste images and GIFs into a note, and to click Send to Claude when they're done.

If they say "check my notes" in chat instead of clicking Send, run
`$MV/edit_video.py notes <project>`.

## Work through the notes

For each open note the printout gives the id, the time in seconds and the frame, an end
time if it covers a stretch, the text, the marked area, attached files and a still.

- **Look at the still first.** Read `review/frames/<id>.jpg`. It's the frame they paused
  on, with their area boxed. Read the note against it.
- **Times are composition seconds** on the root timeline. Find the scene and the tweens
  that cover that time.
- **Areas are composition pixels** from the top-left, because the render is the
  composition's size. `x=458 y=459 w=311 h=211` means
  `left: 458px; top: 459px; width: 311px; height: 211px` on an element placed on the
  root. If the content sits on a moving camera or world canvas, put the overlay on the
  root above it, or convert the area into that layer's coordinates.
- **Attached files** are in `assets/incoming/`. Copy what you use into `assets/`.
- **An image over the screen:** an `<img>` positioned at the area, with
  `class="clip"`, `data-start`, `data-duration` and its own `data-track-index` on the
  `<img>` itself, not on a wrapper. Show it from the note's time to its end, or for about
  2 seconds if the note has no end. Give it a short entrance in the video's motion style,
  with the hidden start state set by `gsap.set`.
- **A GIF over the screen:** HyperFrames renders GIF frames on the composition's clock
  from 0:00, so a GIF that appears at 8.6s starts partway through its loop. That's fine
  for a seamless loop. For anything that should play from its first frame, like a burst,
  a reaction or a one-time animation, convert it to WebM with transparency and use a
  `<video>`, which starts at its own first frame at its `data-start`:

  ```bash
  ffmpeg -i assets/incoming/confetti.gif -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 -an assets/confetti.webm
  ```

  ```html
  <video id="confetti" class="clip" src="assets/confetti.webm" muted playsinline
         data-start="8.6" data-duration="2.77" data-track-index="6"
         style="position: absolute; left: 458px; top: 459px; width: 311px; height: 211px"></video>
  ```

  Don't put timing on a wrapper around a `<video>` (lint rejects it), and don't add
  `crossorigin`.
- **Archival footage or period music** ("old newsreel here", "1920s music under
  this"): use the **archive-media** skill. It finds a clip in the Prelinger or 78rpm
  collections and cuts it into `assets/archive/`.
- **A sound at a moment:** an `<audio>` with an `id` at that time, then re-check loudness
  with the sound-bed skill.
- **Timing notes** ("land a beat later", "hold longer"): move the tweens and keep each
  proof a beat after the word it proves.
- **Copy changes:** follow the brief's copy rules. If the copy is fixed by the brief, reply
  to ask before changing it.
- **Unclear notes:** reply with a question and leave the note open. Don't guess.

## Render, reply, listen again

1. Lint (`npx hyperframes lint`), then draft-render to the next `renders/edit-<n>.mp4`.
   Check each note's moment with `$MV/contact_sheet.py renders/edit-<n>.mp4 --times ...`.
2. Reply on every note you worked on, in a sentence or two that says what changed:

   ```bash
   $MV/edit_video.py reply <project> 3 "Moved the logo up 40px and brought it in 0.3s later." --done
   ```

   Leave out `--done` when the reply asks a question.
3. Start `wait` again in the background, and tell the person in a line or two which
   render to watch and anything you need from them.
4. Record decisions that came from notes in `NOTES.md`.

Repeat until they're happy, then deliver with the motion-video skill.

## Stop

The editor keeps running between rounds. When the person is done, stop it with
`$MV/edit_video.py stop <project>`. Notes stay in `review/notes.json`.

## Files

| Path | What it holds |
| --- | --- |
| `review/notes.json` | Every note and reply, and when notes were last sent |
| `review/frames/<id>.jpg` | The noted frame with the marked area drawn on it |
| `review/server.json`, `review/server.log` | The running editor's address and its log |
| `assets/incoming/` | Files dropped into notes |
