---
description: Check that HyperFrames, ffmpeg and the voice environment are installed and working
---

Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.sh"` and report the result in plain words.
If something failed, explain the fix. Offer to run
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh"`, which installs the voice environment and
warms the HyperFrames CLI. It never uses sudo.
