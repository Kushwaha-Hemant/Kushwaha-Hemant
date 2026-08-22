"""
encode.py -- frames -> GIF / animated WebP / MP4.

GIF gets a single global palette derived from the most detailed frame. Letting
PIL pick a fresh palette per frame costs roughly a third more bytes and makes
the tone flicker between frames, which is very visible on a slow fade.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def _even(frames):
    """H.264 with yuv420p needs both dimensions even."""
    h, w = frames[0].shape[:2]
    if h % 2 == 0 and w % 2 == 0:
        return frames
    h2, w2 = h - (h % 2), w - (w % 2)
    return [f[:h2, :w2] for f in frames]


def pad_to(frames, size, bg=(5, 7, 9)):
    """Centre each frame on a canvas of exactly ``size`` = (W, H)."""
    W, H = size
    out = []
    for f in frames:
        h, w = f.shape[:2]
        canvas = np.zeros((H, W, 3), np.uint8)
        canvas[:, :] = bg
        y = max(0, (H - h) // 2)
        x = max(0, (W - w) // 2)
        cut = f[: min(h, H), : min(w, W)]
        canvas[y : y + cut.shape[0], x : x + cut.shape[1]] = cut
        out.append(canvas)
    return out


def frame_delay_ms(fps: float) -> int:
    """Delay per frame, rounded to the 10ms grid GIF actually stores.

    GIF keeps delays in centiseconds. 13fps wants 76.9ms, gets written as 70ms,
    and the whole loop silently runs 10% fast. Pick an fps that divides into
    100 -- 12.5, 10, 20 -- and this is a no-op.
    """
    return max(10, int(round(1000.0 / fps / 10.0)) * 10)


def save_gif(frames, path, fps=16, colors=64, key_frame=None, dither=False):
    """Animated GIF with one global palette shared by every frame."""
    path = Path(path)
    key = frames[key_frame if key_frame is not None else len(frames) // 2]
    pal_src = Image.fromarray(key).convert(
        "P", palette=Image.ADAPTIVE, colors=max(2, min(256, colors))
    )
    dmode = Image.FLOYDSTEINBERG if dither else Image.NONE
    imgs = [Image.fromarray(f).quantize(palette=pal_src, dither=dmode) for f in frames]
    imgs[0].save(
        path,
        save_all=True,
        append_images=imgs[1:],
        duration=frame_delay_ms(fps),
        loop=0,
        optimize=True,
        disposal=1,
    )
    return path.stat().st_size


def save_webp(frames, path, fps=16, quality=72, method=6):
    """Animated WebP. Far smaller than GIF at the same size, and 24-bit.

    Every frame carries its own ``info["duration"]``. Passing duration only as
    a save() keyword silently produces a file with zero frame delays -- Pillow
    reads the per-frame value first, and arrays built with fromarray() have
    none. The result still decodes, but plays at whatever rate the viewer
    guesses.
    """
    path = Path(path)
    delay = int(round(1000.0 / fps))
    imgs = []
    for f in frames:
        img = Image.fromarray(f)
        img.info["duration"] = delay
        imgs.append(img)
    imgs[0].save(
        path,
        save_all=True,
        append_images=imgs[1:],
        duration=delay,
        loop=0,
        quality=quality,
        method=method,
        lossless=False,
    )
    return path.stat().st_size


def save_mp4(frames, path, fps=16, crf=18, preset="veryslow"):
    """H.264 via the ffmpeg binary bundled with imageio-ffmpeg."""
    import imageio_ffmpeg

    path = Path(path)
    frames = _even(frames)
    h, w = frames[0].shape[:2]
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        exe, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-an",
        "-vcodec", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for f in frames:
        proc.stdin.write(np.ascontiguousarray(f).tobytes())
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed: {err[:800]}")
    return path.stat().st_size


def human(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n / 1.0:.1f}{unit}"
        n /= 1024.0
    return f"{n}B"


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.2f} MB"
