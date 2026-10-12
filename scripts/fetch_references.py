"""Download the venue reference photos listed in data/references/references.json into
data/references/img/ (gitignored: the photos are CC BY-NC-ND, used as modelling reference only).
Also writes one contact sheet per area (img/_<area>.jpg) for a quick look.

    python3 scripts/fetch_references.py
"""
import json
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "data" / "references"
IMG = REF / "img"
manifest = json.loads((REF / "references.json").read_text())
IMG.mkdir(parents=True, exist_ok=True)


def name(p):
    return f"{p['area']}-{p['id']}.jpg"


def fetch(p):
    """Through curl, one at a time: Flickr's image CDN answers Python's urllib with 429."""
    out = IMG / name(p)
    for wait in (0, 10, 30, 90):
        time.sleep(wait)
        code = subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", "-o", str(out), "-w", "%{http_code}", p["image"]],
                              capture_output=True, text=True).stdout
        if code == "200":
            return
        out.unlink(missing_ok=True)
    raise SystemExit(f"HTTP {code} on {p['image']}; rerun later (finished files are kept)")


for p in manifest["photos"]:
    if not (IMG / name(p)).exists():
        fetch(p)
        time.sleep(1)

# contact sheets: three per row at 600 px wide, numbered in manifest order
W = 600
for area in manifest["areas"]:
    files = [IMG / l["file"] for l in manifest["local"] if l["area"] == area]
    files += [IMG / name(p) for p in manifest["photos"] if p["area"] == area]
    ims = [Image.open(f).convert("RGB") for f in files if f.exists()]
    ims = [im.resize((W, round(W * im.height / im.width))) for im in ims]
    rows = [ims[i:i + 3] for i in range(0, len(ims), 3)]
    sheet = Image.new("RGB", (3 * W + 8, sum(max(i.height for i in r) + 4 for r in rows)), "black")
    draw, y, k = ImageDraw.Draw(sheet), 0, 0
    for r in rows:
        for c, im in enumerate(r):
            sheet.paste(im, (c * (W + 4), y))
            draw.rectangle([c * (W + 4), y, c * (W + 4) + 24, y + 14], fill="black")
            draw.text((c * (W + 4) + 4, y + 2), str(k), fill="yellow")
            k += 1
        y += max(i.height for i in r) + 4
    sheet.save(IMG / f"_{area}.jpg", quality=85)
print(f"{len(manifest['photos'])} photos in {IMG}")
