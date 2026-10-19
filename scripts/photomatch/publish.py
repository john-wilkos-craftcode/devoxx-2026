"""The photo-matched finals into the cinema page's media (site/cinema/media/), as they come (John 19/10: commit and
push as we go). Run it any time; it publishes only what's whole and newer than what's there.

    python3 scripts/photomatch/publish.py [final folder]     # default: kino-renders/photomatch/final

- Stills (final/venue/stills): hall, seat-<n>, hall-phone, door-phone-<n> as JPEG, their -front layers as WebP, and
  their shots-stills-*.json merged into media/shots.json. Laptop stills only once they're wide (the hall has px: John
  19/10, ultrawide windows); the narrow ones carry the old walk_end inner.
- Clips (final/venue/<dir>/anim with .complete), web-encoded from the PNG frames (crf 24, faststart: the 6-7 MB
  masters look the same at 2.5 MB): walk there -> walk-<n>, walk back -> back-<n>, fly-through -> intro (-phone
  variants alike).
- A still and the walk that ends on it go up together, so the page never pairs a final walk with an old still.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "site" / "cinema" / "media"
FINAL = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/c/Users/wilkojo/kino-renders/photomatch/final")
STILLS = FINAL / "venue" / "stills"
ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
FPS = 24

shots_file = OUT / "shots.json"
shots = json.loads(shots_file.read_text())
changed = []


def newer(src, dst):
    return not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime


def walk_dir(still):
    """the walk that ends on this still: they go up together, so the page never pairs a final walk with an old still"""
    if still in ("hall", "hall-phone"):
        return "walk" + still[4:]
    kind, n = still.rsplit("-", 1)
    return f"walk-room{n}" if kind == "seat" else f"walk-phone-room{n}"


final_stills = set()
for f in sorted(STILLS.glob("shots-stills-*.json"), key=lambda p: p.stat().st_mtime):
    incoming = json.loads(f.read_text())
    if "laptop" in f.name and not incoming.get("hall", {}).get("px"):
        continue
    for k, v in incoming.items():
        if not (FINAL / "venue" / walk_dir(k) / "anim" / ".complete").exists():
            continue
        v.pop("inner_measured", None)
        if shots.get(k) != v:
            shots[k] = v
            changed.append(k)
        final_stills.add(k)
        for name in (k, v.get("front")):
            png = STILLS / f"{name}.png" if name else None
            if not png or not png.exists():
                continue
            if name.endswith("-front"):         # what stands in front of the screen: keeps its transparency
                dst = OUT / f"{name}.webp"
                if newer(png, dst):
                    Image.open(png).save(dst, quality=88, method=6)
                    changed.append(dst.name)
            else:
                dst = OUT / f"{name}.jpg"
                if newer(png, dst):
                    Image.open(png).convert("RGB").save(dst, quality=86, optimize=True, progressive=True)
                    changed.append(dst.name)


def clip(d):
    """render dir -> (page clip name, the still it must go up with)"""
    phone = d.startswith("walk-phone")
    rest = d[len("walk-phone"):] if phone else d[len("walk"):]
    if not rest:
        return ("intro-phone", "hall-phone") if phone else ("intro", "hall")
    n = rest.removeprefix("-room").removesuffix("-back")
    base = "back" if rest.endswith("-back") else "walk"
    return (f"{base}-phone-{n}", f"door-phone-{n}") if phone else (f"{base}-{n}", f"seat-{n}")


for done in sorted((FINAL / "venue").glob("*/anim/.complete")):
    name, still = clip(done.parent.parent.name)
    if still not in final_stills:
        continue
    dst = OUT / f"{name}.mp4"
    frames = sorted(done.parent.glob("f_*.png"))
    entry = {"kind": "clip", "frames": len(frames), "fps": FPS}
    if newer(done, dst) or shots.get(name) != entry:
        first = int(frames[0].stem[2:])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-start_number", str(first),
                        "-i", str(done.parent / "f_%04d.png"), *ENC, str(dst)], check=True)
        shots[name] = entry
        changed.append(dst.name)

if changed:
    shots_file.write_text(json.dumps(shots, indent=1) + "\n")
print("published: " + (" ".join(changed) if changed else "nothing new"))
