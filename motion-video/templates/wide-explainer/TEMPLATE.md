# 1920x1080 narrated explainer with word-by-word captions

Made for YouTube, social and in-product explainers where sound is on. The demo is a
fictional team-scheduling app, Brightdesk.

## Structure

| Time | Scene | What happens |
| --- | --- | --- |
| 0–3.8 | Problem | Five spreadsheets pile up and a conflict flag appears |
| 3.8–8.2 | Product | A shared calendar fills with shifts, swaps and classes |
| 8.2–13 | End card | Brand wipe, logo, CTA button click with confetti |

## Edit in this order

1. **Voiceover.** `scripts/tts.sh "Line." assets/vo/lN.wav` for each line. Update the `<audio>` tags.
2. **Captions.** Regenerate `CAPTIONS` with
   `scripts/captions.py assets/vo/l1.json@0.2 assets/vo/l2.json@4.0 --text "Line one." --text "Line two."`
   and paste the output over the array. `--text` keeps your exact wording and casing.
3. **Scenes.** Edit `SHEETS`, `CELLS`, `EVENTS` and the markup. Move scene times to the word timings.
4. **End card.** Change the logo and CTA. If the page already has a real button next to the
   video, delete `#cta`, the cursor and the confetti.
5. **Sound.** Replace `assets/music.wav` (see the sound-bed skill).

## Rules this template follows

- Each transition hides the outgoing scene after it finishes, so hidden scenes don't fail contrast checks.
- Confetti uses a seeded random generator, so every render is identical.
