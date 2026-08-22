"""
core.py -- photograph -> character grid.

Produces three aligned grids the renderer consumes:
  * ``index``       which glyph each cell settles on
  * ``luma``        how brightly to draw it
  * ``edge_bucket`` orientation of any stroke running through the cell

Two decisions here carry most of the quality:

1. **Subject isolation.** A seeded GrabCut lifts the head and shoulders off the
   background. Without it, CLAHE invents texture out of a flat studio wall and
   the portrait drowns in noise that reads as static rather than structure.
2. **Local, not global, contrast.** A global curve crushes a black shirt to
   nothing. CLAHE keeps the fabric legible while leaving the face intact.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Ink coverage measured from the real font, not eyeballed. See measure_ramp().
FALLBACK_RAMP = " .-><*=\\/+)(}{[]1#%$0&@"

# Glyphs that read as a stroke in a given direction, indexed by orientation
# bucket: 0 = horizontal, 1 = 45deg, 2 = vertical, 3 = 135deg.
DIRECTIONAL = ("-", "/", "|", "\\")
DIRECTIONAL_NO_PIPE = ("-", "/", "1", "\\")


@dataclass
class SourceConfig:
    """Everything about turning one photo into one character grid."""

    path: str
    cols: int = 132
    cell_aspect: float = 0.5417       # Consolas advance / em. Measured, not guessed.
    head_room: float = 1.95           # crop span as a multiple of face width
    face_bias: float = 0.16           # push the crop down: headroom above, torso below
    crop_shift_x: float = 0.0         # +ve moves the window right, subject sits left
    crop: tuple | None = None         # (cx, cy, w, h) normalised, overrides auto

    # tone
    clahe_clip: float = 2.2
    clahe_grid: int = 8
    gamma: float = 0.86
    black_point: float = 0.02
    white_point: float = 0.995
    detail: float = 0.85              # unsharp amount

    # subject isolation
    segment: bool = True
    grabcut_iters: int = 7
    bg_level: float = 0.06            # how much background survives, 0 = pure black
    mask_feather: float = 3.5

    # structure
    edge_gain: float = 1.0
    lift: float = 0.0                 # raise the whole grid after masking


def measure_ramp(font_path: str, charset: str, size: int = 48) -> str:
    """Order ``charset`` by real rendered ink coverage, lightest first."""
    font = ImageFont.truetype(font_path, size)
    cov: dict[str, float] = {}
    for ch in dict.fromkeys(charset):
        tile = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(tile).text((size // 4, size // 8), ch, fill=255, font=font)
        cov[ch] = float(np.asarray(tile, np.float32).mean())
    return "".join(sorted(cov, key=lambda c: cov[c]))


def detect_face(img: np.ndarray) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, 1.08, 6, minSize=(80, 80))
    if not len(faces):
        return None
    return tuple(int(v) for v in max(faces, key=lambda f: f[2] * f[3]))


_MASK_CACHE: dict = {}


def subject_mask(img: np.ndarray, face: tuple, cfg: SourceConfig) -> np.ndarray:
    """Soft head-and-shoulders matte via seeded GrabCut.

    Seeding with explicit FG/BG regions rather than a bounding rect matters: a
    rect that spans most of the frame leaves GrabCut no background to model, and
    it happily returns three quarters of the image as foreground.
    """
    key = (cfg.path, face, cfg.grabcut_iters, cfg.mask_feather)
    if key in _MASK_CACHE:
        return _MASK_CACHE[key]
    H, W = img.shape[:2]
    s = max(1, int(round(max(H, W) / 420.0)))
    small = cv2.resize(img, (W // s, H // s), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    fx, fy, fw, fh = (v // s for v in face)

    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    cx = fx + fw // 2
    # Definite foreground: inner face, plus a torso column beneath it.
    cv2.ellipse(mask, (cx, fy + int(fh * 0.55)),
                (int(fw * 0.34), int(fh * 0.42)), 0, 0, 360, cv2.GC_FGD, -1)
    cv2.rectangle(mask, (fx + int(fw * 0.05), fy + int(fh * 1.25)),
                  (fx + int(fw * 0.95), h - 1), cv2.GC_FGD, -1)
    # Probable foreground: generous head-and-shoulders envelope.
    cv2.ellipse(mask, (cx, fy + int(fh * 0.5)),
                (int(fw * 0.78), int(fh * 0.86)), 0, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.rectangle(mask, (max(0, fx - int(fw * 0.75)), fy + int(fh * 0.95)),
                  (min(w - 1, fx + int(fw * 1.75)), h - 1), cv2.GC_PR_FGD, -1)
    # Definite background: border strips, and the corners props tend to occupy.
    b = max(2, int(w * 0.045))
    mask[:b, :] = cv2.GC_BGD
    mask[:, :b] = cv2.GC_BGD
    mask[:, -b:] = cv2.GC_BGD

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(small, mask, None, bgd, fgd, cfg.grabcut_iters, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return np.ones((H, W), np.float32)

    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), 8)
    if n > 1:                                     # drop stray islands
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = np.where(lab == big, 255, 0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    m = cv2.GaussianBlur(m, (0, 0), cfg.mask_feather * s)
    out = m.astype(np.float32) / 255.0
    _MASK_CACHE[key] = out
    return out


def _crop_rect(img: np.ndarray, face, cfg: SourceConfig, aspect: float):
    """Crop window around the face at ``aspect`` (width / height)."""
    H, W = img.shape[:2]
    if cfg.crop is not None:
        cx, cy, cw, ch = cfg.crop
        cx, cy, cw, ch = cx * W, cy * H, cw * W, ch * H
    else:
        if face is not None:
            fx, fy, fw, fh = face
            cx, cy = fx + fw / 2.0, fy + fh / 2.0
            span = fw * cfg.head_room
        else:
            cx, cy, span = W / 2.0, H / 2.0, min(W, H) * 0.9
        if aspect >= 1.0:
            ch, cw = span, span * aspect
        else:
            cw, ch = span, span / aspect
        cx += cfg.crop_shift_x * cw

    scale = min(1.0, W / cw, H / ch)
    cw, ch = cw * scale, ch * scale
    cy += cfg.face_bias * ch          # headroom above the hair, torso below
    cx = float(np.clip(cx, cw / 2.0, W - cw / 2.0))
    cy = float(np.clip(cy, ch / 2.0, H - ch / 2.0))
    x0, y0 = int(round(cx - cw / 2.0)), int(round(cy - ch / 2.0))
    return x0, y0, int(round(cw)), int(round(ch))


def _tone_map(gray: np.ndarray, weight: np.ndarray, cfg: SourceConfig) -> np.ndarray:
    """Local-contrast pass. Black/white points sample the subject only."""
    clahe = cv2.createCLAHE(cfg.clahe_clip, (cfg.clahe_grid, cfg.clahe_grid))
    out = clahe.apply(gray)
    if cfg.detail > 0:
        blur = cv2.GaussianBlur(out, (0, 0), 3.0)
        out = cv2.addWeighted(out, 1.0 + 0.7 * cfg.detail, blur, -0.7 * cfg.detail, 0)

    f = out.astype(np.float32) / 255.0
    sel = f[weight > 0.5]
    if sel.size < 64:
        sel = f.reshape(-1)
    lo = float(np.quantile(sel, cfg.black_point))
    hi = float(np.quantile(sel, cfg.white_point))
    f = np.clip((f - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return np.power(f, cfg.gamma, dtype=np.float32)


def build_grid(cfg: SourceConfig, ramp: str, aspect: float = 1.0,
               allow_pipe: bool = True) -> dict:
    """Photo in, character grid out. ``aspect`` is output width / height."""
    img = cv2.imread(cfg.path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(cfg.path)

    face = detect_face(img)
    matte = subject_mask(img, face, cfg) if (cfg.segment and face) else np.ones(img.shape[:2], np.float32)

    x0, y0, cw, ch = _crop_rect(img, face, cfg, aspect)
    crop = img[y0:y0 + ch, x0:x0 + cw]
    matte = matte[y0:y0 + ch, x0:x0 + cw]
    ch, cw = crop.shape[:2]

    # Cells are taller than wide, so row count must compensate or the face
    # comes out vertically stretched.
    rows = max(8, int(round(cfg.cols * (ch / cw) * cfg.cell_aspect)))

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    tone = _tone_map(gray, matte, cfg)

    # Gradients at full resolution, averaged per cell: cell-scale structure
    # survives, pixel grain does not.
    sigma = max(cw / max(cfg.cols, 1), 1.0) * 0.9
    blurred = cv2.GaussianBlur(tone, (0, 0), sigma)
    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)

    def down(a):
        return cv2.resize(a, (cfg.cols, rows), interpolation=cv2.INTER_AREA)

    luma, gxc, gyc, mk = down(tone), down(gx), down(gy), down(matte)

    # Fade the background instead of cutting it: a faint ghost keeps depth.
    luma = np.clip(luma * (cfg.bg_level + (1.0 - cfg.bg_level) * mk) + cfg.lift, 0.0, 1.0)

    mag = np.sqrt(gxc * gxc + gyc * gyc)
    q = float(np.quantile(mag, 0.985))
    mag = np.clip(mag / max(q, 1e-6), 0.0, 1.0) * cfg.edge_gain
    mag = np.clip(mag * mk, 0.0, 1.0).astype(np.float32)   # no edges in the void

    index = np.clip((luma * (len(ramp) - 1)).round().astype(np.int32), 0, len(ramp) - 1)

    # Stroke runs perpendicular to the gradient.
    edge_dir = (np.degrees(np.arctan2(gyc, gxc)) + 90.0) % 180.0
    bucket = (np.floor(((edge_dir + 22.5) % 180.0) / 45.0).astype(np.int32)) % 4
    chars = list(DIRECTIONAL if allow_pipe else DIRECTIONAL_NO_PIPE)

    return {
        "rows": rows,
        "cols": cfg.cols,
        "luma": luma.astype(np.float32),
        "mag": mag,
        "matte": mk.astype(np.float32),
        "index": index,
        "edge_bucket": bucket,
        "edge_chars": chars,
        "face": face,
    }
