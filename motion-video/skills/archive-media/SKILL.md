---
name: archive-media
description: Find archival b-roll and period music on the Internet Archive and cut it into a motion video. Searches the Prelinger film collection (vintage ads, educational, industrial and home films) and the 78rpm record collection, trims a clip into the project and credits it in NOTES.md. Use whenever a video needs archival, vintage, retro, newsreel or old-film footage, period or old-timey music, a 1920s-1950s feel, or public-domain b-roll, including when a note in the video editor asks for it.
---

# Archive media

Scripts are in `<base dir>/../../scripts` (call it `$MV`). The tool is
`$MV/archive_media.py`. It needs Python and ffmpeg, and no account or key.

Whenever a video needs archival b-roll or period music, look in these two collections
before generating or licensing anything:

- **Prelinger** (`prelinger`): about 2,000 ephemeral films from 1903 to the 1980s, such
  as ads, driver's ed, industrial films and home movies. Most are public domain.
- **78rpm** (`78`): shellac records from the Great 78 Project, mostly 1900s to 1950s, with
  dance bands, jazz, ragtime, novelty songs and spoken word.

## Rights

- **Prelinger:** `search` and `files` show each item's rights. Use items marked public
  domain. If an item says "no license listed", read its page before using it.
- **78s:** in the US a recording enters the public domain 100 years after the end of its
  publication year. `search 78` returns only records old enough. `get` refuses later ones
  unless you pass `--allow-later`. Pass it only when the person says they hold a license.
- `get` writes the source, date, clip range and rights to the project's `NOTES.md` under
  **Archival sources**. Keep those lines. They are the record if a client or platform
  asks where a clip came from.

## Find it

```bash
$MV/archive_media.py search prelinger "kitchen appliances" --years 1950-1962
$MV/archive_media.py search 78 "fox trot" --rows 20
$MV/archive_media.py search prelinger 'subject:"Automobiles"'
```

Results are sorted by downloads, which surfaces the better-known, better-scanned items.
`--sort "date asc"` sorts by date instead. Search words match titles, descriptions and
subjects, so describe what's on screen ("assembly line", "family dinner") rather than
the mood.

Then look before you cut:

```bash
$MV/archive_media.py files WeDriver1936
```

This lists the video or audio files with their lengths and a thumbnail link. For a
film, find the shot. Fetch a low-res copy, run `$MV/contact_sheet.py` on it with
`--count 40`, and read the sheet to pick start and end times.

```bash
$MV/archive_media.py get WeDriver1936 /tmp/look --file WeDriver1936_512kb.mp4 --name look
```

`/tmp/look` needs an `index.html`, so use a scratch project, or fetch into the real
project and delete the preview afterwards. For a 78, listen to it, or read its
`_whisper_asr.json` to find where the singing starts, since the band intro is often the
usable part.

## Cut it in

```bash
$MV/archive_media.py get WeDriver1936 <project> --start 42 --end 46 --name drivers
$MV/archive_media.py get 78_charleston-mad_n-m-l-dance-orchestra_gbia0039051b <project> --start 8 --end 38 --name bed
```

A clip with `--start`/`--end` is cut straight from the URL, so a few seconds out of a
long film take a few seconds. Video comes out as H.264 MP4 without sound. Audio comes
out as 48kHz stereo WAV. Both land in `assets/archive/`.

- **Film b-roll:** a `<video>` with `class="clip"`, `muted`, `data-start`,
  `data-duration` and its own `data-track-index`, placed like any other clip. Old film is
  4:3 and soft. Crop it with `object-fit: cover` inside a frame, or keep the 4:3 and
  design around it. Grain and gate weave are part of the look, so don't over-sharpen.
  Prelinger films are often sped up or slowed down. If motion looks wrong, set
  `playbackRate` or retime with ffmpeg `setpts`.
- **78 music:** treat the WAV as the bed and continue with the **sound-bed** skill:
  `envelope.py` to map its hits, `build_bed.py` to fit it to the cuts, then the loudness
  check. 78s are mono and have surface noise. A gentle high-pass around 60Hz and a
  low-pass around 8kHz keep the period sound without the hiss. Turn the bed down under
  narration.

## From the editor

When a note in the video editor asks for archival footage or period music ("old
newsreel here", "1920s music under this"), search, cut the clip to the note's time range
(about 2 seconds if it has no end time), place it at the note's area, and reply with the
title and year so the person knows what they're looking at. If nothing fits, reply with
the two or three closest finds and their `/details/` links, and leave the note open.
