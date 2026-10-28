"""Turn render folders from build_scene.py into the cinema page's media (site/media/).

    python3 scripts/blender/publish_renders.py /mnt/c/Users/wilkojo/kino-renders/final [more folders...]

- Stills (hall, hall-phone, seat-<n>, seat-phone-<n>) become JPEGs; their -front layers (what stands in front of
  the cinema screen, on transparency) become WebP.
- Phase-1 clips declare ordered parts in shots-<room>.json. Join at the identical shared
  boundary, retaining that frame once. Intros and independent return clips use the same encoder.
  No cuts, fades, repairs, reversal or legacy path publishing.
- A clip newer than its frames (and this script) is not encoded again.
- shots-<n>.json files are merged into media/shots.json, so rooms rendered on different nights add up.
- A folder with laptop.json (build_laptop.py) gives laptop-open/-closed.webp, laptop-anim-<i>.webp and shots["laptop"].
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import os
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "site" / "media"
OUT.mkdir(parents=True, exist_ok=True)
existing = OUT / "shots.json"
shots = json.loads(existing.read_text()) if existing.exists() else {}
srcs = [Path(p) for p in sys.argv[1:]]

def place_inner(old, new):
    """Where the walk's 16:9 frame (old: a seat shot without px) sits inside a wide seat still (new), from where the
    same screen lands in both: same camera, so the old picture is the new one scaled and shifted."""
    (ox0, oy0), (ox1, oy1) = old["overlay"]["screen"][2], old["overlay"]["screen"][0]
    (nx0, ny0), (nx1, ny1) = new["overlay"]["screen"][2], new["overlay"]["screen"][0]
    sx, sy = (nx1 - nx0) / (ox1 - ox0), (ny1 - ny0) / (oy1 - oy0)
    x0, y0 = nx0 - ox0 * sx, ny0 - oy0 * sy
    new["inner"] = [round(x0, 5), round(y0, 5), round(x0 + sx, 5), round(y0 + sy, 5)]


for src in srcs:
    for f in sorted(src.glob("shots-*.json")):
        incoming = json.loads(f.read_text())
        for k, v in incoming.items():
            if k.startswith("seat-") and v.get("px") and k in shots and not shots[k].get("px"):
                place_inner(shots[k], v)
            elif k.startswith("seat-") and v.get("px") and shots.get(k, {}).get("inner") and not v.get("inner_measured"):
                v["inner"] = shots[k]["inner"]          # measured before; the formula's guess is off
            v.pop("inner_measured", None)
        shots.update(incoming)
    for png in sorted(src.glob("*.png")):
        if png.stem.endswith("-front"):         # what stands in front of the screen: keeps its transparency
            Image.open(png).save(OUT / f"{png.stem}.webp", quality=88, method=6)
            print(f"{png.stem}.webp")
        elif png.stem == "hall" or png.stem.startswith(("hall-", "seat-", "door-")):
            Image.open(png).convert("RGB").save(OUT / f"{png.stem}.jpg", quality=86, optimize=True, progressive=True)
            print(f"{png.stem}.jpg")


def frames_of(name):
    for src in srcs:
        d = src / name
        if d.is_dir() and any(d.glob("f_*.png")):
            return sorted(d.glob("f_*.png"))
    return []


ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
def fresh(out, frame_lists):
    newest = max([Path(__file__).stat().st_mtime] + [p.stat().st_mtime for fl in frame_lists for p in fl])
    return out.exists() and out.stat().st_mtime > newest


def complete_frames(name, expected):
    frames = frames_of(name)
    wanted = [f"f_{i:05d}.png" for i in range(expected)]
    if [p.name for p in frames] != wanted:
        print(f"SKIP {name}: incomplete sequence ({len(frames)}/{expected}); previews are not publishable")
        return None
    return frames


for key, info in sorted(list(shots.items())):
    if info.get("pipeline") != 2 or not info.get("parts"):
        continue
    lists = []
    for part in info["parts"]:
        frames = complete_frames(part, shots[part]["frames"])
        if frames is None:
            break
        lists.append(frames)
    else:
        out = OUT / f"{key}.mp4"
        if fresh(out, lists):
            continue
        # Adjacent parts include the same boundary frame. Drop only that duplicate.
        seq = lists[0] + [p for frames in lists[1:] for p in frames[1:]]
        if len(seq) != info["frames"]:
            raise ValueError(f"{key}: manifest count {info['frames']} != sequence {len(seq)}")
        with tempfile.TemporaryDirectory() as tmp:
            for i, source in enumerate(seq):
                destination = Path(tmp) / f"f_{i:05d}.png"
                try:
                    os.symlink(source.resolve(), destination)
                except OSError:
                    shutil.copyfile(source, destination)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(info["fps"]),
                            "-i", str(Path(tmp) / "f_%05d.png"), *ENC, str(out)], check=True)
        print(f"{key}.mp4 ({len(seq)} frames, continuous join)")

# the laptop on your lap (build_laptop.py): open and closed stills and the frames between, on transparency
for src in srcs:
    lj = src / "laptop.json"
    if not lj.exists():
        continue
    shots["laptop"] = json.loads(lj.read_text())
    for name in ("laptop-open", "laptop-closed"):
        if (src / f"{name}.png").exists():
            Image.open(src / f"{name}.png").save(OUT / f"{name}.webp", quality=90, method=6)
            print(f"{name}.webp")
    for i, f in enumerate(sorted((src / "anim").glob("f_*.png"))):
        Image.open(f).save(OUT / f"laptop-anim-{i:02d}.webp", quality=80, method=6)
    print(f"laptop: {shots['laptop'].get('frames', 0)} frames")

existing.write_text(json.dumps(shots, indent=1))
print(f"shots.json: {', '.join(sorted(shots))}")
