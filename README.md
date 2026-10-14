# motion-video-skills

[![CI](https://github.com/tjdotwal/motion-video-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/tjdotwal/motion-video-skills/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/tjdotwal/motion-video-skills?sort=semver)](https://github.com/tjdotwal/motion-video-skills/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Make narrated motion videos with Claude Code: landing-page heroes, product explainers and
social cuts. You bring a brief. Claude writes or takes the script, generates the voiceover
locally, builds the sound bed, animates the product UI in HTML and renders a 60fps MP4
with [HyperFrames](https://github.com/heygen-com/hyperframes). It checks the result
before you see it.

Sample renders of both templates are attached to every
[release](https://github.com/tjdotwal/motion-video-skills/releases).

## What you get

- **A production workflow.** The `motion-video` skill takes a brief through script,
  voiceover, sound, build, QA and delivery, and asks only for what the brief leaves out.
- **Voiceover that sounds right.** Local Kokoro text-to-speech, word timings from Whisper,
  and fixes for the usual problems, like misread numbers and pauses inside them.
- **Sound that lands on the cuts.** Tools to map a music track's hits and rebuild it so
  they line up with your scenes.
- **Two templates that render out of the box:**
  - A 1200x1200 looping hero with a persistent checklist.
  - A 1920x1080 explainer with word-by-word captions.
- **QA tools.** Contact sheets, a loop-seam check and loudness checks.

## Install

You need [Claude Code](https://claude.com/claude-code), Node 22 or newer, ffmpeg and
Python 3.9 or newer. On a Mac with Homebrew: `brew install node ffmpeg`.

**1. Add HyperFrames and this plugin** (in Claude Code; the same commands work in the
terminal with `claude plugin ...`):

```text
/plugin marketplace add heygen-com/hyperframes
/plugin install hyperframes@hyperframes
/plugin marketplace add tjdotwal/motion-video-skills
/plugin install motion-video@motion-video-skills
```

**2. Set up the voice environment:**

```text
/video-doctor
```

It checks your machine and offers to run the setup, which installs Kokoro into
`~/.motion-video/venv`. It never uses sudo.

**3. Optional: install a plain-writing editor** for scripts Claude writes:

```sh
npx skills add petergyang/no-ai-slop --skill no-ai-slop --global --yes
```

### Without Claude Code

The scripts work on their own. Clone the repo and run setup:

```sh
git clone https://github.com/tjdotwal/motion-video-skills.git
cd motion-video-skills/motion-video/scripts
./setup.sh && ./doctor.sh
./new_video.py square-loop ~/videos/my-first-video
```

## Use it

Start a project from a template:

```text
/new-video square-loop ~/videos/spring-launch
```

Or describe what you want and the `motion-video` skill takes over:

> Make a 30 second square hero video for our booking app's pricing page. The H1 next to it
> is "Book, pay and remind in one place". Here's the brief and our logo.

Claude reads the brief, tells you what's missing, and shows draft frames before the
final render. Every project keeps a `NOTES.md`, so you or a later session can pick it up.

## What's inside

| Skill | Use it for |
| --- | --- |
| `motion-video` | The end-to-end workflow, from brief to delivered MP4 |
| `voiceover` | Generating, fixing and timing narration |
| `sound-bed` | Music and effects that hit on the cuts, plus loudness |
| `video-qa` | Lint, contact sheets, loop and loudness checks, and the handover checklist |
| `motion-techniques` | Patterns that make product videos feel continuous: one camera, a persistent element, a clean loop |

| Command | What it does |
| --- | --- |
| `/new-video [template] [folder]` | Checks your setup, creates a project from a template, starts the brief |
| `/video-doctor` | Checks HyperFrames, ffmpeg and the voice environment |

| Script (`motion-video/scripts/`) | What it does |
| --- | --- |
| `setup.sh`, `doctor.sh` | Install and check dependencies |
| `new_video.py` | Create a project from a template |
| `tts.sh`, `vo_finish.sh` | Generate a voiceover line, normalize it and get word timings |
| `vo_gaps.py` | Find and shorten pauses inside a spoken number or name |
| `captions.py` | Turn word timings into caption pages |
| `envelope.py`, `build_bed.py` | Map a track's hits and rebuild it to your cuts |
| `synth_bed.py` | Generate a rights-free placeholder bed |
| `contact_sheet.py`, `loop_check.py`, `loudness.py` | QA a render |

## Repository layout

```text
.claude-plugin/marketplace.json   marketplace entry (what /plugin marketplace add reads)
motion-video/                     the plugin
  .claude-plugin/plugin.json      plugin manifest (version lives here)
  skills/                         the five skills
  commands/                       slash commands
  scripts/                        stdlib Python and Bash tools
  templates/                      ready-to-render starter projects
scripts/                          repo tooling (validation for CI)
```

## Contributing

Changes go through pull requests, and CI must pass first. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the branch, commit and release conventions.

## Credits

- [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen (Apache-2.0) renders
  every video. This repo depends on it and doesn't copy it.
- [Prompt Motion](https://prompt-motion.com) inspired the techniques in `motion-techniques`.
  The prompts there belong to their creators, who are credited in
  [the reference list](motion-video/skills/motion-techniques/references/prompt-motion.md).
- [no-ai-slop](https://github.com/petergyang/no-ai-slop) by Peter Yang (MIT) is the
  optional writing editor.
- Voice: [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) through `kokoro-onnx`.

## License

[MIT](LICENSE). The demo brand in the templates, Brightdesk, is fictional.
