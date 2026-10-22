#!/usr/bin/env python3
"""Finish the page assets: the loupe as a black-plate mask (assets/loupe.png) with its lens ellipse measured, and the
halftones as lossless WebP (the band at 2x, the sheet at 1x).
  python3 tools/assets.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets"


def loupe():
    im = Image.open(OUT / "loupe-raw.png").convert("RGBA")
    a = np.asarray(im)
    al = a[..., 3]
    op = al > 128
    ys, xs = np.where(op)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    # the lens: the transparent run down the centre column between the ring's top and the skirt
    cx = (x0 + x1) // 2
    col = op[y0:y1, cx]
    runs, start = [], None
    for i, v in enumerate(col):
        if not v and start is None:
            start = i
        if v and start is not None:
            runs.append((start, i)); start = None
    lens_top, lens_bot = max(runs, key=lambda r: r[1] - r[0])
    cy = y0 + (lens_top + lens_bot) // 2
    row = op[cy, x0:x1]
    runs, start = [], None
    for i, v in enumerate(row):
        if not v and start is None:
            start = i
        if v and start is not None:
            runs.append((start, i)); start = None
    lens_l, lens_r = max(runs, key=lambda r: r[1] - r[0])
    print("loupe box", box, "lens (fractions of the trimmed box): left %.3f top %.3f width %.3f height %.3f" % (
        lens_l / w, lens_top / h, (lens_r - lens_l) / w, (lens_bot - lens_top) / h))
    mask = np.zeros((h, w, 4), np.uint8)
    mask[..., 3] = al[y0:y1, x0:x1]
    out = Image.fromarray(mask, "RGBA")
    W = 420
    out = out.resize((W, round(h * W / w)), Image.LANCZOS)
    out.save(OUT / "loupe.png", optimize=True)
    print("loupe.png", out.size, (OUT / "loupe.png").stat().st_size // 1024, "KB")


def webp():
    for name in ("halftone-band", "halftone-phone", "halftone-sheet"):
        p = OUT / f"{name}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        if name == "halftone-sheet":                  # a ghost behind the opened blue state: lossy is fine
            im = im.resize((980, 613), Image.LANCZOS)
            im.save(OUT / f"{name}.webp", quality=78, method=6)
        else:
            im.save(OUT / f"{name}.webp", lossless=True, quality=100, method=6)
        print(f"{name}.webp", im.size, (OUT / f"{name}.webp").stat().st_size // 1024, "KB")


loupe()
webp()
