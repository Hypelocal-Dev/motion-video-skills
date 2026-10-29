#!/usr/bin/env bash
# SessionStart hook. If this machine isn't set up for motion-video yet, tell Claude to
# offer the setup walkthrough. Prints nothing once setup is done. Fast and offline:
# no npx, no imports. doctor.sh does the full check.
#
# To stop the offer without finishing setup: touch ~/.motion-video/skip-setup
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"

[[ -e "$MOTION_VIDEO_HOME/skip-setup" ]] && exit 0

missing=()
if ! command -v node >/dev/null || (( $(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0) < 22 )); then
  missing+=("Node 22+")
fi
command -v ffmpeg >/dev/null || missing+=("ffmpeg")
command -v python3 >/dev/null || missing+=("Python 3")
compgen -G "$MV_VENV/lib/python*/site-packages/kokoro_onnx" >/dev/null || missing+=("the voice environment")

(( ${#missing[@]} == 0 )) && exit 0

list="$(printf '%s, ' "${missing[@]}")"
cat <<EOF
The motion-video plugin is installed, but this machine isn't set up for it yet. Missing: ${list%, }.
In your first reply, tell the person this in one sentence and offer to walk them through
setup now (the motion-video setup skill). If they say yes, follow that skill. If they
decline, carry on with what they asked. If they never want the offer again, run
touch "$MOTION_VIDEO_HOME/skip-setup".
EOF
