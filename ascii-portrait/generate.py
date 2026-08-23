#!/usr/bin/env python3
"""
generate.py -- build the animated code-portrait in every delivery size.

    python generate.py --image me.png
    python generate.py --image me.png --only square --formats webp,mp4
    python generate.py --image me.png --preview          # stills only, fast

Three presets come out of one photo:

    square   1:1, for a profile picture or a centred README block
    wide     hero banner, portrait left, name set in the same character grid
    small    lightweight loop for inline embedding

Run --preview first. It renders one resolved still per preset in a couple of
seconds, which is the fastest way to check the crop and tone before paying for
a full encode.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))

import banner
import core
import encode
import render
import terminal

# The character set from the brief, ordered lightest-to-densest by measured ink
# coverage. core.measure_ramp() recomputes this for any other font.
CHARSET = " .-><*=\\/+)(}{[]1#%$0&@"

# Cool desaturated cyan-grey. Deliberately not phosphor green or amber.
PALETTE = (
    (0.00, 6, 9, 12),
    (0.30, 58, 92, 102),
    (0.65, 158, 202, 212),
    (1.00, 234, 250, 254),
)

WEIGHTS_2 = [0.235, 0.235]
WEIGHTS_3 = [0.205, 0.205, 0.130]

FONT_REGULAR = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"

PRESETS = {
    # Wide hero for the GitHub profile README. Plays once and stops on the
    # finished portrait; everything else here loops.
    "banner": dict(
        out_size=(1800, 600),
        cols=132, cell=(5, 9), frames=104, fps=12.5,
        # Tighter crop than the square cuts: the portrait now owns 36.7% of the
        # width, so the face can fill more of its box without being cropped.
        head_room=1.95, face_bias=0.0, crop_shift_x=0.07,
        banner_cols=360,
        play_once=True, hold_last_ms=6000,
        # GitHub renders the hero at roughly 880px wide, so 1800 is already 2x.
        # The WebP keeps full resolution; the GIF fallback is written at 1200
        # wide, which is still 1.4x the display size and about half the bytes.
        gif_size=(1200, 400),
        gif_colors=48, webp_quality=64, crf=22,
        formats=("gif", "webp", "mp4"),
    ),
    "square": dict(
        out_size=(600, 600),
        cols=120, cell=(5, 9), frames=64, fps=12.5,
        head_room=2.10, face_bias=0.09,
        gif_colors=48, webp_quality=64, crf=22,
        formats=("webp", "gif", "mp4"),
    ),
    "wide": dict(
        out_size=(1200, 560),
        cols=110, cell=(5, 9), frames=64, fps=12.5,
        head_room=2.10, face_bias=0.09,
        wide_cols=240, pad_left=4, text_x=(126, 238),
        gif_colors=16, webp_quality=60, crf=23,
        text=("HEMANT", "KUSHWAHA", "AI & FULL-STACK"),
        formats=("webp", "mp4"),
    ),
    "boot": dict(
        out_size=(600, 600),
        cols=120, cell=(5, 9), frames=100, fps=12.5,
        head_room=2.10, face_bias=0.09,
        boot=True,
        gif_colors=16, webp_quality=62, crf=23,
        formats=("webp", "gif", "mp4"),
    ),
    "small": dict(
        out_size=(320, 320),
        cols=64, cell=(5, 9), frames=50, fps=10,
        head_room=2.05, face_bias=0.09,
        gif_colors=12, webp_quality=58, crf=26,
        formats=("gif", "webp"),
    ),
}


def stamp_text(grid: dict, lines, cell, x0: int, x1: int, font_path: str) -> None:
    """Burn caption text into the character grid itself.

    The mask is drawn at final pixel resolution and only then averaged down to
    cells. Drawing straight into a cell-sized canvas looks like it should work
    and does not: cells are 5x9, so letterforms come out squashed to
    unreadable mush. Building the text out of the same glyphs as the face --
    rather than compositing pixels over the top -- lets it resolve with the
    portrait instead of floating above it.
    """
    cw, ch = cell
    rows, cols = grid["rows"], grid["cols"]
    wc = max(8, x1 - x0)
    canvas = Image.new("L", (wc * cw, rows * ch), 0)
    d = ImageDraw.Draw(canvas)

    px_h = rows * ch
    px_w = wc * cw
    weights = (WEIGHTS_3 if len(lines) > 2 else WEIGHTS_2)[: len(lines)]
    fitted = []
    for text, weight in zip(lines, weights):
        size = max(10, int(px_h * weight))
        f = ImageFont.truetype(font_path, size)
        while d.textlength(text, font=f) > px_w * 0.97 and size > 8:
            size -= 1
            f = ImageFont.truetype(font_path, size)
        fitted.append((text, f, size))

    gaps = [int(px_h * 0.012), int(px_h * 0.075)]
    total = sum(s for _, _, s in fitted) + sum(gaps[: len(fitted) - 1])
    y = (px_h - total) // 2
    for i, (text, f, size) in enumerate(fitted):
        d.text((0, y), text, fill=255, font=f)
        y += size + (gaps[i] if i < len(gaps) else 0)

    mask = np.asarray(canvas.resize((wc, rows), Image.LANCZOS), np.float32) / 255.0
    # Soft, not binary: letting stroke edges fall to lighter glyphs anti-aliases
    # the letterforms into the same ramp the face is built from. The gamma keeps
    # the body of each stroke up at the dense end.
    mask = np.clip((mask - 0.08) / 0.60, 0.0, 1.0) ** 0.62

    sl = slice(x0, x0 + wc)
    grid["luma"][:, sl] = np.maximum(grid["luma"][:, sl], mask * 0.97)
    grid["index"][:, sl] = np.clip(
        (grid["luma"][:, sl] * (len(CHARSET) - 1)).round(), 0, len(CHARSET) - 1
    ).astype(grid["index"].dtype)
    grid["matte"][:, sl] = np.maximum(grid["matte"][:, sl], mask)
    grid["_text_mask"] = np.zeros((rows, cols), np.float32)
    grid["_text_mask"][:, sl] = mask


def compose_wide(src_grid: dict, cols_w: int, pad_left: int) -> dict:
    """Letterbox a correctly-proportioned portrait into a wider grid.

    Cropping the source photo to a 2.4:1 window instead would shave the top of
    the head off -- a square photo simply has no wide framing that keeps a full
    head in shot.
    """
    rows = src_grid["rows"]
    out = dict(src_grid)
    out["cols"] = cols_w
    for key, fill in (("luma", 0.0), ("mag", 0.0), ("matte", 0.0),
                      ("index", 0), ("edge_bucket", 0)):
        src = src_grid[key]
        wide = np.full((rows, cols_w), fill, dtype=src.dtype)
        w = min(src.shape[1], cols_w - pad_left)
        wide[:, pad_left:pad_left + w] = src[:, :w]
        out[key] = wide
    return out


def build_banner(p: dict, image: str, outdir: Path, formats=None, preview=False):
    """Wide 3:1 hero: portrait centred, code rain and terminal text either side."""
    cw, ch = p["cell"]
    bcfg = banner.BannerConfig(total_cols=p["banner_cols"], portrait_cols=p["cols"])

    sc = core.SourceConfig(
        path=image, cols=p["cols"], head_room=p["head_room"],
        face_bias=p["face_bias"], bg_level=0.02, cell_aspect=cw / ch,
        crop_shift_x=p.get("crop_shift_x", 0.0),
    )
    # Crop to the portrait BOX's aspect, not to a square. The box is 660x603, so
    # a square crop would leave the sides of it empty.
    rows_target = p["out_size"][1] // ch
    box_aspect = (p["cols"] * cw) / float(rows_target * ch)
    grid = banner.compose(core.build_grid(sc, CHARSET, aspect=box_aspect), bcfg)
    rows, cols = grid["rows"], grid["cols"]
    W, H = cols * cw, rows * ch

    rc = render.RenderConfig(
        cell_w=cw, cell_h=ch, frames=p["frames"], fps=p["fps"], stops=PALETTE,
        vignette=0.28, scanline=0.10, bloom=0.34, edge_threshold=2.0,
        grain=0.008, grain_static=True, shimmer=0.0, noise_hold=3,
        glitch_amount=0.40,
    )

    rain = banner.CodeRain(rows, cols, len(CHARSET), bcfg)
    sw = banner.side_weight(rows, cols, bcfg)

    # Both text layers now share one left-hand band. left_frac=0 keeps them
    # flush with each other so the block reads as a single column.
    tx0 = bcfg.text_x * cw
    band = bcfg.text_cols * cw

    boot_cfg = terminal.BootConfig(left_frac=0.0, font_frac=0.040)
    info_cfg = terminal.BootConfig(
        script=list(banner.IDENT_LINES), left_frac=0.0, font_frac=0.043, bar_cells=0,
    )
    boot_layout = terminal.plan(boot_cfg, W, H, x0=tx0, width=band)
    info_layout = terminal.plan(info_cfg, W, H, x0=tx0, width=band)

    def boot_draw(w, h, prog, blink):
        return terminal.draw(boot_layout, boot_cfg, w, h, prog, blink)

    def info_draw(w, h, prog, blink):
        return terminal.draw(info_layout, info_cfg, w, h, prog, 1.0)

    ko_boot = banner.text_knockout(rows, cols, (cw, ch), boot_layout, len(boot_cfg.script))
    ko_info = banner.text_knockout(rows, cols, (cw, ch), info_layout, len(info_cfg.script))

    def rain_gate(t):
        # The info block stays to the end, so its knockout is permanent. The
        # boot log fades, so its knockout releases and the rain fills back in.
        return np.minimum(ko_info, 1.0 - (1.0 - ko_boot) * render.curve(t, render.B_BOOT))

    t0 = time.time()
    frames = render.render_banner(grid, CHARSET, rc, rain, sw,
                                  boot_draw, info_draw, rain_gate=rain_gate)
    frames = encode.pad_to(frames, p["out_size"])
    Wp, Hp = p["out_size"]
    print(f"  banner {Wp}x{Hp} ({Wp/Hp:.2f}:1) {len(frames)}f @{p['fps']}fps "
          f"({len(frames)/p['fps']:.1f}s)  render {time.time()-t0:.1f}s")

    final = Image.fromarray(frames[-1])
    final.save(outdir / "banner-final.png")
    print(f"      png  {encode.fmt_size((outdir/'banner-final.png').stat().st_size):>9}  banner-final.png")
    if preview:
        return

    for fmt in (formats or p["formats"]):
        t = time.time()
        path = outdir / f"portrait-banner.{fmt}"
        if fmt == "gif":
            gw, gh = p.get("gif_size", tuple(p["out_size"]))
            src = frames
            if (gw, gh) != tuple(p["out_size"]):
                src = [np.asarray(Image.fromarray(fr).resize((gw, gh), Image.LANCZOS))
                       for fr in frames]
            # loop=None omits the Netscape extension entirely -> plays once.
            # key_frame=-1: build the palette from the frame the viewer ends on.
            size = encode.save_gif(src, path, p["fps"], colors=p["gif_colors"],
                                   key_frame=-1, loop=None,
                                   hold_last_ms=p["hold_last_ms"])
        elif fmt == "webp":
            size = encode.save_webp(frames, path, p["fps"], quality=p["webp_quality"],
                                    loop=1, hold_last_ms=p["hold_last_ms"])
        elif fmt == "mp4":
            size = encode.save_mp4(frames, path, p["fps"], crf=p["crf"])
        else:
            continue
        print(f"      {fmt:4} {encode.fmt_size(size):>9}  ({time.time()-t:.1f}s)  {path.name}")


def build(name: str, image: str, outdir: Path, formats=None, preview=False):
    p = PRESETS[name]
    if p.get("banner_cols"):
        return build_banner(p, image, outdir, formats, preview)
    cw, ch = p["cell"]
    W, H = p["out_size"]

    sc = core.SourceConfig(
        path=image,
        cols=p["cols"],
        head_room=p["head_room"],
        face_bias=p["face_bias"],
        bg_level=0.02,
        cell_aspect=cw / ch,
    )
    # Always crop the portrait square; wide layouts letterbox it afterwards so
    # the head stays whole.
    grid = core.build_grid(sc, CHARSET, aspect=1.0)

    if p.get("wide_cols"):
        grid = compose_wide(grid, p["wide_cols"], p["pad_left"])
    if p.get("text"):
        tx0, tx1 = p["text_x"]
        stamp_text(grid, p["text"], (cw, ch), tx0, tx1, FONT_BOLD)

    rc = render.RenderConfig(
        cell_w=cw, cell_h=ch,
        frames=p["frames"], fps=p["fps"],
        stops=PALETTE,
        vignette=0.35, scanline=0.10, bloom=0.34,
        edge_threshold=2.0,          # tone alone carries structure; see README
        grain=0.008, grain_static=True,
        shimmer=0.03, noise_hold=3,
        glitch_amount=0.45,
    )

    boot_cfg = terminal.BootConfig() if p.get("boot") else None

    t0 = time.time()
    if preview:
        still = render.render_frames(grid, CHARSET, rc, still=True)
        still = encode.pad_to(still, (W, H))
        path = outdir / f"preview-{name}.png"
        Image.fromarray(still[0]).save(path)
        print(f"  {name:6} preview {W}x{H}  {time.time() - t0:.1f}s  -> {path.name}")
        return

    if boot_cfg is not None:
        layout_cache = {}

        def boot_draw(bw, bh, progress, blink):
            key = (bw, bh)
            if key not in layout_cache:
                layout_cache[key] = terminal.plan(boot_cfg, bw, bh)
            return terminal.draw(layout_cache[key], boot_cfg, bw, bh, progress, blink)

        frames = render.render_boot_loop(grid, CHARSET, rc, boot_draw)
    else:
        frames = render.render_frames(grid, CHARSET, rc)
    frames = encode.pad_to(frames, (W, H))
    seam = float(np.abs(frames[0].astype(int) - frames[-1].astype(int)).mean())
    print(f"  {name:6} {W}x{H} {len(frames)}f @{p['fps']}fps "
          f"({len(frames) / p['fps']:.1f}s)  render {time.time() - t0:.1f}s  seam {seam:.2f}")

    want = formats or p["formats"]
    for fmt in want:
        t = time.time()
        path = outdir / f"portrait-{name}.{fmt}"
        if fmt == "gif":
            size = encode.save_gif(frames, path, p["fps"], colors=p["gif_colors"])
        elif fmt == "webp":
            size = encode.save_webp(frames, path, p["fps"], quality=p["webp_quality"])
        elif fmt == "mp4":
            size = encode.save_mp4(frames, path, p["fps"], crf=p["crf"])
        else:
            continue
        print(f"      {fmt:4} {encode.fmt_size(size):>9}  ({time.time() - t:.1f}s)  {path.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True, help="source photograph")
    ap.add_argument("--out", default="../assets", help="output directory")
    ap.add_argument("--only", default="", help="comma list: square,wide,small")
    ap.add_argument("--formats", default="", help="comma list: webp,gif,mp4")
    ap.add_argument("--preview", action="store_true", help="stills only, fast")
    a = ap.parse_args()

    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    names = [n.strip() for n in a.only.split(",") if n.strip()] or list(PRESETS)
    formats = [f.strip() for f in a.formats.split(",") if f.strip()] or None

    print(f"source: {a.image}")
    for n in names:
        if n not in PRESETS:
            print(f"  ! unknown preset {n!r}, skipping")
            continue
        build(n, a.image, outdir, formats, a.preview)


if __name__ == "__main__":
    main()
