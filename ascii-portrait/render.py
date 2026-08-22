"""
render.py -- character grid -> animated frames.

The loop is built so that both ends of the timeline land on an empty dark
terminal, which is what makes it wrap without a visible seam. Every random
choice is drawn from a precomputed stack indexed by ``frame % N``, so the noise
field is periodic for free.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Timeline, in fractions of one loop. Both ends land on darkness.
PHASES = {
    "scan": (0.00, 0.16),
    "resolve": (0.16, 0.44),
    "hold": (0.44, 0.66),
    "glitch": (0.66, 0.72),
    "dissolve": (0.73, 0.90),
    "fade": (0.90, 1.00),
}

REVEAL = [(0.00, 0.0), (0.16, 0.0), (0.44, 1.0), (0.73, 1.0), (0.90, 0.0), (1.00, 0.0)]
DENSITY = [(0.00, 0.08), (0.14, 0.68), (0.66, 0.68), (0.86, 0.68), (1.00, 0.08)]
FIELD = [(0.00, 0.0), (0.07, 1.0), (0.93, 1.0), (1.00, 0.0)]


@dataclass
class RenderConfig:
    frames: int = 96
    fps: int = 16
    cell_w: int = 5
    cell_h: int = 9
    font_path: str = "C:/Windows/Fonts/consola.ttf"
    font_scale: float = 1.06
    # Colour stops: (position, R, G, B). Cool desaturated cyan-grey.
    stops: tuple = (
        (0.00, 5, 7, 9),
        (0.35, 46, 74, 82),
        (0.70, 140, 186, 196),
        (1.00, 228, 246, 250),
    )
    bloom: float = 0.38
    scanline: float = 0.13
    scanline_period: int = 3
    vignette: float = 0.55
    grain: float = 0.012
    grain_static: bool = True      # same grain each frame; per-frame grain wrecks
                                   # temporal compression (48MB vs 3MB on GIF)
    glitch_amount: float = 0.45
    shimmer: float = 0.05
    front_width: float = 0.13
    noise_hold: int = 2
    edge_threshold: float = 0.42
    edge_compensate: bool = True   # keep perceived tone when swapping in a stroke
    seed: int = 20260823


def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def curve(t: float, points) -> float:
    """Smoothstep interpolation through keyframes."""
    for i in range(len(points) - 1):
        t0, v0 = points[i]
        t1, v1 = points[i + 1]
        if t0 <= t <= t1:
            if t1 - t0 < 1e-9:
                return float(v1)
            return float(v0 + (v1 - v0) * _smooth((t - t0) / (t1 - t0)))
    return float(points[-1][1])


def build_atlas(chars: str, cfg: RenderConfig) -> np.ndarray:
    """Pre-render every glyph into a cell-sized tile once.

    Blitting from this atlas is what keeps the render fast: a whole frame
    becomes one fancy-index plus a reshape instead of thousands of draw calls.
    """
    size = max(6, int(round(cfg.cell_h * cfg.font_scale)))
    font = ImageFont.truetype(cfg.font_path, size)
    tiles = np.zeros((len(chars), cfg.cell_h, cfg.cell_w), np.float32)
    pad = 8
    for i, ch in enumerate(chars):
        big = Image.new("L", (cfg.cell_w + 2 * pad, cfg.cell_h + 2 * pad), 0)
        d = ImageDraw.Draw(big)
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = pad + (cfg.cell_w - w) / 2.0 - bbox[0]
        y = pad + (cfg.cell_h - h) / 2.0 - bbox[1]
        d.text((x, y), ch, fill=255, font=font)
        arr = np.asarray(big, np.float32)[pad:pad + cfg.cell_h, pad:pad + cfg.cell_w]
        tiles[i] = arr / 255.0
    return tiles


def build_settle(grid: dict, cfg: RenderConfig) -> np.ndarray:
    """When each cell locks onto its final glyph, in [0, 1].

    Weighted so the face resolves before the shoulders: distance from the
    subject centre dominates, with enough random jitter that it never reads as
    an expanding circle, plus a nudge for high-detail cells.
    """
    rows, cols = grid["rows"], grid["cols"]
    rng = np.random.default_rng(cfg.seed)
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float32)
    cx, cy = 0.50, 0.42
    dx = xx / max(cols - 1, 1) - cx
    dy = yy / max(rows - 1, 1) - cy
    dist = np.sqrt((dx / 0.62) ** 2 + (dy / 0.72) ** 2)
    dist /= max(float(dist.max()), 1e-6)

    detail = np.clip(grid["mag"] * 0.6 + grid["luma"] * 0.4, 0.0, 1.0)
    jitter = rng.random((rows, cols)).astype(np.float32)
    s = 0.54 * dist + 0.31 * jitter + 0.15 * (1.0 - detail)
    s -= s.min()
    s /= max(float(s.max()), 1e-6)
    s *= 0.92

    # Caption text lands after the face has formed, left to right.
    tm = grid.get("_text_mask")
    if tm is not None:
        sweep = np.linspace(0.0, 1.0, cols, dtype=np.float32)[None, :]
        late = 0.62 + 0.28 * sweep + 0.04 * jitter
        s = np.where(tm > 0.3, late, s)
    return s.astype(np.float32)


def build_noise_stack(grid: dict, n_glyphs: int, cfg: RenderConfig):
    """Random glyph indices and lifetimes, periodic over the loop."""
    rows, cols = grid["rows"], grid["cols"]
    rng = np.random.default_rng(cfg.seed + 1)
    steps = max(1, cfg.frames // max(cfg.noise_hold, 1))
    # Bias noise toward the sparser glyphs: a screen full of '@' reads as mud.
    weights = np.linspace(1.0, 0.25, n_glyphs) ** 1.4
    weights /= weights.sum()
    idx = rng.choice(n_glyphs, size=(steps, rows, cols), p=weights).astype(np.int32)
    life = rng.random((steps, rows, cols)).astype(np.float32)
    return idx, life


def _ramp_lut(cfg: RenderConfig) -> np.ndarray:
    """256-entry RGB lookup built from the colour stops."""
    stops = sorted(cfg.stops, key=lambda s: s[0])
    xs = np.array([s[0] for s in stops], np.float32) * 255.0
    lut = np.zeros((256, 3), np.float32)
    for c in range(3):
        lut[:, c] = np.interp(np.arange(256), xs, [s[c + 1] for s in stops])
    return lut


def _glitch(rgb: np.ndarray, amt: float, rng) -> np.ndarray:
    """A few displaced row-bands and at most one pixel of chromatic split.

    Restraint is the whole point. Rolling the red and blue channels by two
    pixels each on a cyan-tinted image throws orange and blue fringes across
    the face -- unmistakably the cheap-hacker look. One pixel, applied only
    near the peak of the burst, reads as a signal fault instead.
    """
    if amt <= 0.001:
        return rgb
    h, w = rgb.shape[:2]
    out = rgb.copy()
    for _ in range(int(1 + 2 * amt)):
        bh = int(rng.integers(2, max(3, int(h * 0.028))))
        y = int(rng.integers(0, max(1, h - bh)))
        span = max(2, int(w * 0.012 * amt) + 2)
        out[y:y + bh] = np.roll(out[y:y + bh], int(rng.integers(-span, span)), axis=1)
    if amt > 0.62:
        out[..., 0] = np.roll(out[..., 0], -1, axis=1)
        out[..., 2] = np.roll(out[..., 2], 1, axis=1)
    return out


def blit(atlas: np.ndarray, idx: np.ndarray, inten: np.ndarray) -> np.ndarray:
    """Character grid -> intensity image, in one vectorised step.

    ``atlas[idx]`` gives (rows, cols, cell_h, cell_w); the transpose interleaves
    cell rows with pixel rows so the reshape lands every glyph in place. This is
    why a frame costs one fancy-index instead of thousands of draw calls.
    """
    tiles = atlas[idx] * inten[:, :, None, None]
    rows, cols, chh, cw = tiles.shape
    return tiles.transpose(0, 2, 1, 3).reshape(rows * chh, cols * cw)


class Compositor:
    """Pixel-side pipeline shared by the portrait and the boot log.

    bloom -> colour ramp -> scanlines -> vignette -> glitch -> grain. Both
    stages run through this so the CRT treatment is identical and the handoff
    between them is invisible.
    """

    def __init__(self, cfg: RenderConfig, H: int, W: int):
        self.cfg, self.H, self.W = cfg, H, W
        self.lut = _ramp_lut(cfg)
        yy = np.arange(H, dtype=np.float32)
        self.scan = (
            1.0 - cfg.scanline * 0.5
            * (1.0 + np.cos(2.0 * np.pi * yy / max(cfg.scanline_period, 1)))
        ).astype(np.float32)[:, None, None]
        yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
        vx = (xv / max(W - 1, 1) - 0.5) / 0.72
        vy = (yv / max(H - 1, 1) - 0.46) / 0.76
        self.vig = np.clip(
            1.0 - cfg.vignette * np.clip(np.sqrt(vx * vx + vy * vy) - 0.52, 0, 2) ** 1.4,
            0, 1,
        ).astype(np.float32)[..., None]

    def __call__(self, img: np.ndarray, glitch_amt: float = 0.0, fseed: int = 0):
        cfg = self.cfg
        if cfg.bloom > 0:
            img = img + cfg.bloom * cv2.GaussianBlur(img, (0, 0), cfg.cell_h * 0.85)
        img = np.clip(img, 0.0, 1.0)
        rgb = self.lut[(img * 255).astype(np.uint8)] * self.scan * self.vig
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        if glitch_amt > 0.02:
            rgb = _glitch(rgb, glitch_amt, np.random.default_rng(cfg.seed + 100 + fseed))
        if cfg.grain > 0:
            gseed = cfg.seed + 500 + (0 if cfg.grain_static else fseed)
            g = np.random.default_rng(gseed).normal(0, cfg.grain * 255, (self.H, self.W, 1))
            rgb = np.clip(rgb.astype(np.float32) + g, 0, 255).astype(np.uint8)
        return rgb


def resolve_target(grid: dict, ramp: str, cfg: RenderConfig, atlas=None):
    """Final glyph per cell, plus a per-cell brightness correction.

    Swapping a tone glyph for a directional stroke changes how much ink the
    cell carries -- '/' covers 3.2% of its box where '@' covers 10.4%. Left
    uncorrected the strokes punch dark holes through exactly the features they
    were meant to sharpen, so the compensation scales intensity by the ratio of
    real ink coverage.
    """
    n = len(ramp)
    target = grid["index"].copy()
    edge_idx = np.array(
        [ramp.index(c) if c in ramp else n - 1 for c in grid["edge_chars"]], np.int32
    )
    strong = grid["mag"] > cfg.edge_threshold
    picked = edge_idx[grid["edge_bucket"]]
    out = np.where(strong, picked, target).astype(np.int32)

    comp = np.ones(target.shape, np.float32)
    if cfg.edge_compensate and atlas is not None and strong.any():
        cov = np.maximum(atlas.mean(axis=(1, 2)), 1e-4)
        ratio = np.clip(cov[target] / cov[picked], 0.45, 2.8).astype(np.float32)
        comp = np.where(strong, ratio, 1.0).astype(np.float32)
    return out, comp


def render_frames(grid: dict, ramp: str, cfg: RenderConfig, still: bool = False):
    """Produce the loop as a list of RGB uint8 arrays.

    ``still=True`` renders a single fully-resolved frame, which is what the
    tuning pass uses to judge legibility without waiting for 96 frames.
    """
    rows, cols = grid["rows"], grid["cols"]
    atlas = build_atlas(ramp, cfg)
    n_glyphs = len(ramp)

    target, comp = resolve_target(grid, ramp, cfg, atlas)
    base_int = 0.30 + 0.70 * grid["luma"]
    base_int = np.clip(base_int * comp * (1.0 + 0.18 * grid["mag"]), 0.0, 2.2).astype(np.float32)

    settle = build_settle(grid, cfg)
    noise_idx, noise_life = build_noise_stack(grid, n_glyphs, cfg)
    lut = _ramp_lut(cfg)

    H, W = rows * cfg.cell_h, cols * cfg.cell_w
    comp = Compositor(cfg, H, W)
    row_norm = (np.arange(rows, dtype=np.float32) / max(rows - 1, 1))[:, None]
    gs, ge = PHASES["glitch"]

    def compose(idx, inten, glitch_amt, fseed):
        return comp(blit(atlas, idx, inten), glitch_amt, fseed)

    if still:
        return [compose(target, base_int, 0.0, 0)]

    frames = []
    for f in range(cfg.frames):
        t = f / cfg.frames
        reveal = curve(t, REVEAL)
        density = curve(t, DENSITY)
        field = curve(t, FIELD)

        step = (f // max(cfg.noise_hold, 1)) % noise_idx.shape[0]
        nidx, nlife = noise_idx[step], noise_life[step]

        settled = settle < reveal
        alive = nlife < density

        # Scan-in: characters only exist above the sweeping cursor line.
        s0, s1 = PHASES["scan"]
        band = np.zeros((rows, 1), np.float32)
        if t < s1:
            head = np.clip((t - s0) / max(s1 - s0, 1e-6), 0.0, 1.0)
            alive = alive & (row_norm <= head)
            band = np.clip(1.0 - np.abs(row_norm - head) / 0.05, 0.0, 1.0) * 1.6

        idx = np.where(settled, target, nidx)
        show = settled | alive

        inten = np.where(settled, base_int, 0.34 + 0.30 * nlife).astype(np.float32)
        if 0.0 < reveal < 1.0:
            age = (reveal - settle) / max(cfg.front_width, 1e-6)
            inten = inten + np.where(settled, np.clip(1.0 - age, 0.0, 1.0) * 0.85, 0.0)
        if cfg.shimmer > 0 and reveal >= 1.0:
            flick = (nlife < cfg.shimmer) & settled
            inten = np.where(flick, inten * 1.55, inten)
        inten = (inten + band) * show.astype(np.float32) * field

        gl = 0.0
        if gs <= t < ge:
            u = (t - gs) / max(ge - gs, 1e-6)
            gl = float(np.sin(np.pi * u) ** 1.5) * cfg.glitch_amount
        frames.append(compose(idx, inten.astype(np.float32), gl, f))
    return frames


# --- boot-prologue variant ------------------------------------------------
# A longer loop: terminal log types out, hands over to the character field,
# the portrait resolves, holds, glitches, dissolves. Both ends are black, so
# it still wraps seamlessly.
BOOT_PHASES = {
    "black": (0.00, 0.03),
    "type": (0.03, 0.38),
    "ready": (0.38, 0.45),
    "handoff": (0.45, 0.52),
    "resolve": (0.52, 0.72),
    "hold": (0.72, 0.86),
    "glitch": (0.86, 0.91),
    "dissolve": (0.91, 0.975),
    "fade": (0.975, 1.00),
}
BOOT_ALPHA = [(0.00, 0.0), (0.05, 1.0), (0.45, 1.0), (0.52, 0.0), (1.00, 0.0)]
BOOT_REVEAL = [(0.00, 0.0), (0.52, 0.0), (0.72, 1.0), (0.91, 1.0), (0.975, 0.0), (1.00, 0.0)]
BOOT_DENSITY = [(0.00, 0.05), (0.50, 0.72), (0.90, 0.72), (0.99, 0.08), (1.00, 0.05)]
BOOT_FIELD = [(0.00, 0.0), (0.45, 0.0), (0.53, 1.0), (0.965, 1.0), (1.00, 0.0)]

CURSOR_FRAMES = 8       # blink period; keep cfg.frames a multiple of this


def cell_state(f, reveal, density, field, target, base_int, settle,
               noise_idx, noise_life, cfg):
    """Glyph index and intensity per cell for one frame."""
    step = (f // max(cfg.noise_hold, 1)) % noise_idx.shape[0]
    nidx, nlife = noise_idx[step], noise_life[step]

    settled = settle < reveal
    alive = nlife < density
    idx = np.where(settled, target, nidx)

    inten = np.where(settled, base_int, 0.34 + 0.30 * nlife).astype(np.float32)
    if 0.0 < reveal < 1.0:                       # bright wavefront on new cells
        age = (reveal - settle) / max(cfg.front_width, 1e-6)
        inten = inten + np.where(settled, np.clip(1.0 - age, 0.0, 1.0) * 0.85, 0.0)
    if cfg.shimmer > 0 and reveal >= 1.0:
        inten = np.where((nlife < cfg.shimmer) & settled, inten * 1.55, inten)
    return idx, inten, (settled | alive), field


def render_boot_loop(grid: dict, ramp: str, cfg: RenderConfig, boot_draw=None):
    """Boot log, handoff, portrait, glitch, dissolve -- one seamless loop.

    ``boot_draw(width, height, progress, blink)`` returns a float32 intensity
    buffer for the terminal layer. Passing it in rather than importing the
    terminal module keeps this file free of any dependency on it.
    """
    rows, cols = grid["rows"], grid["cols"]
    atlas = build_atlas(ramp, cfg)
    target, comp_ratio = resolve_target(grid, ramp, cfg, atlas)
    base_int = 0.30 + 0.70 * grid["luma"]
    base_int = np.clip(
        base_int * comp_ratio * (1.0 + 0.18 * grid["mag"]), 0.0, 2.2
    ).astype(np.float32)

    settle = build_settle(grid, cfg)
    noise_idx, noise_life = build_noise_stack(grid, len(ramp), cfg)

    H, W = rows * cfg.cell_h, cols * cfg.cell_w
    comp = Compositor(cfg, H, W)
    t0, t1 = BOOT_PHASES["type"]
    gs, ge = BOOT_PHASES["glitch"]

    frames = []
    for f in range(cfg.frames):
        t = f / cfg.frames
        idx, inten, show, field = cell_state(
            f, curve(t, BOOT_REVEAL), curve(t, BOOT_DENSITY), curve(t, BOOT_FIELD),
            target, base_int, settle, noise_idx, noise_life, cfg,
        )
        img = blit(atlas, idx, (inten * show.astype(np.float32) * field).astype(np.float32))

        alpha = curve(t, BOOT_ALPHA)
        if alpha > 0.002 and boot_draw is not None:
            p = float(np.clip((t - t0) / max(t1 - t0, 1e-6), 0.0, 1.0))
            blink = (f % CURSOR_FRAMES) / float(CURSOR_FRAMES)
            img = np.maximum(img, boot_draw(W, H, p, blink) * alpha)

        gl = 0.0
        if gs <= t < ge:
            u = (t - gs) / max(ge - gs, 1e-6)
            gl = float(np.sin(np.pi * u) ** 1.5) * cfg.glitch_amount
        frames.append(comp(img, gl, f))
    return frames
