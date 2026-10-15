"""Reading aid for annotating a photo: a labelled pixel grid, and (with a calibrated camera) world grids drawn into
the photo so positions can be read off in metres.

  python3 scripts/photomatch/grid.py <photo> <out.jpg> [--pix 50] [--crop x0,y0,x1,y1] [--width 1400]
      [--cal cal.json --C x,y,z --turns 0 --plane z=0 --plane x=4.5 --range -10:10 --step 1]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from pm import Cam  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("out")
    ap.add_argument("--pix", type=int, default=0, help="pixel grid spacing (photo pixels)")
    ap.add_argument("--crop")
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--cal")
    ap.add_argument("--C", default="0,0,1.6")
    ap.add_argument("--turns", type=int, default=0)
    ap.add_argument("--plane", action="append", default=[], help="axis=value, e.g. z=0 or x=4.5")
    ap.add_argument("--range", default="-30:30", help="grid extent along the plane's two axes (metres)")
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--dim", type=float, default=0.7)
    a = ap.parse_args()
    img = cv2.imread(a.photo, cv2.IMREAD_COLOR)
    H, W = img.shape[:2]
    out = (img * a.dim).astype(np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    x0, y0, x1, y1 = [int(v) for v in a.crop.split(",")] if a.crop else (0, 0, W, H)
    s = a.width / (x1 - x0)
    out = cv2.resize(out[y0:y1, x0:x1], None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)

    def P(u, v):
        return int(round((u - x0) * s)), int(round((v - y0) * s))
    if a.pix:
        for u in range((x0 // a.pix) * a.pix, x1 + 1, a.pix):
            cv2.line(out, P(u, y0), P(u, y1), (0, 200, 255), 1)
            cv2.putText(out, str(u), (P(u, y0)[0] + 2, 12), font, 0.38, (0, 220, 255), 1, cv2.LINE_AA)
        for v in range((y0 // a.pix) * a.pix, y1 + 1, a.pix):
            cv2.line(out, P(x0, v), P(x1, v), (0, 200, 255), 1)
            cv2.putText(out, str(v), (2, P(x0, v)[1] - 2), font, 0.38, (0, 220, 255), 1, cv2.LINE_AA)
    if a.cal:
        cam = Cam(a.cal, [float(v) for v in a.C.split(",")], a.turns)
        r0, r1 = [float(v) for v in a.range.split(":")]
        cols = [(80, 80, 255), (80, 255, 80), (255, 160, 60)]
        for k, pl in enumerate(a.plane):
            ax, val = pl.split("=")
            ax = "xyz".index(ax)
            val = float(val)
            others = [i for i in range(3) if i != ax]
            ts = np.arange(r0, r1 + 1e-6, a.step)
            fine = np.linspace(r0, r1, 400)
            col = cols[k % 3]
            for i, j in ((0, 1), (1, 0)):
                for t in ts:
                    X = np.zeros((len(fine), 3))
                    X[:, ax] = val
                    X[:, others[i]] = t
                    X[:, others[j]] = fine
                    rel = (X - cam.C) @ cam.R
                    ok = rel[:, 2] > 0.3
                    uv = cam.project(X)
                    pts = [P(*p) for p, o in zip(uv, ok) if o and -W < p[0] < 2 * W and -H < p[1] < 2 * H]
                    major = abs(t - round(t / (5 * a.step)) * 5 * a.step) < 1e-6
                    for p, q in zip(pts, pts[1:]):
                        cv2.line(out, p, q, col, 2 if major else 1, cv2.LINE_AA)
            # labels at grid crossings
            for t1 in ts:
                for t2 in ts:
                    if abs(t1 % (2 * a.step)) > 1e-6 or abs(t2 % (2 * a.step)) > 1e-6:
                        continue
                    X = np.zeros(3)
                    X[ax], X[others[0]], X[others[1]] = val, t1, t2
                    if ((X - cam.C) @ cam.R)[2] < 0.3:
                        continue
                    u, v = cam.project(X)[0]
                    if x0 <= u < x1 and y0 <= v < y1:
                        cv2.putText(out, f"{t1:g},{t2:g}", P(u + 2, v - 2), font, 0.33, col, 1, cv2.LINE_AA)
    cv2.imwrite(a.out, out, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == "__main__":
    main()
