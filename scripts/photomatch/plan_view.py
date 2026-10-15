"""Top-down drawing of the venue plan (data/venue/venue.json) with the photo cameras on it, to check a model's
layout against the plan.  python3 scripts/photomatch/plan_view.py <out.png> [--floor 0] [--box x0,y0,x1,y1] [--ppm 12]"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from pm import Cam  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--floor", type=int, default=0)
ap.add_argument("--box", default="-40,-90,50,20")
ap.add_argument("--ppm", type=float, default=12)
a = ap.parse_args()
v = json.loads((ROOT / "data/venue/venue.json").read_text())["venue"]
x0, y0, x1, y1 = [float(t) for t in a.box.split(",")]
S = a.ppm
W, H = int((x1 - x0) * S), int((y1 - y0) * S)
im = Image.new("RGB", (W, H), (250, 250, 248))
d = ImageDraw.Draw(im)


def P(x, y):
    return ((x - x0) * S, (y1 - y) * S)


def rect(b, **kw):
    d.rectangle([P(b["x"], b["y"] + b["h"]), P(b["x"] + b["w"], b["y"])], **kw)


for gx in range(int(x0) // 5 * 5, int(x1) + 1, 5):
    d.line([P(gx, y0), P(gx, y1)], fill=(225, 225, 225))
    d.text(P(gx + 0.2, y1 - 0.5), str(gx), fill=(150, 150, 150))
for gy in range(int(y0) // 5 * 5, int(y1) + 1, 5):
    d.line([P(x0, gy), P(x1, gy)], fill=(225, 225, 225))
    d.text(P(x0 + 0.2, gy + 0.6), str(gy), fill=(150, 150, 150))
for r in v["rooms"]:
    if r["floor"] == a.floor:
        rect(r["bounds"], outline=(120, 160, 220), width=2)
        d.text(P(r["bounds"]["x"] + 0.3, r["bounds"]["y"] + r["bounds"]["h"] - 0.4), f"{r['id']} e{r.get('elevation', 0)}", fill=(80, 120, 200))
        for vd in r.get("voids", []):
            rect(vd, fill=(235, 235, 235), outline=(180, 180, 180))
for l in v["links"]:
    if l["from"] == a.floor or l["to"] == a.floor:
        rect(l["bounds"], fill=(255, 240, 200), outline=(200, 150, 50))
        d.text(P(l["bounds"]["x"] + 0.2, l["bounds"]["y"] + 0.8), l["id"], fill=(160, 110, 30))
col = {"booth": (255, 200, 200), "desk": (200, 170, 120), "chair": (210, 210, 255), "stanchion": (120, 120, 255),
       "screen": (0, 160, 0), "structure": (150, 150, 150), "glazing": (120, 200, 255), "sign": (255, 160, 0),
       "signAccent": (255, 210, 120), None: (190, 190, 190), "paving": (170, 170, 170)}
for x in v["decor"]:
    if x["floor"] == a.floor and x.get("material") not in ("signAccent",):
        rect(x["bounds"], fill=col.get(x.get("material"), (200, 200, 200)))
for o in v["obstacles"]:
    if o["floor"] == a.floor and not o.get("hidden") and not o.get("linkId"):
        rect(o["bounds"], fill=(40, 40, 40) if o["bounds"]["w"] < 1.2 and o["bounds"]["h"] < 1.2 else (90, 90, 90))
cams = {}
for f in sorted((ROOT / "data/photomatch/cameras").glob("*.json")):
    cams.update(json.loads(f.read_text()))
for name, spec in cams.items():
    if "cal" not in spec:
        continue
    cal = json.loads((ROOT / "data/photomatch" / spec["cal"]).read_text())
    c = Cam(cal, spec["C"], spec.get("turns", 0))
    if abs(c.C[2] - (6.2 if a.floor else 0)) > 6:
        continue
    fwd = c.R[:, 2]
    half = math.radians(cal["fov_h"]) / 2
    ang = math.atan2(fwd[1], fwd[0])
    pts = [P(*c.C[:2])] + [P(c.C[0] + 8 * math.cos(ang + s * half), c.C[1] + 8 * math.sin(ang + s * half)) for s in (-1, 1)]
    d.polygon(pts, outline=(220, 0, 0), width=2)
    d.text(P(c.C[0] + 0.3, c.C[1] - 0.3), name.replace("inside_", "").replace("kinepolis_", "")[:22], fill=(200, 0, 0))
im.save(a.out)
print(a.out, im.size)
