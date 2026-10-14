---
name: sound-bed
description: Build the music and sound-effect bed for a motion video so its hits land on the scene cuts. Use when adding background music, reusing a track or a reference video's audio, stretching or shortening a track to a new length, separating music from a voiced reference video, or checking loudness of a mix.
---

# Sound bed

Scripts are in `<base dir>/../../scripts` (call it `$MV`).

## Rights first

Use only audio you have the right to use: a licensed track, the client's own audio,
something you generated, or `$MV/synth_bed.py` for a placeholder. Note the source and
license in the project's `NOTES.md`.

## Separate music from a voiced reference (optional)

If a reference video has the music and effects you want under someone else's voice,
split it with Demucs:

```bash
python3 -m venv ~/.motion-video/demucs && ~/.motion-video/demucs/bin/pip install demucs
~/.motion-video/demucs/bin/demucs --two-stems vocals -o stems reference.mp4
```

`stems/htdemucs/reference/no_vocals.wav` is the bed. Its effects stay timed to the
reference's cuts, which is why the next step matters.

## Make the hits land on your cuts

1. **Map the track:**

   ```bash
   $MV/envelope.py no_vocals.wav
   ```

   This prints a loudness bar per second and a list of hits. `BIG` marks the strong ones.
   Low stretches are quiet regions you can repeat as padding.
2. **List your video's events** from the timeline plan: scene cuts, check-offs, the end
   frame. Decide which ones get a big hit.
3. **Plan segments.** Each segment copies a source range to an output time. To move a hit
   from source time `h` to video time `v`, start a segment at output time `v - (h - a)`,
   where `a` is the segment's source start. Fill gaps with quiet regions. Never cut
   through a hit.

   ```json
   {
     "duration": 41.0,
     "segments": [
       {"src": [0.0, 3.0], "at": 0.0},
       {"src": [7.6, 10.3], "at": 3.0},
       {"src": [3.0, 24.6], "at": 5.7},
       {"src": [16.4, 30.0], "at": 27.3}
     ]
   }
   ```

4. **Build it:**

   ```bash
   $MV/build_bed.py no_vocals.wav segments.json assets/music.wav
   ```

   It prints the seam times. Pass them on as "check by ear" points.
5. **Re-run `envelope.py`** on the result and confirm each big hit is within about 0.1s
   of its event.

## Loudness

- Voiceover clips: -13.5 LUFS each (`tts.sh` does this).
- Finished mix: about -14 to -12 LUFS integrated, true peak under -1 dBFS for web and
  social. Check it with `$MV/loudness.py renders/final.mp4`.
- If the voice gets buried, lower the bed with `data-volume` on its `<audio>` tag
  (try 0.7) rather than re-normalizing the voice.
