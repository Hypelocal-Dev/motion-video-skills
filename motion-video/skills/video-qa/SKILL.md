---
name: video-qa
description: Check a rendered motion video before handing it over. Use after any HyperFrames render, before delivering a video, or when someone reports a visual or audio problem. Covers lint, draft renders, contact sheets, loop seams, loudness and the delivery checklist.
---

# Video QA

Scripts are in `<base dir>/../../scripts` (call it `$MV`).

## Loop

1. **Lint:** `npx hyperframes lint`. Fix every error. Read every warning. Some warnings
   are known and fine (duplicate image sources, file length). Say which ones you left.
2. **Draft render:** `npx hyperframes render -q draft -f 30 -o renders/draft.mp4`.
   It takes about a second of render time per second of video.
3. **Contact sheet** at the moments that matter, not just even spacing:

   ```bash
   $MV/contact_sheet.py renders/draft.mp4 --times 0.05,4.9,7.6,11.6,16.6,19.8 --cols 3
   ```

   Pick the frame just after each entrance, each check-off and each transition, plus the
   first and last frames. Then read the sheet.
4. Fix and repeat. Re-render only what you need to check, and re-check the frames that
   changed.

## What to look for on every sheet

- **Text.** Headlines overflow the frame or wrap badly. Watch for orphans and lines that
  end on "and", and for a scaled-up headline that runs off the edge.
- **Overlaps.** Two layers land on each other, or a floating element covers UI.
- **Hidden layers.** A tag, chip or toast never appears, usually because it sits under
  a later sibling or its initial state was never reversed.
- **Targets.** A cursor or tap lands off its button, or confetti fires from the wrong spot.
- **See-through screens.** A phone screen that slides over another needs its own
  background.
- **Stray state.** A green check box left behind, or a gap left where an item was removed.
- **Brief rules.** Banned words or UI on screen, invented claims, competitor names, an
  animated CTA when the page has a real one.

## Final render and checks

```bash
npx hyperframes render -q delivery -f 60 -o renders/<Name>.mp4
$MV/loop_check.py renders/<Name>.mp4        # looping videos: PASS at 40 dB or more
$MV/loudness.py renders/<Name>.mp4          # about -14 to -12 LUFS
```

## Handover checklist

- [ ] Lint has 0 errors, and you can say what each remaining warning is.
- [ ] Contact sheets checked for every scene and transition.
- [ ] Loop check passes (looping videos).
- [ ] Loudness is in range.
- [ ] `NOTES.md` is updated.
- [ ] The report names what to check by ear, with timestamps, and lists mock data and
      judgment calls.
