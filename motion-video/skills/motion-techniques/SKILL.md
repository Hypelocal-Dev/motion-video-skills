---
name: motion-techniques
description: Motion design patterns that make product-UI videos feel continuous and premium, written for HyperFrames and GSAP. Use when planning or building the animation of a motion video, choosing transitions, making a video loop cleanly, or when a draft feels like a slideshow.
---

# Motion techniques

These patterns come from building product videos and from studying the
[Prompt Motion](https://prompt-motion.com) library. Prompt Motion is a curated collection of
motion videos made with Claude, with the prompts behind them. The prompts belong to
their creators, so this skill describes the techniques in its own words and links to the
originals in [references/prompt-motion.md](references/prompt-motion.md).

## Use these

### One world, one camera

Lay every scene out as a panel on one large canvas (`#world`) and move a camera between
them (`gsap.to("#world", { x, y })`). Nothing hard-cuts, and related UI can sit next to
each other: the phone that books, then the dashboard that sees it. With the camera at a
panel and scale 1, panel coordinates equal screen coordinates, which keeps cursor and
tap targets simple.

### A persistent element that resolves

Give the video one element that stays on screen and changes as the story moves. Examples:
a three-item checklist that checks off, or an inbox of complaints that empties as each
one gets solved. It turns a feature tour into one story, and muted viewers can follow it.
Keep it outside the world so the camera doesn't move it.

### Proof that travels

When a scene proves a point, send something from the proof to the persistent element. A
check that flies from the Submit button into "Registered" works. So does an email chip
that turns green and leaves the inbox. Fly with x and y on different eases
(`power2.inOut` and `power3.in`) for an arc.

### A loop that doesn't jump

For autoplaying loops, end on a fade to a copy of the opening background (`#veil`), and
start the video on that same empty background. Hold the end frame first, so people can
read it. Then check the seam with `loop_check.py`.

### Real input, small overshoot

Every change comes from a visible click, tap or drag. Use springy eases with at most a
small overshoot (`back.out(1.2–1.8)` for pops). Avoid bounce. Admin and business audiences
read bounce as cheap.

### Kinetic headlines

Bring headlines in word by word (`y: 40` to `0`, about 0.06s stagger) and take them out
quickly before the next scene. A headline can also start big in the middle of the frame
and then move up to the headline slot when the UI arrives.

### Counts and tags that update

Numbers ticking (Paid 142 to 147), tags flipping (Pending to Paid) and capacity bars
filling read as "real time" without any explanation.

### Motion blur (experimental)

Some library entries render several subframes per frame and blend them with ffmpeg
`tmix` for motion blur on camera moves. HyperFrames doesn't do this natively. Test it on
one scene before using it everywhere.

## Avoid these

- Particle bursts, heavy glows and 3D flips in product-UI videos. They pull attention off
  the product. Confetti on a CTA click is the exception, and only when there's a CTA to click.
- Animating a CTA button when a real one sits next to the video on the page.
- Exit animations that empty a scene before its transition. The transition is the exit.
- Copying a library prompt word for word into a project. Borrow the technique and credit it.
