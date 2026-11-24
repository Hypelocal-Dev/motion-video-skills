#!/usr/bin/env bash
# Rebuild a tutorial edit after any change to work/plan.json:
#   brand theme -> plan, generate the composition, mix the bed under the voice, lint.
# Usage: tutorial_build.sh PROJECT
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR source=_env.sh
source "$HERE/_env.sh"
PROJECT="${1:?usage: tutorial_build.sh PROJECT}"

python3 "$HERE/tutorial_gen.py" "$PROJECT"
python3 "$HERE/tutorial_mix.py" "$PROJECT"
cd "$PROJECT/edit"
npx --yes "hyperframes@${MV_HYPERFRAMES_VERSION}" lint
