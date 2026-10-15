"""Check the unified model against the venue plan: on a top-down cut of the model (render.sh venue --plan=...), draw
the plan's columns and walls (red outlines), booth footprints (magenta), the hall steps (orange) and the walk (cyan).
Where the model's grey shapes and the red outlines disagree, the model is off the plan.

  python3 scripts/photomatch/plan_check.py <plan-cut.png> x0,y0,x1,y1,cut_z,ppm <out.png>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
src, box, out = sys.argv[1], [float(v) for v in sys.argv[2].split(",")], sys.argv[3]
x0, y0, x1, y1, cut = box[:5]
ppm = box[5] if len(box) > 5 else 10
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
v = json.loads((ROOT / "data/venue/venue.json").read_text())["venue"]


def P(x, y):
    return ((x - x0) * ppm, (y1 - y) * ppm)


def rect(b, **kw):
    d.rectangle([P(b["x"], b["y"] + b["h"]), P(b["x"] + b["w"], b["y"])], **kw)


for o in v["obstacles"]:
    if o["floor"] == 0 and not o.get("hidden") and not o.get("linkId"):
        rect(o["bounds"], outline=(230, 0, 0), width=1)
for x in v["decor"]:
    if x["floor"] == 0 and x.get("material") == "booth":
        rect(x["bounds"], outline=(230, 0, 230), width=1)
for l in v["links"]:
    if l["from"] == 0 and l["to"] == 0 or l["id"] == "grand-stair":
        rect(l["bounds"], outline=(255, 140, 0), width=1)
w = json.loads((ROOT / "data/photomatch/walk.json").read_text())
pts = [P(*p) for p in w["points"]]
d.line(pts, fill=(0, 200, 255), width=3)
for p in pts:
    d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=(0, 200, 255))
sx, sy, _ = w["screen"]
d.rectangle([P(sx - 1.8, sy + 0.15), P(sx + 1.8, sy - 0.15)], fill=(0, 160, 0))
for gx in range(int(x0) // 10 * 10, int(x1) + 1, 10):
    d.text(P(gx + 0.3, y1 - 0.3), str(gx), fill=(0, 0, 160))
for gy in range(int(y0) // 10 * 10, int(y1) + 1, 10):
    d.text(P(x0 + 0.3, gy + 0.8), str(gy), fill=(0, 0, 160))
im.save(out)
print(out)
