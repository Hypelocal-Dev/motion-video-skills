#!/usr/bin/env bash
# Check that every tool motion-video uses is installed and working. Changes nothing.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"

ok=0; bad=0
pass() { printf '  \033[32m✓\033[0m %s\n' "$*"; ok=$((ok + 1)); }
miss() { printf '  \033[31m✗\033[0m %s\n' "$*"; bad=$((bad + 1)); }

echo "motion-video doctor"
if command -v node >/dev/null && (( $(node -p 'process.versions.node.split(".")[0]') >= 22 )); then
  pass "node $(node --version)"
else
  miss "node 22+ not found (https://nodejs.org)"
fi
if command -v ffmpeg >/dev/null; then pass "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"; else miss "ffmpeg not found (brew install ffmpeg)"; fi
if command -v ffprobe >/dev/null; then pass "ffprobe"; else miss "ffprobe not found (comes with ffmpeg)"; fi
if command -v python3 >/dev/null; then pass "python3 $(python3 --version | awk '{print $2}')"; else miss "python3 not found"; fi

if HF="$(npx --yes "hyperframes@${MV_HYPERFRAMES_VERSION}" --version 2>/dev/null)"; then
  pass "hyperframes $HF"
else
  miss "hyperframes CLI failed to run (npx hyperframes --version)"
fi

if [[ -x "$HYPERFRAMES_PYTHON" ]] && "$HYPERFRAMES_PYTHON" -c "import kokoro_onnx, soundfile" 2>/dev/null; then
  pass "voice environment ($MV_VENV)"
else
  miss "voice environment missing. Run setup.sh"
fi

if (( ${#MV_VENV} > 60 )); then
  miss "MOTION_VIDEO_HOME path is long (${#MV_VENV} chars); espeak may fail. Use a shorter folder."
fi

echo
if (( bad == 0 )); then echo "All $ok checks passed."; else echo "$bad problem(s). Fix them, or run setup.sh."; fi
exit $(( bad > 0 ))
