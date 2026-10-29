---
name: setup
description: Walk someone through setting up motion-video on their machine, one step at a time, checking each step before moving on. Use when the plugin was just installed, when the session-start check says setup is missing, or when someone says "set me up", "set up motion video", "install the video tools", "help me get started" or "why won't my video render". Also use when /video-doctor reports a failure the person wants fixed.
---

# Setup

Scripts are in `<base dir>/../../scripts` (call it `$MV`).

Assume the person isn't technical. Do the work for them where you can, explain each step
in one plain sentence, and confirm it worked before the next one. Ask before installing
anything.

## Steps

1. **Check the machine.** Run `bash $MV/doctor.sh` and tell them what's missing in
   plain words. Skip any step below that already passes.

2. **System tools** (Node 22+, ffmpeg, Python 3, Git LFS).
   - On a Mac, check for Homebrew with `command -v brew`.
   - If Homebrew is there, offer to run the install for them, listing only what's
     missing: `brew install node ffmpeg git-lfs && git lfs install`. Python 3 comes with
     macOS; if `python3` is missing, add `python` to the brew list.
   - If Homebrew is missing, it needs their Mac password, so they have to run it. Tell
     them to type this into the Claude Code prompt and follow what it asks:

     ```text
     ! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```

     When it finishes, it prints two lines to add Homebrew to the PATH. Run those for
     them, then do the brew install above.
   - On Linux, give the `apt` or `dnf` command and have them run it with `!`, since it
     needs sudo. Never run sudo yourself.

3. **Voice and renderer.** Run `bash $MV/setup.sh`. Tell them it takes a few minutes
   the first time. It installs the voice model into `~/.motion-video/venv` and
   downloads the HyperFrames renderer. If it fails, read the error and fix that one
   thing, then run it again.

4. **HyperFrames skills.** Check that the `hyperframes` skills are loaded in this
   session. If they aren't, have them run `/plugin marketplace add heygen-com/hyperframes`
   and `/plugin install hyperframes@hyperframes`, then restart Claude Code.

5. **Confirm.** Run `bash $MV/doctor.sh` again. Don't move on until every check passes.

6. **Test render.** Offer to make a test video so they see it work:
   `python3 $MV/new_video.py square-loop ~/videos/test-video`, then
   `cd ~/videos/test-video && npx hyperframes render -q draft -f 30 -o renders/test.mp4`,
   then `open renders/test.mp4` on a Mac.

7. **Hand off.** Tell them setup is done and how to start: describe the video they want,
   or run `/new-video`. Mention `/edit-video` for leaving notes on a render.

## When something goes wrong

- **A new tool isn't found right after installing it.** The shell hasn't picked up the
  new PATH. Run `eval "$(/opt/homebrew/bin/brew shellenv)"` first, or ask them to
  restart Claude Code.
- **`git-lfs: command not found` when adding the HyperFrames marketplace.** Install
  Git LFS (step 2), run `git lfs install`, then add the marketplace again.
- **The voice environment fails on a long path.** `MOTION_VIDEO_HOME` must be short.
  Unset it to use the default `~/.motion-video`.
- **They want to stop being asked about setup.** Run `touch ~/.motion-video/skip-setup`.
