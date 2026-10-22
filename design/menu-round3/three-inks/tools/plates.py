#!/usr/bin/env python3
"""Separate the Codex riso drum (assets/drum2-raw.png: pink + black with a transparent ground) into two printing
plates: drum-ink.png (alpha = where the colour ink prints; tinted per band in CSS) and drum-key.png (alpha = the black
keyline, rims and mesh). The silhouette is the drawing's own alpha. The drum is drawn slim, so it is widened 1.3x here
(invisible at 50-90 px wide on the sheet) to read as a stout ink drum.
  python3 tools/plates.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets"
STRETCH = 1.3
H = 640


def main():
    im = Image.open(OUT / "drum2-raw.png").convert("RGBA")
    a = np.asarray(im).astype(float)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    inside = np.clip((al - 120) / 100.0, 0, 1)
    pinkish = np.clip((r - g - 40) / 70.0, 0, 1) * np.clip((b - 40) / 60.0, 0, 1) * inside
    key = np.clip((120 - lum) / 60.0, 0, 1) * inside
    # the ink plate is the whole silhouette (a riso drum is solid colour; the mesh is printed over it in black), and
    # the mesh, which the drawing made as big black dots, is weakened to a texture so the drum reads as its ink
    ink = inside.copy()
    near = Image.fromarray((pinkish * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(9))
    near = np.clip(np.asarray(near).astype(float) / 255.0 * 2.2, 0, 1)      # ~1 inside the mesh, ~0 at rims and outline
    key = key * (1 - 0.72 * near)
    ys, xs = np.where(inside > 0.5)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    for name, m in (("drum-ink", ink), ("drum-key", key)):
        rgba = np.zeros(im.size[::-1] + (4,), np.uint8)
        rgba[..., 3] = (m * 255).astype(np.uint8)
        out = Image.fromarray(rgba, "RGBA").crop(box)
        w = round(out.width * H / out.height * STRETCH)
        out = out.resize((w, H), Image.LANCZOS)
        out.save(OUT / f"{name}.png", optimize=True)
        print(name, out.size, (OUT / f"{name}.png").stat().st_size // 1024, "KB")
    prev = Image.new("RGBA", out.size, (0xEE, 0xF0, 0xEC, 255))
    prev.paste(Image.new("RGBA", out.size, (0xFF, 0x48, 0xB0, 255)), (0, 0), Image.open(OUT / "drum-ink.png"))
    prev.paste(Image.new("RGBA", out.size, (0x11, 0x11, 0x11, 255)), (0, 0), Image.open(OUT / "drum-key.png"))
    prev.save(OUT / "drum-preview.png")


main()
