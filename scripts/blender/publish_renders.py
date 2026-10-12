"""Turn render folders from build_scene.py into the cinema page's media (site/cinema/media/).

    python3 scripts/blender/publish_renders.py /mnt/c/Users/wilkojo/kino-renders/final [more folders...]

- Stills (hall, hall-phone, seat-<n>, seat-phone-<n>) become JPEGs; their -front layers (what stands in front of
  the cinema screen, on transparency) become WebP.
- The walk is rendered in two halves: walk-a-<side> (the hall to the top of that side's stair, shared by its rooms)
  and walk-b-<n> (the corridor and the room). They meet at rest, so they are joined into walk-<n>.mp4, and the
  same frames played backwards make walk-<n>-back.mp4 for the way out. H.264, yuv420p, faststart.
- shots-<n>.json files are merged into media/shots.json, so rooms rendered on different nights add up.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

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
        elif png.stem in ("hall", "hall-phone") or png.stem.startswith("seat-"):
            Image.open(png).convert("RGB").save(OUT / f"{png.stem}.jpg", quality=86, optimize=True, progressive=True)
            print(f"{png.stem}.jpg")


def frames_of(name):
    for src in srcs:
        d = src / name
        if d.is_dir() and any(d.glob("f_*.png")):
            return sorted(d.glob("f_*.png"))
    return []


ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
for key, info in sorted(shots.items()):
    if not key.startswith("walk-b-"):
        continue
    n = key.split("-")[-1]
    a, b = frames_of(f"walk-a-{info['side']}"), frames_of(key)
    if not a or not b:
        continue
    fps = info.get("fps", 30)
    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "frames.txt"
        listing.write_text("".join(f"file '{p}'\nduration {1 / fps:.6f}\n" for p in a + b))
        for name, vf in ((f"walk-{n}.mp4", []), (f"walk-{n}-back.mp4", ["-vf", "reverse"])):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-r", str(fps), *vf, *ENC,
                            str(OUT / name)], check=True)
    shots[f"walk-{n}"] = {"kind": "clip", "frames": len(a) + len(b), "fps": fps}
    print(f"walk-{n}.mp4 and walk-{n}-back.mp4 ({len(a)} + {len(b)} frames)")

existing.write_text(json.dumps(shots, indent=1))
print(f"shots.json: {', '.join(sorted(shots))}")
