"""
terminal.py -- the boot-log prologue that runs before the portrait resolves.

The boot text is drawn as *real* terminal text at a readable size, not as
characters-made-of-characters. At the cell sizes the portrait needs (5x9px) one
glyph per cell would put a 40-column log inside 200 pixels -- illegible. Drawing
it directly onto the frame buffer keeps it crisp, and the visual shift from
"terminal" to "portrait built from glyphs" is what sells the transition.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BLOCK = "\u2588"

# Per-line size multipliers, keyed by the line's kind. One font size for
# every line gives a flat block with no hierarchy; the name has to out-weigh
# the status lines beneath it.
SCALES = {"title": 2.05, "sub": 1.15, "norm": 1.0,
          "dim": 1.0, "ok": 1.0, "bar": 1.0}

# (text, kind). kind drives colour weight: 'dim' prompt, 'norm', 'ok', 'bar'.
DEFAULT_SCRIPT = [
    ("> booting hemant.dev", "norm"),
    ("", "norm"),
    ("> loading ai systems", "dim"),
    ("> loading rag pipeline", "dim"),
    ("> loading backend", "dim"),
    ("> loading cloud", "dim"),
    ("", "norm"),
    ("__BAR__", "bar"),
    ("", "norm"),
    ("> system ready", "ok"),
]


@dataclass
class BootConfig:
    script: list = field(default_factory=lambda: list(DEFAULT_SCRIPT))
    font_path: str = "C:/Windows/Fonts/consola.ttf"
    font_frac: float = 0.042        # glyph size as a fraction of frame height
    line_frac: float = 1.62         # line height as a multiple of font size
    bar_cells: int = 24
    left_frac: float = 0.5          # 0.5 centres the text block
    cursor_period: float = 0.12     # blink period in loop-time
    y_frac: float = 0.5             # vertical centre of the block, 0..1
    dim: float = 0.42
    norm: float = 0.80
    ok: float = 1.0
    title: float = 1.0
    sub: float = 0.66


def _fit(cfg: BootConfig, W: int, H: int):
    size = max(9, int(round(H * cfg.font_frac)))
    font = ImageFont.truetype(cfg.font_path, size)
    adv = font.getlength("M")
    widest = 0
    for text, kind in cfg.script:
        n = cfg.bar_cells + 6 if kind == "bar" else len(text)
        widest = max(widest, n)
    # Shrink until the widest line fits with a margin.
    while widest * adv > W * 0.86 and size > 8:
        size -= 1
        font = ImageFont.truetype(cfg.font_path, size)
        adv = font.getlength("M")
    return font, size, adv


def plan(cfg: BootConfig, W: int, H: int, x0: int = 0, width: int | None = None):
    """Expand the script into per-character reveal fractions in [0, 1].

    ``x0``/``width`` confine the block to a horizontal band, which is what lets
    the wide banner put the boot log on the left and the system info on the
    right instead of centring both on top of the portrait.
    """
    band = W if width is None else width
    base = max(9, int(round(H * cfg.font_frac)))
    lines = []
    total_chars = 0
    for text, kind in cfg.script:
        n = cfg.bar_cells if kind == "bar" else len(text)
        size = max(8, int(round(base * SCALES.get(kind, 1.0))))
        f = ImageFont.truetype(cfg.font_path, size)
        # Shrink this line alone until it fits the band.
        while text and f.getlength(text) > band * 0.94 and size > 8:
            size -= 1
            f = ImageFont.truetype(cfg.font_path, size)
        lines.append({"text": text, "kind": kind, "n": n, "font": f, "size": size,
                      "adv": f.getlength("M")})
        total_chars += max(n, 0)
    total_chars = max(total_chars, 1)
    font = lines[0]["font"]
    size = lines[0]["size"]
    adv = lines[0]["adv"]

    # A blank line still costs a beat, so the pauses read as pauses.
    beat = 1.0 / (total_chars + 2 * len(lines))
    cursor = 0.0
    for ln in lines:
        ln["start"] = cursor
        cursor += ln["n"] * beat
        ln["end"] = cursor
        cursor += 2 * beat
    span = max(cursor, 1e-6)
    for ln in lines:
        ln["start"] /= span
        ln["end"] /= span

    # Each line reserves height proportional to its own size, so a large title
    # does not collide with the small lines under it.
    for ln in lines:
        ln["h"] = ln["size"] * cfg.line_frac
    block_h = sum(ln["h"] for ln in lines)
    y0 = H * cfg.y_frac - block_h / 2.0
    widest_px = max(
        (cfg.bar_cells + 6) * ln["adv"] if ln["kind"] == "bar" else ln["font"].getlength(ln["text"])
        for ln in lines
    )
    origin = x0 + (band - widest_px) * cfg.left_frac

    return {"font": font, "size": size, "adv": adv, "lines": lines,
            "line_h": lines[0]["h"], "x0": origin, "y0": y0}


def draw(layout: dict, cfg: BootConfig, W: int, H: int, p: float,
         blink: float) -> np.ndarray:
    """Render the boot log at typing progress ``p`` in [0, 1].

    Returns a float32 intensity buffer, same convention as the character grid,
    so both go through one colour ramp and one set of CRT effects.
    """
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    font = layout["font"]
    weights = {"dim": cfg.dim, "norm": cfg.norm, "ok": cfg.ok, "bar": cfg.norm,
               "title": cfg.title, "sub": cfg.sub}

    head_xy = None
    y = layout["y0"]
    for ln in layout["lines"]:
        font = ln["font"]
        adv = ln["adv"]
        if p < ln["start"]:
            break
        frac = 1.0 if p >= ln["end"] else (
            (p - ln["start"]) / max(ln["end"] - ln["start"], 1e-6)
        )
        w = weights.get(ln["kind"], cfg.norm)

        if ln["kind"] == "bar":
            filled = int(round(cfg.bar_cells * frac))
            d.text((layout["x0"], y), BLOCK * filled, fill=int(255 * 0.92), font=font)
            pct = f" {int(round(frac * 100)):3d}%"
            d.text((layout["x0"] + cfg.bar_cells * adv, y), pct,
                   fill=int(255 * 0.72), font=font)
            head_xy = (layout["x0"] + filled * adv, y, ln["size"])
        else:
            shown = ln["text"][: int(round(len(ln["text"]) * frac))]
            if shown:
                d.text((layout["x0"], y), shown, fill=int(255 * w), font=font)
            head_xy = (layout["x0"] + len(shown) * adv, y, ln["size"])
        y += ln["h"]

    # Block cursor at the typing head.
    if head_xy is not None and blink < 0.55:
        hx, hy, hs = head_xy
        d.rectangle([hx, hy + hs * 0.12, hx + hs * 0.5 * 0.82, hy + hs * 0.98],
                    fill=int(255 * 0.85))

    return np.asarray(img, np.float32) / 255.0
