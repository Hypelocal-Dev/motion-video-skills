---
name: motion-video
description: End-to-end workflow for making a narrated product or UI motion video (landing-page hero, explainer, social cut) with HyperFrames. Use when someone asks for a motion video, animated explainer, hero video or product animation from a brief, a landing page, a script or a reference video. Covers brief intake, script, voiceover, sound bed, composition, QA and delivery, and routes to the voiceover, sound-bed, video-qa, video-editor and motion-techniques skills.
---

# Motion video

Turn a brief into a finished MP4: script, voiceover, sound bed, an animated HTML
composition rendered by HyperFrames, and a QA pass before anyone sees it.

**Scripts** for every step live in this plugin's `scripts/` folder, two levels up from
this skill's base directory. Set `MV=<base dir>/../../scripts` and call `$MV/tts.sh`,
`$MV/contact_sheet.py` and so on. Run `$MV/doctor.sh` first in a new environment. If it
fails, run `$MV/setup.sh`.

**HyperFrames** does the rendering. Its own skills cover the composition contract (data
attributes, timelines, lint rules). Install them with
`claude plugin marketplace add heygen-com/hyperframes` then
`claude plugin install hyperframes@hyperframes`, and read `/hyperframes` when you need
framework detail. This skill is the production workflow on top.

## 1. Read the brief before anything else

Get these answered from the brief or the person. Ask only for what's missing.

- **Placement.** Where it plays and what sits next to it: the page H1, a real CTA button,
  the section it heroes. If a real button sits beside the video, don't animate one.
- **Format.** 1200x1200 square, 1920x1080 wide or 1080x1920 vertical. Loop or not.
  Autoplay muted or sound-on. Target length.
- **Audience and angle.** Who watches and what they already believe. A switcher from a
  competitor needs different pains than a first-time buyer. Build the story for this
  page and this audience. Don't reuse a sister video's story because it exists.
- **Copy rules.** Is the VO and on-screen text given exactly, or yours to write? Are
  claims, numbers, prices or competitor names allowed? Is there banned UI (ads, upsells)?
- **Assets.** Logos, icons, product screenshots, people photos, a reference video, a
  music track and its license.

If several versions exist, never overwrite one. Give each a new project and file name
that says its angle (`-search`, `-switchers`, `-short`).

## 2. Script

- One VO line per scene beat. Each line should be speakable in the scene's time.
- Muted viewers see only on-screen text, so each scene gets a short headline that
  carries its point.
- Write plainly. If the `no-ai-slop` skill is installed, run it on any copy you wrote.
  Never edit copy the brief says to use exactly.
- Write numbers for the voice the way people say them. See the voiceover skill.

## 3. Assets

- Scan what was provided. Make a contact sheet of the images
  (`$MV/contact_sheet.py` works on images too if you pass `--times 0`, or tile them with
  ffmpeg) and say what you'll use, what you won't, and what's still missing.
- Prefer vector logos and icons. A logo SVG may only wrap a PNG; check before trusting it.
- Crop people photos tight, and make sure no banned text from the source image survives
  the crop.
- Keep the source files in `assets/incoming/` and copy what you use into `assets/`.

## 4. Voiceover

Use the **voiceover** skill. Out of it you get normalized clips, word timings and clip
lengths. Those timings drive every animation time that follows.

## 5. Plan the timeline

Write a table before building: scene, start and end, VO line, on-screen text, and the
moment that proves the line (a check-off, a tag flipping, a count updating). Put each
proof a beat after the word it proves.

## 6. Sound bed

Use the **sound-bed** skill. Plan the bed against your scene cuts so the hits land on
them.

## 7. Build

Start from a template: `$MV/new_video.py --list`, then `$MV/new_video.py square-loop <dir>`.
Read the template's `TEMPLATE.md`. Then:

- Build each scene's end state in HTML and CSS first, then animate into it.
- Use the **motion-techniques** skill for the patterns: the world canvas with a camera,
  a persistent element that resolves (checklist, inbox), check-offs that fly from the UI
  to the element, a loop that matches its first frame.
- Lint after every meaningful change: `npx hyperframes lint`. Lessons that cost time:
  - Set initial hidden states with `gsap.set`, not `tl.set(..., 0)`, or frame 0 shows them.
  - Repeated `fromTo` on one element needs `immediateRender: false`.
  - Don't tween `top` or `left`; tween `x` and `y`.
  - Don't set `transform` in CSS on an element GSAP scales or moves; set it with `gsap.set`.
  - No template-literal selectors in `querySelector`; use `getElementById(id).querySelectorAll(...)`.
  - Hide a scene after its exit transition so it can't fail contrast checks.
  - An element inside a card that has a transform can't render above a later sibling
    card. Give the card a `z-index` when something drags out of it.

## 8. QA

Use the **video-qa** skill. Draft-render at 30fps, look at contact sheets, fix, and
repeat. Then do the final render at 60fps, with the loop and loudness checks.

## 9. Edit with the person

Use the **video-editor** skill. Open the editor on the newest draft so the person can pin
notes to frames, mark areas and drop in images or GIFs. Work through each round of notes,
render again and reply on each note until they're happy. Do this whenever they say
"let's edit this", even after delivery.

## 10. Deliver

- Final render: `npx hyperframes render -q delivery -f 60 -o renders/<Name>.mp4`, then
  copy it to the delivery folder.
- Fill in the project's `NOTES.md`: purpose, brief rules, narration with start times,
  scenes, audio plan, decisions. The next session reads it first.
- Report back plainly:
  - What changed.
  - Anything you couldn't verify. You can measure audio, not hear it, so name the
    seam times to check by ear.
  - Any brief rule you had to interpret.
  - Mock data shown on screen.
