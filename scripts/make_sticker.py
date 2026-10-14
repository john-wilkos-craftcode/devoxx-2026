"""Die-cut sticker texture for the laptop lid, from the artwork in data/laptop/sticker-source.png.

    python3 scripts/make_sticker.py

The source is small and flat (black lines, orange waves, on white), so it is upscaled and each colour is cleaned to a
smooth edge, then cut out like a vinyl sticker: the artwork's outline, holes filled, grown by a white margin.
Writes data/laptop/sticker.png (RGBA: the print, transparent off the sticker) and sticker-height.png (the sticker's
raised edge, for the bump), both 2048 px tall.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DIR = Path(__file__).resolve().parent.parent / "data" / "laptop"
src = Image.open(DIR / "sticker-source.png").convert("RGB")
src = src.crop((0, 0, src.width, src.height - 10))            # the source is cropped through the shoulders: end above that
H = 2048
scale = H / src.height
pad = int(0.09 * H)                                       # room for the white margin
big = np.asarray(src.resize((round(src.width * scale), H), Image.LANCZOS), dtype=np.float32) / 255
r, g, b = big[..., 0], big[..., 1], big[..., 2]
ink = ndimage.gaussian_filter(((r + g + b) / 3 < 0.45).astype(np.float32), 2.2) > 0.5            # the black line work
orange = ndimage.gaussian_filter(((r - b) > 0.35).astype(np.float32), 2.2) > 0.5                  # the waves
ink &= ~orange
art = np.pad(ink | orange, pad)
ink, orange = np.pad(ink, pad), np.pad(orange, pad)
# die cut: the artwork with its holes filled, grown by a margin, edge smoothed (a cutter can't follow tiny notches)
yy, xx = np.mgrid[-1:2, -1:2]
cut = ndimage.binary_fill_holes(ndimage.binary_closing(art, iterations=int(0.03 * H)))
dist = ndimage.distance_transform_edt(~cut)
margin = 0.035 * H
cut = ndimage.gaussian_filter((dist <= margin).astype(np.float32), 0.012 * H) > 0.5
cut = ndimage.binary_fill_holes(cut)
# below the cup, the neck is one piece of vinyl, not two legs: fill each row between its outermost edges
rows = np.nonzero(cut.any(axis=1))[0]
for y in range(rows[0] + int(0.72 * (rows[-1] - rows[0])), rows[-1] + 1):
    xs_ = np.nonzero(cut[y])[0]
    cut[y, xs_[0]:xs_[-1] + 1] = True
cut = ndimage.gaussian_filter(cut.astype(np.float32), 0.006 * H) > 0.5
alpha = ndimage.gaussian_filter(cut.astype(np.float32), 1.0)                                     # antialiased edge

white, black, orng = np.array([0.95, 0.95, 0.93]), np.array([0.07, 0.07, 0.08]), np.array([0.96, 0.62, 0.17])
inkf = ndimage.gaussian_filter(ink.astype(np.float32), 0.8)[..., None]
orf = ndimage.gaussian_filter(orange.astype(np.float32), 0.8)[..., None]
rgb = white * (1 - inkf - orf).clip(0, 1) + black * inkf + orng * orf
out = np.dstack([rgb, alpha]).clip(0, 1)
ys, xs = np.nonzero(alpha > 0.01)
crop = (slice(max(0, ys.min() - 8), ys.max() + 9), slice(max(0, xs.min() - 8), xs.max() + 9))
Image.fromarray((out[crop] * 255).astype(np.uint8), "RGBA").save(DIR / "sticker.png", optimize=True)
# height: the vinyl is a flat slab with a slightly rounded edge; the print adds nothing
height = ndimage.gaussian_filter(cut.astype(np.float32), 0.004 * H)[crop]
Image.fromarray((height * 255).astype(np.uint8), "L").save(DIR / "sticker-height.png", optimize=True)
print("sticker.png", out[crop].shape)
