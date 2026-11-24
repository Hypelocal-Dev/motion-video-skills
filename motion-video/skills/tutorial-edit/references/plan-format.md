# Formats: cut.json, plan.json, theme.json

All three live in the project. Times in `cut.json` are seconds in the raw recording.
Times in `plan.json` are seconds in the cut (the spine), except overlay-local times,
which count from the overlay's own `start`.

## work/cut.json

```json
{
  "source": "../footage/recording.mp4",
  "crop": "auto",
  "level": true,
  "tighten": {"min_gap": 0.55, "pad": 0.14},
  "segments": [
    {"kind": "speech", "from": 0.0,   "to": 11.5,  "tag": "intro"},
    {"kind": "hold",   "from": 56.4,  "dur": 2.0,  "tag": "ch1"},
    {"kind": "speech", "from": 57.0,  "to": 106.0, "tag": "ch1-folder"},
    {"kind": "speed",  "from": 452.6, "to": 616.0, "rate": 14, "tag": "skip-1"}
  ]
}
```

- `crop`: `"auto"` center-crops to 16:9 (a screen capture with an odd height loses a
  little top and bottom). Or `[w, h, x, y]` in source pixels.
- `speech`: 1x with sound. Pauses longer than `min_gap` are cut, keeping `pad` of air
  either side. Add `"tighten": false` to keep a pause.
- `hold`: `dur` seconds of muted footage from `from`, under a full-screen card.
- `speed`: muted, sped up by `rate`.
- `tag`: names the section in the `--dry` printout and in `spine_map.json`.

## work/plan.json

```json
{
  "agenda": ["Set up the workspace", "Write the brief", "Run it", "Check the result"],
  "overlays": [ ... ],
  "zooms": [[61.4, 67.5, 1060, 640, 2.0]],
  "covers": [[226.7, 231.1, 221.6]],
  "highlights": [[533.2, 538.5, 556, 283, 200, 30]],
  "captions": {
    "proper": {"acme": "Acme", "dms": "DMs"},
    "fixes": [[170, 176, "share", "reshare"]],
    "drop": ["um", "uh"],
    "hide": [],
    "max_words": 4, "max_chars": 26, "lowercase": true
  },
  "music": {"bed": "assets/audio/music.m4a", "low": 0.55, "high": 0.8, "sfx": true},
  "theme": {}
}
```

- `zooms`: `[start, end, x, y, scale]`. `x, y` is the point to center, in 1920x1080
  spine pixels. Start at 0 to begin zoomed. Scale 1.3-2.0.
- `covers`: `[start, end, media_start]`. Plays muted spine footage from `media_start`
  over a private stretch. Pick a clean moment of similar screen.
- `highlights`: `[start, end, x, y, w, h]`. A highlighter bar on screen text, in spine
  pixels; it zooms with the screen.
- `captions.fixes`: `[from, to, heard, replacement]`. The replacement applies only
  inside the time window. An empty replacement drops the word.
- `theme` overrides `brand/theme.json` for this video only.

### Overlay types

Every overlay has `type`, `start`, and usually `dur` and an `id` (default: type plus
index). Times inside lists are local to the overlay.

| type | fields | notes |
| --- | --- | --- |
| `agenda` | `title`, `kicker`, `note`, `list_label` | Full-frame. Lists `plan.agenda`. |
| `chapter` | `step` (1-based), `title` (default: the agenda item), `note`, `dur` (2) | Full-frame, echoes the agenda. Lifts the music. |
| `panel` | `kicker`, `title`, `items: [[t, text, sub], ...]`, `mark` (`"number"` or `"alert"`) | Docks right; pushes the screen left. |
| `stat` | `kicker`, `value` (number counts up), `unit`, `note`, `note_at`, `rows: [[t, label, value], ...]` | Docks right; pushes the screen left. |
| `chip` | `label`, `text`, `pos` (`tl`, `tr`, `bl`), `warn` | Tips, gotchas, fixes, results. |
| `skip` | `text`, `label` (`Fast-forward`) | Put it over each `speed` segment. Lifts the music. |
| `note` | `text`, `x`, `y`, `size` (58), `rot` (-2) | Handwritten aside. |
| `steps` | `head`, `note`, `steps: [[label, icon], ...]` (2 or 3), `beats: [t, ...]` | Full-frame sketch. Icons: `stack lens doc build check loop inbox clock bot`. |
| `sort` | `head`, `source`, `agent`, `source_icon`, `agent_icon`, `buckets: [[t, label], ...]`, `skip: [t, label]`, `beats: {"source": t, "agent": t}` | Full-frame sketch: source → agent → buckets. |
| `quote` | `lines` (HTML; wrap highlighted words in `<span class="hl">`), `hi_at`, `note` | Full-frame dark. Hides captions. |
| `kinetic` | `beats: [{"t", "text", "size", "accent", "gap"}]` | Full-frame dark close. Hides captions. |
| `end` | `cta`, `dur` (default: to the end) | Wordmark or logo. Hides captions. |

## brand/theme.json

```json
{
  "ink": "#2F6BFF", "deep": "#123A9C", "paper": "#F7F8FC", "line": "#DCE6FF",
  "dark": "#16161F", "soft": "#8E8FA6", "warn": "#E5484D", "bg": "#E8EEFF",
  "chip_label": "#9DB4FF",
  "head_font": "Poppins", "body_font": "Inter",
  "wordmark": "acme", "logo": "brand/logo-black.svg", "logo_on_dark": "brand/logo-white.svg"
}
```

- `ink` is the one accent: highlights, active caption word, numbers' companions.
  `deep` is a darker shade for big numbers. `paper` is the card color, `line` its rule
  and dot grid, `dark` the text and dark cards, `soft` muted text.
- Fonts: any Google Fonts family works (HyperFrames embeds it at render). For a brand
  font that isn't on Google Fonts, put the `.woff2` in `edit/assets/fonts/` and map it:
  `"font_files": {"Acme Sans": "assets/fonts/acme-sans.woff2"}`, then use
  `"head_font": "Acme Sans"`.
- `logo`: the logo for light backgrounds (the agenda slide). `logo_on_dark`: the version
  for dark backgrounds (the end card); leave it out when one full-color logo works on
  both. Paths are project-relative; the generator copies them into `edit/assets/brand/`.
  Without a logo, `wordmark` is set in the head font.
