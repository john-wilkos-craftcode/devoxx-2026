"""Draw the venue plan's boxes (booths, columns, walls, steps) as wireframes into a reference photo from its solved
camera: shows at a glance whether the plan's layout and the camera agree with what the photo shows.
  python3 scripts/photomatch/plan_overlay.py <camera name> <out.jpg> [--floor 0] [--booth-h 2.5]"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from pm import Cam  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cam")
ap.add_argument("out")
ap.add_argument("--floor", type=int, default=0)
ap.add_argument("--booth-h", type=float, default=2.5)
ap.add_argument("--width", type=int, default=1600)
a = ap.parse_args()
cams = {}
for f in sorted((ROOT / "data/photomatch/cameras").glob("*.json")):
    cams.update(json.loads(f.read_text()))
spec = cams[a.cam]
cam = Cam(json.loads((ROOT / "data/photomatch" / spec["cal"]).read_text()), spec["C"], spec.get("turns", 0))
img = cv2.imread(str(ROOT / "data/references" / spec["photo"]))
s = a.width / img.shape[1]
img = cv2.resize((img * 0.75).astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
v = json.loads((ROOT / "data/venue/venue.json").read_text())["venue"]


def seg(p, q, col, w=1):
    P = np.array([p, q], float)
    rel = (P - cam.C) @ cam.R
    if (rel[:, 2] < 0.2).all():
        return
    if rel[0, 2] < 0.2 or rel[1, 2] < 0.2:          # clip to the near plane
        t = (0.2 - rel[0, 2]) / (rel[1, 2] - rel[0, 2])
        X = P[0] + t * (P[1] - P[0])
        P = np.array([X, P[1]]) if rel[0, 2] < 0.2 else np.array([P[0], X])
    uv = cam.project(P) * s
    if np.abs(uv).max() > 1e5:
        return
    cv2.line(img, tuple(int(c) for c in uv[0]), tuple(int(c) for c in uv[1]), col, w, cv2.LINE_AA)


def boxw(b, z0, z1, col, w=1):
    x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i in range(4):
        (xa, ya), (xb, yb) = c[i], c[(i + 1) % 4]
        seg((xa, ya, z0), (xb, yb, z0), col, w)
        seg((xa, ya, z1), (xb, yb, z1), col, w)
        seg((xa, ya, z0), (xa, ya, z1), col, w)


base = 6.2 if a.floor == 1 else 0.0
for o in v["obstacles"]:
    if o["floor"] != a.floor or o.get("hidden"):
        continue
    b = o["bounds"]
    col = (0, 255, 255) if b["w"] < 1.2 and b["h"] < 1.2 else (0, 200, 0)
    z0 = base + o.get("base", 0)
    boxw(b, z0, z0 + min(o["height"], 3.4), col, 2 if col[1] == 255 and col[0] == 0 else 1)
for x in v["decor"]:
    if x["floor"] == a.floor and x.get("material") == "booth":
        boxw(x["bounds"], base, base + a.booth_h, (255, 80, 255), 2)
cv2.imwrite(a.out, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(a.out)
