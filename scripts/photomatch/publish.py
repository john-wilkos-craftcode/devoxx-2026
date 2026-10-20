"""The photo-matched finals into the cinema page's media (site/cinema/media/), as they come (John 19/10: commit and
push as we go). Run it any time; it publishes only what's whole and newer than what's there.

    python3 scripts/photomatch/publish.py [final folder]     # default: kino-renders/photomatch/final

- Stills (final/venue/stills): hall, seat-<n>, hall-phone, door-phone-<n> as JPEG, their -front layers as WebP, and
  their shots-stills-*.json merged into media/shots.json. Laptop stills only once they're wide (the hall has px: John
  19/10, ultrawide windows); the narrow ones carry the old walk_end inner.
- Clips (final/venue/<dir>/anim with .complete), web-encoded from the PNG frames in AV1, HEVC and H.264, full size,
  smaller and as a walks-off glimpse (files()): walk there -> walk-<n>, walk back -> back-<n>, fly-through -> intro
  (-phone variants alike). John 19/10: not one big mp4 each time; see cinema.js clipSrc for which file plays.
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
CODECS = {   # best first; at the same look AV1 is 1.1 MB per 10 s laptop walk, HEVC 1.5, H.264 2.6 (19/10, room 8)
    "av1": ["-c:v", "libaom-av1", "-cpu-used", "6", "-row-mt", "1", "-crf", "36", "-b:v", "0"],
    "hevc": ["-c:v", "libx265", "-preset", "slow", "-crf", "26", "-tag:v", "hvc1", "-x265-params", "log-level=error"],
    "h264": ["-c:v", "libx264", "-preset", "slow", "-crf", "24"],
}
# a keyframe every second, so the walks-off jump lands on one; faststart, so a walk plays while it downloads
COMMON = ["-g", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]
SMALL = 0.6                     # the -s files' scale (1600 px -> 960)
GLIMPSE = 12                    # frames at each end in the -g files (half a second)
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


def files(name):
    """a final walk's files on the page (cinema.js clipSrc): AV1 and HEVC each full size, smaller (-s: data saver,
    slow networks, small windows) and as a glimpse (-g: the first and last half second, for walks off); H.264, the
    fallback for the few browsers without either, smaller and glimpse only"""
    out = {}
    for codec in CODECS:
        for v in ("", "-s", "-g"):
            if codec == "h264" and not v:
                continue
            out[(codec, v)] = OUT / f"{name}{v}{'' if codec == 'h264' else '.' + codec}.mp4"
    return out


def encode(src, first, n, codec, v, dst, w, h, full):
    vf = [f"crop={full[0]}:{full[1]}:0:0"]           # even sides (H.264/HEVC need them; the phones render 810x1755)
    if v == "-s":
        vf.append(f"scale={w}:{h}:flags=lanczos")
    if v == "-g":                                   # the first and last half second, back to back
        vf.append(f"select='lt(n\\,{GLIMPSE})+gte(n\\,{n - GLIMPSE})',setpts=N/{FPS}/TB")
    subprocess.run(["nice", "-n", "19", "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-start_number", str(first), "-i", str(src / "f_%04d.png"), "-vf", ",".join(vf),
                    *CODECS[codec], *COMMON, str(dst)], check=True)


for done in sorted((FINAL / "venue").glob("*/anim/.complete")):
    name, still = clip(done.parent.parent.name)
    if still not in final_stills:
        continue
    frames = sorted(done.parent.glob("f_*.png"))
    w, h = Image.open(frames[0]).size
    w, h = w - w % 2, h - h % 2                      # an odd side loses its last pixel row or column
    small = [round(w * SMALL / 2) * 2, round(h * SMALL / 2) * 2]
    entry = {"kind": "clip", "frames": len(frames), "fps": FPS, "px": [w, h], "small": small, "glimpse": GLIMPSE,
             "codecs": list(CODECS)}
    out = files(name)
    if shots.get(name) == entry and not any(newer(done, f) for f in out.values()):
        continue
    first = int(frames[0].stem[2:])
    for (codec, v), dst in out.items():
        encode(done.parent, first, len(frames), codec, v, dst, *small, (w, h))
    (OUT / f"{name}.mp4").unlink(missing_ok=True)   # the single H.264 file of before
    shots[name] = entry
    changed.append(name)

if changed:
    shots_file.write_text(json.dumps(shots, indent=1) + "\n")
print("published: " + (" ".join(changed) if changed else "nothing new"))
