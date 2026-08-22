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
    dim: float = 0.42
    norm: float = 0.80
    ok: float = 1.0


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


def plan(cfg: BootConfig, W: int, H: int):
    """Expand the script into per-character reveal fractions in [0, 1]."""
    font, size, adv = _fit(cfg, W, H)
    lines = []
    total_chars = 0
    for text, kind in cfg.script:
        n = cfg.bar_cells if kind == "bar" else len(text)
        lines.append({"text": text, "kind": kind, "n": n})
        total_chars += max(n, 0)
    total_chars = max(total_chars, 1)

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

    line_h = size * cfg.line_frac
    block_h = line_h * len(lines)
    y0 = (H - block_h) / 2.0
    widest = max(
        (cfg.bar_cells + 6) if l["kind"] == "bar" else len(l["text"]) for l in lines
    )
    x0 = (W - widest * adv) * cfg.left_frac

    return {"font": font, "size": size, "adv": adv, "lines": lines,
            "line_h": line_h, "x0": x0, "y0": y0}


def draw(layout: dict, cfg: BootConfig, W: int, H: int, p: float,
         blink: float) -> np.ndarray:
    """Render the boot log at typing progress ``p`` in [0, 1].

    Returns a float32 intensity buffer, same convention as the character grid,
    so both go through one colour ramp and one set of CRT effects.
    """
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    font = layout["font"]
    weights = {"dim": cfg.dim, "norm": cfg.norm, "ok": cfg.ok, "bar": cfg.norm}

    head_xy = None
    for i, ln in enumerate(layout["lines"]):
        y = layout["y0"] + i * layout["line_h"]
        if p < ln["start"]:
            break
        frac = 1.0 if p >= ln["end"] else (
            (p - ln["start"]) / max(ln["end"] - ln["start"], 1e-6)
        )
        w = weights[ln["kind"]]

        if ln["kind"] == "bar":
            filled = int(round(cfg.bar_cells * frac))
            bar = BLOCK * filled
            d.text((layout["x0"], y), bar, fill=int(255 * 0.92), font=font)
            pct = f" {int(round(frac * 100)):3d}%"
            d.text((layout["x0"] + cfg.bar_cells * layout["adv"], y), pct,
                   fill=int(255 * 0.72), font=font)
            head_xy = (layout["x0"] + filled * layout["adv"], y)
        else:
            shown = ln["text"][: int(round(len(ln["text"]) * frac))]
            if shown:
                d.text((layout["x0"], y), shown, fill=int(255 * w), font=font)
            head_xy = (layout["x0"] + len(shown) * layout["adv"], y)

    # Block cursor at the typing head.
    if head_xy is not None and blink < 0.55:
        cw = layout["adv"]
        chh = layout["size"] * 0.98
        d.rectangle([head_xy[0], head_xy[1] + layout["size"] * 0.12,
                     head_xy[0] + cw * 0.82, head_xy[1] + chh],
                    fill=int(255 * 0.85))

    return np.asarray(img, np.float32) / 255.0
