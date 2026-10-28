#!/usr/bin/env python3
"""Check the seams between the page's stills and its walks (John 19/10: going between a still and a walk must feel
seamless). Each published laptop clip's first and last frames against the still the page shows there, cropped to the
still's "inner" box (the walk's frame inside the wider still, shots.json) and scaled to the clip's size:
  intro: last -> hall;  walk-N: first -> hall, last -> seat-N;  back-N: first -> seat-N, last -> hall.
Prints per seam the mean difference (0-255) and the share of pixels that differ visibly (> 24 after a 2 px blur, so
codec noise doesn't count), and writes still | frame | difference sheets for the failures.
  python3 scripts/photomatch/seams.py [--out DIR] [--all-sheets]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MEDIA = Path(__file__).resolve().parents[2] / "site" / "media"
MEAN_MAX, SHARE_MAX = 3.0, 0.005           # a seam passes below both

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/mnt/c/Users/wilkojo/kino-renders/photomatch/seams")
ap.add_argument("--all-sheets", action="store_true")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
shots = json.loads((MEDIA / "shots.json").read_text())


def clip_file(key):
    for name in (f"{key}.mp4", f"{key}.hevc.mp4", f"{key}.av1.mp4"):
        if (MEDIA / name).exists():
            return MEDIA / name


def frame(key, last):
    """the clip's first or last frame as the browser decodes it"""
    with tempfile.TemporaryDirectory() as t:
        png = Path(t) / "f.png"
        pre = ["-sseof", "-0.5"] if last else []
        post = ["-update", "1"] if last else ["-frames:v", "1"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *pre, "-i", str(clip_file(key)), *post, str(png)], check=True)
        return Image.open(png).convert("RGB")


def still(key, size):
    im = Image.open(MEDIA / f"{key}.jpg").convert("RGB")
    x0, y0, x1, y1 = shots[key].get("inner", [0, 0, 1, 1])
    w, h = im.size
    return im.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h))).resize(size, Image.LANCZOS)


def compare(name, clip, last, still_key):
    f = frame(clip, last)
    s = still(still_key, f.size)
    d = np.abs(np.asarray(f.filter(ImageFilter.GaussianBlur(2)), float)
               - np.asarray(s.filter(ImageFilter.GaussianBlur(2)), float)).max(axis=2)
    mean, share = d.mean(), (d > 24).mean()
    ok = mean < MEAN_MAX and share < SHARE_MAX
    print(f"{'ok  ' if ok else 'SEAM'} {name:28s} mean {mean:5.2f}  visibly different {share * 100:5.2f}%")
    if not ok or a.all_sheets:
        diff = Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).convert("RGB")
        sheet = Image.new("RGB", (f.width * 3, f.height))
        for i, im in enumerate((s, f, diff)):
            sheet.paste(im, (i * f.width, 0))
        sheet.resize((sheet.width // 2, sheet.height // 2)).save(out / f"{name}.jpg", quality=85)
    return ok


seams, old = [], []
for v, hall, room in (("", "hall", "seat-{}"), ("-phone", "hall-phone", "door-phone-{}")):
    clips = [(f"intro{v}", (None, hall))]
    clips += [(c, e) for n in range(3, 11) for c, e in ((f"walk{v}-{n}", (hall, room.format(n))),
                                                        (f"back{v}-{n}", (room.format(n), hall)))]
    for clip, (start, end) in clips:
        if not (shots.get(clip, {}).get("kind") == "clip" and clip_file(clip)):
            continue
        if "codecs" not in shots[clip]:           # a walk from before the photo-matched venue, still to be replaced
            old.append(clip)
            continue
        seams += [(f"{clip}-start", clip, False, start)] if start else []
        seams += [(f"{clip}-end", clip, True, end)]
bad = [s[0] for s in seams if not compare(*s)]
if old:
    print(f"not checked (old walks, not rendered in the photo-matched venue yet): {' '.join(old)}")
print(f"{len(seams) - len(bad)} of {len(seams)} seams ok" + (f"; sheets for the others in {out}" if bad else ""))
sys.exit(1 if bad else 0)
