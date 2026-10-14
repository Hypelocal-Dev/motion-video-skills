# Shared settings for the shell scripts. Sourced, not run.
# shellcheck shell=bash
export MOTION_VIDEO_HOME="${MOTION_VIDEO_HOME:-$HOME/.motion-video}"
export MV_VENV="$MOTION_VIDEO_HOME/venv"
# The HyperFrames CLI reads this to find a Python with Kokoro installed.
export HYPERFRAMES_PYTHON="$MV_VENV/bin/python"
# Minimum tested HyperFrames version. "latest" also works; pin when you need repeatable renders.
export MV_HYPERFRAMES_VERSION="${MV_HYPERFRAMES_VERSION:-latest}"
