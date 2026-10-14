#!/usr/bin/env bash
# Generate one voiceover line, normalize it, and write its word timings.
#
# Usage: tts.sh "Text to speak." out.wav [voice]
#   writes  out.wav            normalized to -13.5 LUFS, 48 kHz
#           out.raw.wav        the untouched take (keep it; re-normalize from it)
#           out.json           word timings from Whisper
#   prints  each word with its start time, and the clip length for data-duration
#
# Write numbers the way people say them: "thirty five hundred plus", "seven days".
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"

[[ $# -ge 2 ]] || { sed -n '2,11p' "$0"; exit 2; }
TEXT="$1"; OUT="$2"; VOICE="${3:-af_heart}"
BASE="${OUT%.wav}"
RAW="$BASE.raw.wav"
DIR="$(dirname "$OUT")"
mkdir -p "$DIR"

[[ -x "$HYPERFRAMES_PYTHON" ]] || { echo "voice environment missing; run $HERE/setup.sh" >&2; exit 1; }

npx --yes "hyperframes@${MV_HYPERFRAMES_VERSION}" tts "$TEXT" -v "$VOICE" -o "$RAW" </dev/null >/dev/null
exec "$HERE/vo_finish.sh" "$RAW" "$OUT"
