#!/usr/bin/env bash
# Install everything motion-video needs that isn't already on the machine.
#   - checks Node 22+ and ffmpeg (prints install hints; never runs sudo)
#   - creates the voice environment (Kokoro TTS) in $MOTION_VIDEO_HOME/venv
#   - warms the HyperFrames CLI so the first render isn't slow
#
# Usage: setup.sh            # install
#        setup.sh --check    # same as doctor.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "--check" ]]; then exec "$HERE/doctor.sh"; fi

# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"

say() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

say "1/4 Checking Node"
command -v node >/dev/null || fail "Node 22+ is required. Install it from https://nodejs.org or with 'brew install node'."
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
(( NODE_MAJOR >= 22 )) || fail "Node $NODE_MAJOR found; HyperFrames needs 22+."

say "2/4 Checking ffmpeg"
command -v ffmpeg >/dev/null || fail "ffmpeg is required. macOS: 'brew install ffmpeg'. Ubuntu: 'sudo apt install ffmpeg'."

say "3/4 Creating the voice environment in $MV_VENV"
PY="$(command -v python3 || true)"
[[ -n "$PY" ]] || fail "Python 3.9+ is required."
if (( ${#MV_VENV} > 60 )); then
  fail "MOTION_VIDEO_HOME is too long (${#MV_VENV} chars). espeak, which Kokoro uses, fails on long data paths. Use a shorter folder."
fi
mkdir -p "$MOTION_VIDEO_HOME"
[[ -x "$MV_VENV/bin/python" ]] || "$PY" -m venv "$MV_VENV"
"$MV_VENV/bin/python" -m pip install --quiet --upgrade pip
"$MV_VENV/bin/python" -m pip install --quiet "kokoro-onnx>=0.4,<0.5" "soundfile>=0.12"

say "4/4 Warming the HyperFrames CLI"
npx --yes "hyperframes@${MV_HYPERFRAMES_VERSION}" --version >/dev/null

say "Done. Run doctor.sh any time to check the setup."
