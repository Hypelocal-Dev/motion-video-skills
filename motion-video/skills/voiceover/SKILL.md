---
name: voiceover
description: Generate, fix and time narration for a motion video with local Kokoro TTS. Use when writing VO lines for text-to-speech, generating voiceover clips, getting word timings for animation or captions, or fixing a line that sounds wrong (misread numbers, odd pauses, mispronounced names).
---

# Voiceover

Scripts are in `<base dir>/../../scripts` (call it `$MV`). The voice environment comes
from `$MV/setup.sh`.

## Generate a line

```bash
$MV/tts.sh "Every class needs to be booked, paid and reminded." assets/vo/l1.wav
```

This writes:

- `l1.wav`, normalized to -13.5 LUFS at 48 kHz.
- `l1.raw.wav`, the untouched take. Re-normalize from it, never from `l1.wav`.
- `l1.json`, the word timings.

It also prints each word's start time and the clip length. Put the length in the
`<audio>` tag's `data-duration`. Lines play on alternating track indexes and must not
overlap. Leave at least 0.2s between lines.

Default voice: `af_heart`. Pass a third argument for another Kokoro voice. Keep one voice
across a video, and across a series.

## Write for the voice

TTS reads text literally. Write lines the way a person says them:

| Written | Write it as |
| --- | --- |
| 3,500+ | thirty five hundred plus |
| 7 days a week | seven days a week |
| 24/7 | twenty four seven |
| $49/mo | forty nine dollars a month |
| U11 | U eleven (check the transcript) |
| example.com | example dot com |

On-screen text keeps the written form ("3,500+"). Only the TTS input changes.

## Check every take

You can't hear the audio, so measure it:

1. **Read the transcript** that `tts.sh` prints. If a word comes back wrong, the voice
   probably said it wrong. Brand names are the usual problem: respell them phonetically
   in the TTS text, or accept the pronunciation and tell the person.
2. **Scan numbers and names for pauses.** Voices often leave a gap inside a spoken
   number, and it sounds like a stumble. Use the number's start and end from the timings:

   ```bash
   $MV/vo_gaps.py assets/vo/l5.raw.wav --start 0.55 --end 1.70
   ```

   The first gap is usually the normal break before the number. A second gap of 60ms or
   more inside the number is the stumble. Cut it to about 35ms:

   ```bash
   $MV/vo_gaps.py assets/vo/l5.raw.wav --start 0.55 --end 1.70 --fix assets/vo/l5.fixed.raw.wav
   ```

   Then finish it, which normalizes and re-transcribes, and update `data-duration`:

   ```bash
   $MV/vo_finish.sh assets/vo/l5.fixed.raw.wav assets/vo/l5.wav
   ```

   A good sign is that Whisper now hears the number as one token ("3,500").
3. **Tell the person what to check by ear**, with timestamps. Don't say it sounds right
   when you only measured it.

## Word timings drive the edit

Use the JSON timings to place everything: headline entrances, taps, check-offs and
caption highlights. For captions, `$MV/captions.py` turns the timings into caption
pages. Pass `--text` with the original lines so captions keep your exact wording.
