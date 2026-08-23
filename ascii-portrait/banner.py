"""
banner.py -- the wide horizontal composition.

A square portrait dropped into a 3:1 canvas leaves black bars, so the artwork is
recomposed for the shape instead: one continuous character field spanning the
full width, with the portrait occupying the middle third and the outer thirds
carrying a code-rain field plus terminal text.

The device that makes it read as one image rather than three panels is the
falloff in :func:`side_weight` -- the ambient field does not stop at the
portrait's edge, it fades into it. There is no boundary to see.

Everything here works on the character grid, so the sides are made of the same
glyphs as the face and share the same colour ramp and CRT treatment.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class BannerConfig:
    total_cols: int = 360           # 360 * 5px = 1800px
    portrait_cols: int = 132        # 132 * 5px = 660px = 36.7% of the width
    portrait_x: int = 200           # left edge in cells; 342..360 stays as margin
    text_x: int = 36                # 180px in = 10% left margin
    text_cols: int = 140            # text band ends at col 176, 34 cols clear of
                                    # the portrait so the two never touch
    rain_density: float = 0.52      # fraction of columns carrying a stream
    rain_tail: int = 16             # trail length in cells
    rain_speed: tuple = (0.30, 1.05)# cells per frame, per-column range
    rain_bright: float = 0.60       # peak intensity of a stream head
    ambient_floor: float = 0.10     # dim static field so gaps never read as empty
    transition_cols: int = 26       # how quickly the rain reaches full strength
    rain_hold: int = 4              # frames a rain position persists. Every cell
                                    # moving on every frame is what turns a
                                    # full-width animation into a 10MB GIF.
    seed: int = 20260823


def side_weight(rows: int, cols: int, cfg: BannerConfig) -> np.ndarray:
    """1.0 away from the portrait, ~0 across it, smooth in between.

    Keyed off the portrait's actual span rather than the canvas centre, so the
    falloff follows the portrait wherever it is placed. Without it the ambient
    field would butt up against the portrait's edge and the composition would
    read as two unrelated blocks.
    """
    x = np.arange(cols, dtype=np.float32)
    px0 = float(cfg.portrait_x)
    px1 = float(cfg.portrait_x + cfg.portrait_cols)
    outside = np.maximum(px0 - x, x - px1)          # >0 only beyond the portrait
    d = outside / float(max(cfg.transition_cols, 1))
    w = np.clip(d, 0.0, 1.0)
    w = w * w * (3.0 - 2.0 * w)                     # smoothstep
    return np.repeat(w[None, :], rows, axis=0).astype(np.float32)


class CodeRain:
    """Downward-drifting columns of characters, deliberately dim.

    Kept monochrome and low-contrast: bright green streams would turn a
    developer banner into a film prop.
    """

    def __init__(self, rows: int, cols: int, n_glyphs: int, cfg: BannerConfig):
        rng = np.random.default_rng(cfg.seed)
        self.rows, self.cols, self.cfg = rows, cols, cfg
        self.active = rng.random(cols) < cfg.rain_density
        self.speed = rng.uniform(*cfg.rain_speed, size=cols).astype(np.float32)
        self.offset = rng.uniform(0, rows + cfg.rain_tail, size=cols).astype(np.float32)
        # A per-cell glyph field that changes slowly, so streams look like text
        # rather than static.
        self.glyphs = rng.integers(0, n_glyphs, size=(rows + cfg.rain_tail * 2, cols))
        self.row_idx = np.arange(rows, dtype=np.float32)[:, None]
        # Sparse, unmoving, very dim: texture rather than motion.
        alive = rng.random((rows, cols)) < 0.34
        self.floor = (alive * rng.uniform(0.45, 1.0, size=(rows, cols))
                      * cfg.ambient_floor).astype(np.float32)

    def frame(self, f: int) -> tuple[np.ndarray, np.ndarray]:
        """Glyph indices and intensity for frame ``f``."""
        cfg = self.cfg
        step = f // max(cfg.rain_hold, 1)
        head = (self.offset + step * self.speed * cfg.rain_hold) % (self.rows + cfg.rain_tail)
        dist = head[None, :] - self.row_idx                  # >0 above the head
        inside = (dist >= 0) & (dist < cfg.rain_tail)
        decay = np.clip(1.0 - dist / cfg.rain_tail, 0.0, 1.0) ** 1.6
        inten = np.where(inside & self.active[None, :], decay * cfg.rain_bright, 0.0)
        # Head cell slightly brighter, which is what makes it read as motion.
        inten = np.where(inside & (dist < 1.0) & self.active[None, :],
                         cfg.rain_bright * 1.5, inten)
        # A static dim floor under the streams. Without it the gaps between
        # streams are pure black and the side reads as unused canvas.
        inten = np.maximum(inten, self.floor)
        shift = int(step * 0.5) % cfg.rain_tail
        glyphs = self.glyphs[shift:shift + self.rows]
        return glyphs.astype(np.int32), inten.astype(np.float32)


def compose(portrait: dict, cfg: BannerConfig) -> dict:
    """Centre the portrait grid inside a wide grid, leaving the sides empty.

    The sides are filled at render time by the rain and text layers, not here,
    so they can animate independently of the portrait.
    """
    rows = portrait["rows"]
    cols = cfg.total_cols
    x0 = cfg.portrait_x

    out = dict(portrait)
    out["cols"] = cols
    out["portrait_x0"] = x0
    out["portrait_x1"] = x0 + portrait["cols"]
    # Outside these columns there is no portrait at all. Without an explicit
    # mask the renderer's brightness floor (0.30 + 0.70*luma) gives empty side
    # cells a phantom 0.30 intensity carrying a space glyph -- invisible, but
    # bright enough to beat the code rain and suppress it entirely.
    occupied = np.zeros((rows, cols), np.float32)
    occupied[:, x0:x0 + portrait["cols"]] = 1.0
    out["occupied"] = occupied
    for key, fill in (("luma", 0.0), ("mag", 0.0), ("matte", 0.0),
                      ("index", 0), ("edge_bucket", 0)):
        src = portrait[key]
        wide = np.full((rows, cols), fill, dtype=src.dtype)
        wide[:, x0:x0 + portrait["cols"]] = src
        out[key] = wide
    return out


def text_knockout(rows: int, cols: int, cell, layout, n_lines: int,
                  pad_cells: int = 3) -> np.ndarray:
    """0 inside a text block's bounding box, 1 outside, with a soft edge.

    Streams running through the system-info block make it hard to read, so the
    rain is held back where text lives rather than drawn over and then covered.
    """
    cw, ch = cell
    x0 = max(0, int(layout["x0"] / cw) - pad_cells)
    x1 = min(cols, int((layout["x0"] + layout["adv"] * 30) / cw) + pad_cells)
    y0 = max(0, int(layout["y0"] / ch) - pad_cells)
    y1 = min(rows, int((layout["y0"] + layout["line_h"] * n_lines) / ch) + pad_cells)

    m = np.ones((rows, cols), np.float32)
    m[y0:y1, x0:x1] = 0.0
    # Feather so the hole does not read as a rectangle.
    for i in range(pad_cells):
        f = (i + 1) / (pad_cells + 1)
        if y0 - 1 - i >= 0:
            m[y0 - 1 - i, x0:x1] = np.minimum(m[y0 - 1 - i, x0:x1], f)
        if y1 + i < rows:
            m[y1 + i, x0:x1] = np.minimum(m[y1 + i, x0:x1], f)
        if x0 - 1 - i >= 0:
            m[y0:y1, x0 - 1 - i] = np.minimum(m[y0:y1, x0 - 1 - i], f)
        if x1 + i < cols:
            m[y0:y1, x1 + i] = np.minimum(m[y0:y1, x1 + i], f)
    return m


# --- side text -----------------------------------------------------------

BOOT_LINES = [
    "> booting hemant.dev",
    "",
    "> loading ai systems",
    "> loading rag pipeline",
    "> loading backend",
    "> loading cloud",
    "",
    "__BAR__",
    "",
    "> system ready",
]

# The state the banner settles into once the boot log has finished. Ordered by
# weight: name, then identity, then supporting detail.
IDENT_LINES = [
    ("HEMANT KUSHWAHA", "title"),
    ("AI & Backend Engineer", "sub"),
    ("", "norm"),
    ("STACK   python · fastapi · kotlin", "dim"),
    ("FOCUS   retrieval-augmented systems", "dim"),
    ("STATUS  open to roles", "norm"),
]
