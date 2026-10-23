#!/usr/bin/env python3
"""The three construction papers (John 23/10): the menu's inks with the fibre of real construction paper, and torn
scraps of them to lay under thumbnails. Source: "Construction paper backgrounds", CC0 scans by an OpenGameArt user
(https://opengameart.org/content/construction-paper-backgrounds, conppr.tar.gz), unpacked into --src.
  python3 scripts/make_paper.py --src <dir with conppr_*.jpg>   ->  site/cinema/paper/*.webp
  python3 scripts/make_paper.py --paper                          ->  site/cinema/paper/{scrap-paper-1,2,swatch-paper}.webp
(--paper: the fourth stock, the menu's bare newsprint (#EEF0EC), for talks outside the three inks; its fibre is read
back from fibre.webp, so it needs no scan. In the dark theatre these pale scraps are what a "paper" talk's tag is.)
Fibre is taken from each scan's own colour as detail around its mean (so the fibres keep their real light/dark
pattern) and laid onto the exact ink; tiles are made seamless by cross-fading with a half-offset copy.
"""
import argparse, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "site" / "cinema" / "paper"
INKS = {"pink": (0xFF, 0x48, 0xB0), "blue": (0x00, 0x78, 0xBF), "yellow": (0xFF, 0xE8, 0x00)}
SCAN = {"pink": "pink", "blue": "blue", "yellow": "yellow"}
TILE = 512


def seamless(a):
    n = a.shape[0]
    r = np.roll(np.roll(a, n // 2, 0), n // 2, 1)
    y, x = np.mgrid[0:n, 0:n] / (n - 1)
    w = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y)) * 2          # 0 at the edges, 1 in the middle
    w = np.clip(w * 2.2, 0, 1)[..., None] if a.ndim == 3 else np.clip(w * 2.2, 0, 1)
    return a * w + r * (1 - w)


def detail(src, colour):
    """the scan's fibre as a multiplier around 1 (per channel, so coloured fibres stay coloured)"""
    im = Image.open(src / f"conppr_{SCAN[colour]}.jpg").convert("RGB")
    im = im.crop((512, 512, 512 + 1024, 512 + 1024)).resize((TILE, TILE), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    low = np.asarray(im.filter(ImageFilter.GaussianBlur(24))).astype(np.float32) / 255
    d = a / np.maximum(low, 1e-3)                       # fibre around 1, the scan's own uneven lighting removed
    lum = d.mean(axis=2, keepdims=True)
    return seamless(lum * 0.75 + d * 0.25)


def tile(colour, d, strength=1.0):
    ink = np.array(INKS[colour], np.float32) / 255
    out = ink * (1 + (d - 1) * 1.6 * strength)
    return np.clip(out, 0, 1)


def noise1d(n, seed, octaves=((40, 7.0), (12, 2.6), (4, 1.0))):
    """a rough line of n samples: a few octaves of smoothed random values (period in samples, amplitude in px)"""
    rnd = random.Random(seed)
    out = np.zeros(n)
    for period, amp in octaves:
        k = n // period + 3
        pts = np.array([rnd.uniform(-1, 1) for _ in range(k)])
        xs = np.arange(n) / period
        i = xs.astype(int)
        f = xs - i
        f = f * f * (3 - 2 * f)
        out += (pts[i] * (1 - f) + pts[i + 1] * f) * amp
    return out


def scrap(colour, d, w, h, seed, torn=(True, True, True, False), pad=16):
    """a torn scrap of construction paper, w x h at 2x, with its lighter torn fringe and a few loose fibres.
    torn: which sides (top, right, bottom, left) are torn rather than cut."""
    S = 2
    W, H = w * S + 2 * pad * S, h * S + 2 * pad * S
    rnd = random.Random(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x0, y0, x1, y1 = pad * S, pad * S, W - pad * S, H - pad * S
    # each side's edge, displaced inward/outward along its length; the fringe is a second, inner edge
    def edge(nlen, i):
        if not torn[i]:
            return np.zeros(nlen), np.zeros(nlen) + 1.2 * S
        e = noise1d(nlen, seed * 7 + i, ((60 * S, 4.5 * S), (14 * S, 2.0 * S), (3 * S, 0.9 * S)))
        f = 2.6 * S + np.abs(noise1d(nlen, seed * 13 + i, ((26 * S, 3.4 * S), (7 * S, 1.8 * S), (2 * S, 0.8 * S))))
        return e, f
    top, ftop = edge(W, 0); bot, fbot = edge(W, 2); lef, flef = edge(H, 3); rig, frig = edge(H, 1)
    xi, yi = xx.astype(int), yy.astype(int)
    dt = yy - (y0 + top[xi]); db = (y1 + bot[xi]) - yy; dl = xx - (x0 + lef[yi]); dr = (x1 + rig[yi]) - xx
    dist = np.minimum(np.minimum(dt, db), np.minimum(dl, dr))                 # distance inside the outline
    fr = np.where(dist == dt, ftop[xi], np.where(dist == db, fbot[xi], np.where(dist == dl, flef[yi], frig[yi])))
    alpha = np.clip(dist + 0.5, 0, 1)
    # paper: the ink with its fibre, tiled
    dd = np.tile(d, (math.ceil(H / TILE) + 1, math.ceil(W / TILE) + 1, 1))[:H, :W]
    rgb = tile(colour, dd)
    # the torn fringe: the paper's pale core, fuzzy, fading into the ink
    # the white core shows in a band along a tear: solid near the edge, breaking up into fibres where it meets the ink
    mott = np.asarray(Image.fromarray((np.random.default_rng(seed).random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    core = np.clip((1 - dist / np.maximum(fr, 1)) * 1.6 - (mott - 0.5) * 0.9, 0, 1)
    tornmask = np.zeros_like(core)
    for i, (m, cond) in enumerate([(torn[0], dist == dt), (torn[2], dist == db), (torn[3], dist == dl), (torn[1], dist == dr)]):
        if m: tornmask = np.maximum(tornmask, cond.astype(np.float32))
    pale = np.clip(0.93 + (dd - 1) * 0.8, 0, 1) * np.array([1.0, 0.99, 0.97])
    k = (core * tornmask * 0.95)[..., None]
    rgb = rgb * (1 - k) + pale * k
    # loose fibres sticking out of the torn edges
    a = (alpha * 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([(rgb * 255).astype(np.uint8), a]), "RGBA")
    from PIL import ImageDraw
    dr_ = ImageDraw.Draw(img)
    for _ in range(int((w + h) * (0.18 if w > 60 else 0.06))):
        side = rnd.choice([i for i in range(4) if torn[i]])
        if side in (0, 2):
            x = rnd.uniform(x0, x1); yb = y0 + top[int(x)] if side == 0 else y1 + bot[int(x)]
            ang = math.radians(rnd.uniform(-60, 60) + (-90 if side == 0 else 90)); px, py = x, yb
        else:
            y = rnd.uniform(y0, y1); xb = x0 + lef[int(y)] if side == 3 else x1 + rig[int(y)]
            ang = math.radians(rnd.uniform(-60, 60) + (180 if side == 3 else 0)); px, py = xb, y
        L = rnd.uniform(1.5, 4.5) * S
        pts = [(px, py)]
        for s in range(4):
            ang += rnd.uniform(-0.5, 0.5); px += math.cos(ang) * L / 4; py += math.sin(ang) * L / 4; pts.append((px, py))
        shade = int(235 + rnd.uniform(-15, 15))
        dr_.line(pts, fill=(shade, shade, shade - 6, int(rnd.uniform(90, 200))), width=1)
    # a slight turn, like a scrap laid down by hand
    img = img.rotate(rnd.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True)
    return img


def paper_pieces():
    """newsprint scraps and a swatch, with the fibre of fibre.webp (written by the --src run: g = 0.5 + (d - 1) * 1.4)"""
    g = np.asarray(Image.open(OUT / "fibre.webp").convert("L")).astype(np.float32) / 255
    d = np.repeat((1 + (g - 0.5) / 1.4 * 0.5)[..., None], 3, axis=2)   # half strength: on near-white the full fibre reads as blotches
    INKS["paper"] = (0xEE, 0xF0, 0xEC)
    for n, (w, h, seed, torn) in enumerate([(180, 104, 3, (True, True, True, False)), (180, 104, 11, (True, False, True, True))]):
        scrap("paper", d, w, h, seed + 5, torn).save(OUT / f"scrap-paper-{n + 1}.webp", quality=88, method=6)
    scrap("paper", d, 24, 24, 10, (True, True, True, True)).save(OUT / "swatch-paper.webp", quality=90, method=6)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src"); ap.add_argument("--paper", action="store_true"); a = ap.parse_args()
    if a.paper:
        paper_pieces()
        return
    if not a.src: ap.error("--src is needed (or --paper)")
    src = Path(a.src); OUT.mkdir(parents=True, exist_ok=True)
    for c in INKS:
        d = detail(src, c)
        Image.fromarray((tile(c, d) * 255).astype(np.uint8)).save(OUT / f"{c}.webp", quality=82, method=6)
        # thumbnails are 16:9; scraps a little larger, two shapes per ink so neighbours differ
        for n, (w, h, seed, torn) in enumerate([(180, 104, 3, (True, True, True, False)), (180, 104, 11, (True, False, True, True))]):
            scrap(c, d, w, h, seed + len(c), torn).save(OUT / f"scrap-{c}-{n + 1}.webp", quality=88, method=6)
        # a small swatch: a torn square for keys and markers
        scrap(c, d, 24, 24, 5 + len(c), (True, True, True, True), pad=5).save(OUT / f"swatch-{c}.webp", quality=90, method=6)
    # the fibre alone, neutral, for light fields (soft-light over any colour)
    d = detail(src, "blue").mean(axis=2)
    g = np.clip(0.5 + (d - 1) * 1.4, 0, 1)
    Image.fromarray((g * 255).astype(np.uint8), "L").save(OUT / "fibre.webp", quality=80, method=6)
    for f in sorted(OUT.iterdir()):
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
