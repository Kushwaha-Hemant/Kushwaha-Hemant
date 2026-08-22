# ascii-portrait

Turns a photograph into a looping portrait built entirely from terminal
characters — the image assembles itself out of a stream of code glyphs, holds,
glitches, dissolves, and wraps seamlessly.

Written for one photo and one profile, but every knob is a parameter.

```
python generate.py --image me.png --preview     # stills only, ~1s
python generate.py --image me.png               # full build, all presets
```

---

## What comes out

| Preset  | Size       | Length | Files |
|---------|------------|--------|-------|
| `square` | 600 × 600  | 5.12 s | `.webp` 1.65 MB · `.gif` 2.72 MB · `.mp4` 1.06 MB |
| `wide`   | 1200 × 560 | 5.12 s | `.webp` 2.49 MB · `.mp4` 1.61 MB |
| `small`  | 320 × 320  | 5.00 s | `.gif` 659 KB · `.webp` 382 KB |

**Use the WebP.** It is roughly 40% the size of the equivalent GIF, keeps 24-bit
colour instead of a 16-entry palette, and every browser GitHub supports renders
it. The GIF exists for surfaces that still refuse WebP; the MP4 is the archival
copy and the one to upload to LinkedIn or a talk slide.

---

## The pipeline

```
photo ──▶ face detect ──▶ subject matte ──▶ tone map ──▶ character grid ──▶ frames ──▶ encode
         (Haar cascade)   (seeded GrabCut)   (CLAHE)      (measured ramp)   (timeline)
```

**`core.py`** — photo to grid.
**`render.py`** — grid to frames.
**`encode.py`** — frames to GIF / WebP / MP4.
**`generate.py`** — presets, layout, CLI.

### Four decisions that carry the quality

**1. The ramp is measured, not guessed.** Every glyph is rendered once and its
ink coverage sampled, then the character set is sorted by that number. In
Consolas the honest order is:

```
' ' 0.00%   '-' 1.07%   '*' 3.02%   '/' 3.21%   ')' 4.16%   '1' 5.02%
'#' 6.94%   '%' 7.43%   '$' 7.63%   '0' 7.93%   '&' 8.43%   '@' 10.37%
```

Guessing this ordering is where most ASCII-art renderers lose their tonal
gradient. `core.measure_ramp()` recomputes it for any font.

**2. The subject is cut out before anything else.** A seeded GrabCut lifts the
head and shoulders off the background. Skip it and CLAHE invents texture out of
a flat studio wall — the portrait ends up buried in static that reads as noise
rather than structure. Seeding matters too: a plain bounding rect that covers
most of the frame gives GrabCut no background to model, and it returns ~74% of
the image as foreground. Explicit FG/BG regions bring that to a clean 49%.

**3. Edge-following strokes are off by default.** The usual trick — override
strong edges with `/ \ | -` oriented along the gradient — actively hurts here.
Those glyphs carry 1–3% ink where the tone glyph they replace carries 8–10%, so
every stroke punches a *dark* hole through exactly the feature it was meant to
sharpen. `edge_compensate` fixes the tone by scaling intensity with the coverage
ratio, and it works; it just turns out that at 120 columns the tone ramp alone
resolves the face better. Set `edge_threshold` below 1.0 to bring them back.

**4. The loop closes because both ends are empty.** The timeline starts and ends
on a dark terminal, and every random draw comes from a precomputed stack indexed
by `frame % N`, so the noise field is periodic for free. Measured seam between
first and last frame: **0.16 / 255**.

### Timeline

| Phase | Fraction | What happens |
|---|---|---|
| scan | 0.00–0.16 | cursor line sweeps down, characters appear above it |
| resolve | 0.16–0.44 | cells lock onto their final glyph, face first |
| hold | 0.44–0.66 | portrait stable, a few cells shimmer |
| glitch | 0.66–0.72 | row-band displacement, 1px chromatic split |
| dissolve | 0.73–0.90 | cells revert to noise, outside in |
| fade | 0.90–1.00 | back to darkness, matching frame 0 |

Cells resolve in an order weighted by distance from the face, with enough random
jitter that it never reads as an expanding circle.

---

## Two traps worth knowing

**Per-frame film grain destroys temporal compression.** Fresh noise on every
pixel of every frame took the square GIF to **48 MB**. The same grain, generated
once and reused for all frames, is still film grain — and the file drops to
10 MB. Dropping dithering and trimming the palette took it to 4 MB. If an
animation is inexplicably huge, look for something reseeding per frame.

**GIF stores delays in centiseconds.** Ask for 13 fps and you want 76.9 ms per
frame; the file gets 70 ms, and the whole loop silently runs 10% fast. Pick an
fps that divides into 100 — 12.5, 10, 20 — or `encode.frame_delay_ms()` will
round for you and the timing will drift.

---

## Tuning

Most of what you'd want to change is in `PRESETS` in `generate.py`.

| Knob | Where | Effect |
|---|---|---|
| `head_room` | preset | crop span as a multiple of face width. Lower = tighter |
| `face_bias` | preset | pushes the crop down; headroom above the hair |
| `cols` | preset | character columns. More detail, bigger files |
| `bg_level` | `SourceConfig` | how much background survives the matte. `0.0` = pure black |
| `clahe_clip` | `SourceConfig` | local contrast. Raise it if clothing goes flat |
| `edge_threshold` | `RenderConfig` | `< 1.0` re-enables directional strokes |
| `glitch_amount` | `RenderConfig` | `0.45` is deliberately restrained |
| `PALETTE` | `generate.py` | colour stops. Currently a cool desaturated cyan-grey |
| `segment=False` | `SourceConfig` | skip GrabCut for an already-cut-out subject |

To retarget the whole thing at a different photo, only `--image` has to change —
the crop follows the detected face. Check `--preview` before a full encode.

## Requirements

```
pip install pillow numpy opencv-python imageio-ffmpeg
```

`imageio-ffmpeg` ships its own ffmpeg binary, so nothing needs to be on `PATH`.
The font path in `RenderConfig.font_path` points at Consolas; on Linux or macOS
point it at any monospace TTF (DejaVu Sans Mono and Menlo both work) and the
ramp will re-measure itself.

---

## Embedding it in a README

The assets are published in this repo, so they already have stable raw URLs:

```
https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/<file>
```

**Full-width hero** — what this profile uses at the top:

```html
<img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-wide.webp"
     width="100%" alt="Hemant Kushwaha — a portrait reconstructed from terminal characters" />
```

**Centred square** — good above a project README, or as a section break:

```html
<div align="center">
  <img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-square.webp"
       width="360" alt="Hemant Kushwaha" />
</div>
```

**Small inline** — cheap enough to sit beside body text:

```markdown
![Hemant Kushwaha](https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-small.webp)
```

**With a GIF fallback**, if you want to cover a client that refuses WebP. Only
one file is ever downloaded:

```html
<picture>
  <source type="image/webp" srcset="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-square.webp" />
  <img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-square.gif"
       width="360" alt="Hemant Kushwaha" />
</picture>
```

### Things worth knowing

- **Set a `width`.** Without one the square renders at its full 600 px, which
  is larger than most READMEs want.
- **GitHub will not play the MP4 inline.** Markdown `<video>` tags are stripped.
  Drag the `.mp4` into an issue or PR comment and GitHub hosts and plays it —
  that is the path for LinkedIn, slides, or anywhere video is preferred.
- **Always keep `alt` text.** It is the only thing a screen reader gets, and the
  portrait carries the identity of the page.
- **Avatars are a separate upload.** GitHub's avatar pipeline re-encodes what
  you give it and animation is not dependable there; the README is the surface
  where this reliably plays. `portrait-small.gif` is the one to try if you want
  to experiment.
- **Regenerating rewrites ~10 MB of binaries.** Git keeps every version
  forever, so avoid committing a fresh render on every tweak — check
  `--preview` output first, then encode once.
