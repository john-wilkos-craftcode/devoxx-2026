"""Put a render next to the reference photo it should match, with numbers to steer by.

    python3 scripts/compare_render.py <render.png> <photo> [out.jpg]

Writes a sheet (photo on top, render below, same width) and prints luminance and colour per band
(top, middle, bottom third), so "too bright", "too blue", "ceiling too dark" are measured, not guessed.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

render_path, photo_path = Path(sys.argv[1]), Path(sys.argv[2])
out = Path(sys.argv[3]) if len(sys.argv) > 3 else render_path.with_name(render_path.stem + "-vs-photo.jpg")
W = 1280
photo, render = (Image.open(p).convert("RGB") for p in (photo_path, render_path))
photo, render = (im.resize((W, round(W * im.height / im.width))) for im in (photo, render))


def stats(im):
    a = np.asarray(im, dtype=np.float32) / 255
    lum = a @ np.array([0.2126, 0.7152, 0.0722])
    rows = []
    for name, band in zip(("top", "middle", "bottom"), np.array_split(np.arange(a.shape[0]), 3)):
        px = a[band].reshape(-1, 3)
        rows.append((name, lum[band].mean(), np.percentile(lum[band], 5), np.percentile(lum[band], 95), *px.mean(0)))
    return rows


print(f"{'':8}{'band':8}{'lum':>6}{'p5':>6}{'p95':>6}{'R':>6}{'G':>6}{'B':>6}")
for label, im in (("photo", photo), ("render", render)):
    for row in stats(im):
        print(f"{label:8}{row[0]:8}" + "".join(f"{v:6.2f}" for v in row[1:]))

sheet = Image.new("RGB", (W, photo.height + render.height + 6), "black")
sheet.paste(photo, (0, 0))
sheet.paste(render, (0, photo.height + 6))
d = ImageDraw.Draw(sheet)
for y, text in ((0, "photo"), (photo.height + 6, "render")):
    d.rectangle([0, y, 60, y + 16], fill="black")
    d.text((4, y + 2), text, fill="yellow")
sheet.save(out, quality=90)
print(out)
