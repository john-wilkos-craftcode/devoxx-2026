"""Lay each render of an area over its reference photo: photo, render, 50/50 blend and an edge overlay (photo
edges cyan, render edges magenta, white where they agree), plus one sheet of all four to look at.

  python3 scripts/photomatch/compare.py <area> [cam ...]

Prints, per camera, how far the render's edges sit from the photo's (median and 75th percentile in pixels at
1280 wide): render edges with nothing in the photo near them are what is wrong or missing.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path("/mnt/c/Users/wilkojo/kino-renders/photomatch")
W = 1280


def edges(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    v = np.median(g)
    return cv2.Canny(g, max(10, 0.5 * v), min(255, max(40, 1.2 * v)))


def label(img, text):
    cv2.rectangle(img, (0, 0), (12 + 9 * len(text), 22), (0, 0, 0), -1)
    cv2.putText(img, text, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 255), 1, cv2.LINE_AA)
    return img


def compare(area, name, spec):
    render_p = OUT / area / f"{name}.png"
    if not render_p.exists():
        return None
    photo = cv2.imread(str(ROOT / "data" / "references" / spec["photo"]), cv2.IMREAD_COLOR)
    render = cv2.imread(str(render_p), cv2.IMREAD_COLOR)
    h = round(W * photo.shape[0] / photo.shape[1])
    photo = cv2.resize(photo, (W, h), interpolation=cv2.INTER_AREA)
    render = cv2.resize(render, (W, h), interpolation=cv2.INTER_AREA)
    for x0, y0, x1, y1 in spec.get("mask", []):               # UI chrome in screenshots: show the render there
        s = W / spec.get("photo_w", W)
        photo[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = render[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)]
    blend = cv2.addWeighted(photo, 0.5, render, 0.5, 0)
    ep, er = edges(photo), edges(render)
    ov = (cv2.cvtColor(render, cv2.COLOR_BGR2GRAY) * 0.35).astype(np.uint8)
    ov = cv2.cvtColor(ov, cv2.COLOR_GRAY2BGR)
    ov[ep > 0] = (255, 255, 0)
    ov[er > 0] = (255, 0, 255)
    near = cv2.dilate(ep, np.ones((5, 5), np.uint8))
    ov[(er > 0) & (near > 0)] = (255, 255, 255)
    dist = cv2.distanceTransform(255 - ep, cv2.DIST_L2, 3)
    d = dist[er > 0]
    score = (float(np.median(d)), float(np.percentile(d, 75))) if d.size else (0.0, 0.0)
    cmp_dir = OUT / area / "cmp"
    cmp_dir.mkdir(exist_ok=True)
    for kind, im in (("photo", photo), ("render", render), ("blend", blend), ("edges", ov)):
        cv2.imwrite(str(cmp_dir / f"{name}-{kind}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
    half = lambda im, t: label(cv2.resize(im, (W // 2, h // 2), interpolation=cv2.INTER_AREA), t)  # noqa: E731
    sheet = np.vstack([np.hstack([half(photo, "photo"), half(render, "render")]),
                       np.hstack([half(blend, "blend"), half(ov, "edges: photo cyan, render magenta")])])
    cv2.imwrite(str(cmp_dir / f"{name}-sheet.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"{name}: render edges from photo edges median {score[0]:.1f}px, p75 {score[1]:.1f}px -> {cmp_dir / (name + '-sheet.jpg')}")
    return score


def main():
    area = sys.argv[1]
    cams = {k: v for f in sorted((ROOT / "data" / "photomatch" / "cameras").glob("*.json")) for k, v in json.loads(f.read_text()).items()}
    names = sys.argv[2:] or [k for k, v in cams.items() if v["area"] == area and "photo" in v]
    for n in names:
        compare(area, n, cams[n])


if __name__ == "__main__":
    main()
