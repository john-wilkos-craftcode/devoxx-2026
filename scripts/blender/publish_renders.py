"""Turn a render folder from build_scene.py into the cinema page's media (site/cinema/media/).

    python3 scripts/blender/publish_renders.py /mnt/c/Users/wilkojo/kino-renders/room8

Stills (hall.png, seat-<n>.png) become JPEGs; each walk-<n>/ frame sequence becomes walk-<n>.mp4 and, played
backwards for the way out, walk-<n>-back.mp4 (H.264, yuv420p, faststart, so every browser plays them inline).
shots.json is merged into the existing one, so rooms rendered on different nights add up.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

src = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "site" / "cinema" / "media"
OUT.mkdir(parents=True, exist_ok=True)
shots = json.loads((src / "shots.json").read_text())

for png in sorted(src.glob("*.png")):
    if png.stem == "hall" or png.stem.startswith("seat-"):
        Image.open(png).convert("RGB").save(OUT / f"{png.stem}.jpg", quality=88, optimize=True, progressive=True)
        print(f"{png.stem}.jpg")

for d in sorted(p for p in src.glob("walk-*") if p.is_dir()):
    frames = sorted(d.glob("f_*.png"))
    if not frames:
        continue
    fps = shots.get(d.name, {}).get("fps", 30)
    common = ["-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
    pattern = str(d / "f_%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", frames[0].stem[2:], "-i", pattern,
                    *common, str(OUT / f"{d.name}.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", frames[0].stem[2:], "-i", pattern,
                    "-vf", "reverse", *common, str(OUT / f"{d.name}-back.mp4")], check=True)
    print(f"{d.name}.mp4 and {d.name}-back.mp4 ({len(frames)} frames)")

existing = OUT / "shots.json"
merged = json.loads(existing.read_text()) if existing.exists() else {}
merged.update(shots)
existing.write_text(json.dumps(merged, indent=1))
print(f"shots.json: {', '.join(sorted(merged))}")
