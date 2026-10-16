"""Frame-sequence quality check for a rendered walk (the automatic half of BRIEF.md's EEVEE rubric).

  python3 scripts/photomatch/qc.py <frames dir> [--png out.png]

Per frame, on a 320 px wide grey copy:
  pop      a cut-like jump: the change from the previous frame is far above the change around it (an object or a crowd
           member switching visibility on screen, a light popping, a texture swapping)
  noise    sample noise left in the frame: Immerkaer's estimate (the image convolved with a mask that cancels smooth
           shading and edges to first order, sigma from its mean absolute value; J. Immerkaer, "Fast Noise Variance
           Estimation", CVIU 1996), on the full-size grey frame, 0-255
  breathing  the median over the frame of each pixel against the mean of its neighbours' (signed, 320 px grey):
           lighting that flickers frame to frame (GI or shadow maps re-solving, exposure) shifts every pixel the same
           way and moves the median; smooth camera motion and things leaving the frame don't
  clip     share of pixels blown out (any channel >= 254) and crushed (all channels <= 2)
Prints a summary and the worst frames; exits 1 if any rubric threshold fails.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

POP_RATIO = 3.0           # a frame's change vs the median change of the 10 frames around it
POP_MIN = 4.0             # ...and at least this much mean change (0-255 grey), so a still scene's noise isn't a pop
NOISE_MAX = 1.5           # Immerkaer sigma (0-255 grey), worst frame
BREATH_MAX = 1.0          # mean-brightness second difference (0-255 grey), worst frame
BLOWN_MAX = 0.02          # blown-out share per frame (screens and practical lights are allowed a little)
CRUSHED_MAX = 0.25        # crushed share per frame (a dark venue: the ceiling is nearly black by design)

ap = argparse.ArgumentParser()
ap.add_argument("frames")
ap.add_argument("--png")
a = ap.parse_args()
files = sorted(Path(a.frames).glob("*.png"))
if len(files) < 3:
    sys.exit(f"QC: only {len(files)} frames in {a.frames}")
grey, blown, crushed, noise = [], [], [], []
K = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)
for f in files:
    im = Image.open(f).convert("RGB")
    rgb = np.asarray(im)
    blown.append(float((rgb >= 254).any(-1).mean()))
    crushed.append(float((rgb <= 2).all(-1).mean()))
    w, h = im.size
    g = np.asarray(im.convert("L"), dtype=np.float32)
    conv = sum(K[i, j] * g[i:h - 2 + i, j:w - 2 + j] for i in range(3) for j in range(3))
    noise.append(float(np.sqrt(np.pi / 2) / (6 * (w - 2) * (h - 2)) * np.abs(conv).sum()))
    grey.append(np.asarray(im.convert("L").resize((320, round(320 * h / w)), Image.BILINEAR), dtype=np.float32))
G = np.stack(grey)
d = np.abs(np.diff(G, axis=0)).mean((1, 2))                     # change from frame i to i + 1
pops = []
for i in range(len(d)):
    ctx = np.concatenate([d[max(0, i - 5):i], d[i + 1:i + 6]])
    if len(ctx) and d[i] > POP_MIN and d[i] > POP_RATIO * max(np.median(ctx), 0.5):
        pops.append((files[i + 1].stem, round(float(d[i]), 1), round(float(np.median(ctx)), 1)))
breath = np.abs(np.median((G[1:-1] - (G[:-2] + G[2:]) / 2).reshape(len(G) - 2, -1), axis=1))
noise = np.array(noise)
fails = []
if pops:
    fails.append(f"{len(pops)} pops")
if noise.max() > NOISE_MAX:
    fails.append(f"noise {noise.max():.2f} > {NOISE_MAX} ({int((noise > NOISE_MAX).sum())} frames)")
if breath.max() > BREATH_MAX:
    fails.append(f"breathing {breath.max():.2f} > {BREATH_MAX}")
nb = sum(b > BLOWN_MAX for b in blown)
nc = sum(c > CRUSHED_MAX for c in crushed)
if nb:
    fails.append(f"{nb} frames blown > {BLOWN_MAX:.0%}")
if nc:
    fails.append(f"{nc} frames crushed > {CRUSHED_MAX:.0%}")
print(f"QC {a.frames}: {len(files)} frames ({files[0].stem}..{files[-1].stem})")
print(f"QC change per frame: median {np.median(d):.1f}, max {d.max():.1f}")
print(f"QC noise: median {np.median(noise):.2f}, max {noise.max():.2f} ({files[int(np.argmax(noise))].stem}); "
      f"breathing: median {np.median(breath):.2f}, max {breath.max():.2f} ({files[int(np.argmax(breath)) + 1].stem})")
print(f"QC blown: max {max(blown):.2%} ({files[int(np.argmax(blown))].stem}); crushed: max {max(crushed):.1%} "
      f"({files[int(np.argmax(crushed))].stem})")
for p in pops[:12]:
    print(f"QC pop at {p[0]}: change {p[1]} vs {p[2]} around it")
print("QC " + ("PASS" if not fails else "FAIL: " + "; ".join(fails)))
if a.png:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    ax[0].plot(d); ax[0].set_ylabel("change")
    ax[1].plot(noise, label="noise"); ax[1].plot(range(1, len(breath) + 1), breath, label="breathing"); ax[1].legend()
    ax[2].plot(blown, label="blown"); ax[2].plot(crushed, label="crushed"); ax[2].legend()
    fig.savefig(a.png, dpi=80)
sys.exit(1 if fails else 0)
