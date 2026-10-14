#!/usr/bin/env bash
# Normalize a raw voiceover take and write its word timings.
# tts.sh calls this. Run it yourself after editing a take (for example with vo_gaps.py --fix).
#
# Usage: vo_finish.sh take.raw.wav out.wav
#   writes out.wav (-13.5 LUFS, 48 kHz) and out.json (word timings), prints words and length
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"

[[ $# -eq 2 ]] || { sed -n '2,7p' "$0"; exit 2; }
RAW="$1"; OUT="$2"
BASE="${OUT%.wav}"
DIR="$(dirname "$OUT")"

ffmpeg -nostdin -v error -y -i "$RAW" -af "loudnorm=I=-13.5:TP=-1.5:LRA=11" -ar 48000 "$OUT"
npx --yes "hyperframes@${MV_HYPERFRAMES_VERSION}" transcribe "$OUT" </dev/null >/dev/null
mv "$DIR/transcript.json" "$BASE.json"

python3 - "$BASE.json" "$OUT" <<'PY'
import json, subprocess, sys
w = json.load(open(sys.argv[1])); w = w if isinstance(w, list) else w.get("words", [])
d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", sys.argv[2]],
                   capture_output=True, text=True).stdout.strip()
print(" ".join(f"{x['text'].strip()}@{x['start']:.2f}" for x in w))
print(f"duration {float(d):.2f}s")
PY
