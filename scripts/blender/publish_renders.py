"""Turn render folders from build_scene.py into the cinema page's media (site/cinema/media/).

    python3 scripts/blender/publish_renders.py /mnt/c/Users/wilkojo/kino-renders/final [more folders...]

- Stills (hall, hall-phone, seat-<n>, seat-phone-<n>) become JPEGs; their -front layers (what stands in front of
  the cinema screen, on transparency) become WebP.
- The walk is rendered in two halves: walk-a-<side> (the hall to the top of that side's stair, shared by its rooms)
  and walk-b-<n> (the corridor and the room). They are joined into walk-<n>.mp4 with a short dip to black where the
  stair climb was (its camera tumbles: an euler wrap under motion blur) and without the rest at the top. Smeared
  frames elsewhere (the same wrap, or a whip pan) are replaced by a blend of the good frames either side (see mend).
  The way back is a fade on the page, not a clip. H.264, yuv420p, faststart.
- Phones have their own portrait walk: phone-a-<side> (leaving the hall totem) and phone-b-<n> (a push-in on the
  room's door totem), joined the same way into walk-phone-<n>.mp4.
- A clip newer than its frames (and this script) is not encoded again.
- shots-<n>.json files are merged into media/shots.json, so rooms rendered on different nights add up.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "site" / "cinema" / "media"
OUT.mkdir(parents=True, exist_ok=True)
existing = OUT / "shots.json"
shots = json.loads(existing.read_text()) if existing.exists() else {}
srcs = [Path(p) for p in sys.argv[1:]]

for src in srcs:
    for f in sorted(src.glob("shots-*.json")):
        shots.update(json.loads(f.read_text()))
    for png in sorted(src.glob("*.png")):
        if png.stem.endswith("-front"):         # what stands in front of the screen: keeps its transparency
            Image.open(png).save(OUT / f"{png.stem}.webp", quality=88, method=6)
            print(f"{png.stem}.webp")
        elif png.stem in ("hall", "hall-phone") or png.stem.startswith(("seat-", "door-")):
            Image.open(png).convert("RGB").save(OUT / f"{png.stem}.jpg", quality=86, optimize=True, progressive=True)
            print(f"{png.stem}.jpg")


def frames_of(name):
    for src in srcs:
        d = src / name
        if d.is_dir() and any(d.glob("f_*.png")):
            return sorted(d.glob("f_*.png"))
    return []


ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
CUT_A = {"west": 43, "east": 37}     # last frame of walk-a before the stair climb
SKIP_B = 8                           # walk-b starts at rest at the top of the stair: drop the slow start
DIP = (6, 4, 6)                      # frames fading out, black, fading in


def mend(ims):
    """Replace smeared frames by a blend of the good frames either side. Two kinds, both from the camera's yaw:
    - a wrap past ±180° that motion blur draws as a full spin: one to three frames that are blurred across the
      frame and out of line with their neighbours (the frames either side are close to each other);
    - a whip pan (rooms 3 and 10 turn round at the top of the stair): a few frames blurred to under 60% of the
      sharpness around them. Blending these makes a short dissolve instead.
    And one not from the yaw: brushing past the door's portal or leaf."""
    grey = [np.asarray(im.convert("L").resize((640, 360)), dtype=np.float32) for im in ims]
    gx = np.array([np.abs(np.diff(g, axis=1)).mean() for g in grey])         # detail across the frame: what a yaw smear blurs
    small = [g[::4, ::4] for g in grey]
    d = lambda i, j: float(np.abs(small[i] - small[j]).mean())
    ratio = {}
    for i in range(len(ims)):
        around = np.r_[gx[max(0, i - 6):max(0, i - 2)], gx[i + 3:i + 7]]     # skip the near neighbours: smears come in runs
        if len(around) >= 3 and gx[i] < 0.85 * np.median(around):
            ratio[i] = gx[i] / np.median(around)
    runs = []
    for i in sorted(ratio):
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    bad = set()
    for r in runs:
        a, b = r[0] - 1, r[-1] + 1
        if a < 0 or b >= len(ims):
            continue
        out_of_line = len(r) <= 3 and sum(d(k, k + 1) for k in range(a, b)) > 3.5 * d(a, b) + 3
        whip = len(r) <= 8 and min(ratio[i] for i in r) < 0.6
        # the doorway: a frame or two where the camera brushes the portal or a door leaf (a flash of red or black)
        brush = len(r) <= 2 and min(ratio[i] for i in r) < 0.8 and sum(d(k, k + 1) for k in range(a, b)) > 1.3 * d(a, b)
        if out_of_line or whip or brush:
            bad.update(r)
    # and any single frame far out of line with its neighbours, blurred or not
    bad.update(i for i in range(1, len(ims) - 1) if d(i - 1, i) + d(i, i + 1) > 2 * d(i - 1, i + 1) + 6)
    out = list(ims)
    for i in sorted(bad):
        lo, hi = i - 1, i + 1
        while lo in bad and lo > 0:
            lo -= 1
        while hi in bad and hi < len(ims) - 1:
            hi += 1
        out[i] = Image.blend(ims[lo], ims[hi], (i - lo) / (hi - lo))
    return out, sorted(bad)

def dip_join(ims_a, ims_b, out, fps):
    """Join two halves with a short dip to black and encode them to out."""
    black = Image.new("RGB", ims_a[0].size)
    fo, bl, fi = DIP
    for k in range(fo):
        ims_a[-fo + k] = Image.blend(ims_a[-fo + k], black, (k + 1) / (fo + 1))
    for k in range(fi):
        ims_b[k] = Image.blend(black, ims_b[k], (k + 1) / (fi + 1))
    seq = ims_a + [black] * bl + ims_b
    with tempfile.TemporaryDirectory() as tmp:
        for i, im in enumerate(seq):
            im.save(Path(tmp) / f"f_{i:04d}.png", compress_level=1)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(tmp) / "f_%04d.png"), *ENC,
                        str(out)], check=True)
    return len(seq)


def fresh(out, *frame_lists):
    """out is newer than every frame it is made from (and this script): skip it."""
    newest = max([Path(__file__).stat().st_mtime] + [p.stat().st_mtime for fl in frame_lists for p in fl])
    return out.exists() and out.stat().st_mtime > newest


for key, info in sorted(shots.items()):
    if key.startswith("walk-b-"):          # laptops: the landscape walk to the seat
        n = key.split("-")[-1]
        a, b = frames_of(f"walk-a-{info['side']}"), frames_of(key)
        if not a or not b:
            continue
        a, b, out = a[:CUT_A[info["side"]]], b[SKIP_B:], OUT / f"walk-{n}.mp4"
        (OUT / f"walk-{n}-back.mp4").unlink(missing_ok=True)
        if fresh(out, a, b) and f"walk-{n}" in shots:
            continue
        ims_a, bad_a = mend([Image.open(p).convert("RGB") for p in a])
        ims_b, bad_b = mend([Image.open(p).convert("RGB") for p in b])
        frames = dip_join(ims_a, ims_b, out, info.get("fps", 30))
        # where the old phone walk stopped (the door), counted in the joined clip; kept for rooms without a phone walk
        door = len(a) + DIP[1] + info["door_frame"] - SKIP_B if info.get("door_frame") is not None else None
        shots[f"walk-{n}"] = {"kind": "clip", "frames": frames, "fps": info.get("fps", 30), "door_frame": door}
        print(f"walk-{n}.mp4 ({len(a)} + {DIP[1]} + {len(b)} frames, mended {bad_a} + {[SKIP_B + i for i in bad_b]})")
    elif key.startswith("phone-b-"):       # phones: their own portrait walk, the hall totem to the door totem
        n = key.split("-")[-1]
        a, b, out = frames_of(f"phone-a-{info['side']}"), frames_of(key), OUT / f"walk-phone-{n}.mp4"
        if len(a) < shots[f"phone-a-{info['side']}"]["frames"] or len(b) < info["frames"]:
            continue                       # not (fully) rendered yet
        if fresh(out, a, b) and f"walk-phone-{n}" in shots:
            continue
        frames = dip_join([Image.open(p).convert("RGB") for p in a], [Image.open(p).convert("RGB") for p in b], out, info["fps"])
        shots[f"walk-phone-{n}"] = {"kind": "clip", "frames": frames, "fps": info["fps"]}
        print(f"walk-phone-{n}.mp4 ({len(a)} + {DIP[1]} + {len(b)} frames)")

existing.write_text(json.dumps(shots, indent=1))
print(f"shots.json: {', '.join(sorted(shots))}")
