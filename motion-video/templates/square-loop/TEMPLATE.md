# 1200x1200 looping hero video with a persistent checklist

Made for a landing-page hero that autoplays muted and loops. The demo is a fictional
studio-booking app, Brightdesk. Swap in your own copy, voiceover and UI.

## Structure

| Time | Scene | What happens |
| --- | --- | --- |
| 0–4.1 | Week card | Three checklist pills (Booked, Paid, Reminded) appear beside the card |
| 4.1–8.3 | Phone | The pills fly to the dock. A member taps a class, then Book spot. Booked checks off |
| 8.3–11.9 | Payments | Pending tags flip to Paid. Paid checks off |
| 11.9–15.8 | Reminders | Notifications land and seats fill. Reminded checks off |
| 15.8–22 | End frame | Logo, wordmark and tagline. The last 0.4s fades to the opening frame |

## Edit in this order

1. **Copy and voiceover.** Write one line per scene. Generate each with
   `scripts/tts.sh "Line." assets/vo/lN.wav`, then update each `<audio>` tag's
   `data-start` and `data-duration`.
2. **Timing.** Move the scene times in the timeline to the word timings `tts.sh` prints.
   Check-offs read best a beat after the word they prove.
3. **Brand.** Change the CSS tokens at the top. Replace the logo mark and wordmark in panel 5.
4. **UI.** Edit the panel markup and the demo arrays (`CLASSES`, `PAYMENTS`). Keep names fictional.
5. **Sound.** Replace `assets/music.wav`. See the sound-bed skill to make a licensed
   track's hits land on the cuts. `scripts/synth_bed.py` makes a placeholder.

## Rules this template follows

- On-screen text carries the message on mute. The headline per scene says what the VO says.
- Nothing hard-cuts: `cam()` pans the world canvas.
- Initial states use `gsap.set` so frame 0 renders them. Repeated `fromTo` calls on one
  element use `immediateRender: false`.
- Keep the `#veil` fade at the end, or the loop shows a jump. Check it with `scripts/loop_check.py`.
