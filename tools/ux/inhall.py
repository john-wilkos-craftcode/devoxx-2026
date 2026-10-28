#!/usr/bin/env python3
"""Put a main-menu screenshot where it really lives: on the schedule screen in the rendered hall, with the plants and
ivy of the still's front layer in front of it, framed as a 16:9 laptop window sees it (the still's "inner" part).
The phone canvas goes on the totem in the phone still. Pixels only: no browser, so it shows what the 3D page shows.
  python3 tools/ux/inhall.py <menu.png> <out.png> [--phone] [--glow]
<menu.png> is the #menu canvas (980x613, or 340x690 with --phone), e.g. tools/ux/shot.mjs's 1-rest.png / 5-phone.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "site/media"


def coeffs(dst, src):
    """PIL perspective coefficients mapping output (dst) points to input (src) points"""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    phone = "--phone" in sys.argv
    menu_png, out_png = Path(args[0]), Path(args[1])
    shots = json.loads((MEDIA / "shots.json").read_text())
    key = "hall-phone" if phone else "hall"
    still = Image.open(MEDIA / f"{key}.jpg").convert("RGB")
    W, H = still.size
    bl, br, tr, tl = [(x * W, y * H) for x, y in shots[key]["overlay"]["programme"]]
    menu = Image.open(menu_png).convert("RGB")
    mw, mh = menu.size
    warped = menu.transform((W, H), Image.PERSPECTIVE, coeffs([tl, tr, br, bl], [(0, 0), (mw, 0), (mw, mh), (0, mh)]),
                            Image.BICUBIC)
    mask = Image.new("L", (mw, mh), 255).transform((W, H), Image.PERSPECTIVE,
                                                   coeffs([tl, tr, br, bl], [(0, 0), (mw, 0), (mw, mh), (0, mh)]), Image.BICUBIC)
    out = still.copy()
    if "--glow" in sys.argv:                      # a screen lights the wall round it a little (the real page doesn't)
        glow = warped.filter(ImageFilter.GaussianBlur(40))
        out = Image.blend(out, Image.composite(glow, out, mask.filter(ImageFilter.GaussianBlur(60))), 0.25)
    out.paste(warped, (0, 0), mask)
    front = MEDIA / f"{shots[key].get('front', key + '-front')}.webp"
    if front.exists():
        f = Image.open(front).convert("RGBA").resize((W, H))
        out = Image.alpha_composite(out.convert("RGBA"), f).convert("RGB")
    x0, y0, x1, y1 = shots[key].get("inner", [0, 0, 1, 1])
    out = out.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    if not phone:
        out = out.resize((1920, 1080), Image.LANCZOS)
    out.save(out_png, quality=92)
    print(f"{out_png}  {out.size[0]}x{out.size[1]}  (screen {round(tr[0] - tl[0])}x{round(bl[1] - tl[1])} px in the still)")


main()
