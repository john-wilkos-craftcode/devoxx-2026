#!/usr/bin/env python3
"""Halftone Room 8 (site/cinema/media/seat-8.jpg) into riso-blue dots on transparent paper, the blue-keyed cinema screen
keyed out to bare paper. Two assets: the band letterbox (2x) and the whole-sheet picture for the opened blue state.
  python3 tools/halftone.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parents[2]
SRC = ROOT / "site/cinema/media/seat-8.jpg"
OUT = HERE / "assets"
BLUE = (0, 0x78, 0xBF, 255)


def keyed_luma(img):
    """luminance 0..1 with the chroma-keyed screen set to 1 (paper)"""
    a = np.asarray(img.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    key = (b > r + 45) & (b > g + 25) & (b > 120)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    # the hall is dark and flat: auto-level on the unkeyed pixels so the seats go light and the walls stay solid ink
    vals = lum[~key]
    lo, hi = np.percentile(vals, 3), np.percentile(vals, 97)
    lum = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1) ** 0.8
    lum[key] = 1.0
    return lum


def halftone(src_crop, out_w, out_h, pitch, angle=45, gain=1.12, supersample=2):
    """draw blue dots on a transparent canvas of out_w x out_h, dot radius from darkness, on a rotated grid"""
    lum = keyed_luma(src_crop.resize((out_w, out_h), Image.LANCZOS))
    S = supersample
    canvas = Image.new("RGBA", (out_w * S, out_h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    diag = int(math.hypot(out_w, out_h) / pitch) + 2
    cx, cy = out_w / 2, out_h / 2
    rmax = pitch / 2 * gain
    for i in range(-diag, diag + 1):
        for j in range(-diag, diag + 1):
            u, v = i * pitch, j * pitch
            x = cx + u * ca - v * sa
            y = cy + u * sa + v * ca
            if x < -pitch or y < -pitch or x > out_w + pitch or y > out_h + pitch:
                continue
            xi, yi = min(max(int(x), 0), out_w - 1), min(max(int(y), 0), out_h - 1)
            dark = 1.0 - lum[yi, xi]
            r = rmax * math.sqrt(dark)
            if r < 0.35:
                continue
            d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=BLUE)
    return canvas.resize((out_w, out_h), Image.LANCZOS)


def main():
    src = Image.open(SRC).convert("RGB")
    W, H = src.size                                     # 3800 x 1620
    # band letterbox: 400 x 117 css px at 2x -> 800 x 234 (after review 1 the drums moved inside the safe margin, so the
    # letterbox is narrower); the same 695 px tall strip (bottom of the screen, the sign, three rows of seats), centre crop
    aspect = 400 / 117
    ch = 695
    cw = int(ch * aspect)
    y0, x0 = 689, (W - cw) // 2
    band = halftone(src.crop((x0, y0, x0 + cw, y0 + ch)), 800, 234, pitch=8)
    band.save(OUT / "halftone-band.png", optimize=True)
    # phone band letterbox: 150 x 131 at 2x -> 300 x 262 (centre crop)
    aspect = 150 / 131
    cw = int(H * aspect)
    x0 = (W - cw) // 2
    phone = halftone(src.crop((x0, 0, x0 + cw, H)), 300, 262, pitch=8.5)
    phone.save(OUT / "halftone-phone.png", optimize=True)
    # whole sheet for the opened blue state: 980 x 613 at 1.5x -> 1470 x 920
    aspect = 980 / 613
    cw = int(H * aspect)
    x0 = (W - cw) // 2
    sheet = halftone(src.crop((x0, 0, x0 + cw, H)), 1470, 920, pitch=7.5)
    sheet.save(OUT / "halftone-sheet.png", optimize=True)
    for f in ("halftone-band.png", "halftone-phone.png", "halftone-sheet.png"):
        print(f, (OUT / f).stat().st_size // 1024, "KB")


main()
