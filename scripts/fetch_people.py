"""Download the people for the Blender scene's crowd into data/models/rocketbox/<avatar>/ (gitignored).

Microsoft Rocketbox avatars (MIT licence, github.com/microsoft/Microsoft-Rocketbox): rigged, realistic, casual
adults. Their animations are 3ds Max files, so build_scene.py poses the rigs itself. Only the colour, normal and
opacity (hair, lashes) maps are kept, shrunk to 1024 px PNG (the originals are 12-16 MB TGAs each).

    python3 scripts/fetch_people.py
"""
import io
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "models" / "rocketbox"
RAW = "https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/Avatars/Adults"
AVATARS = [f"Male_Adult_{i:02d}" for i in range(1, 13)] + [f"Female_Adult_{i:02d}" for i in range(1, 9)]
KEEP = ("_body_color", "_body_normal", "_head_color", "_head_normal", "_opacity_color")


def get(url):
    return subprocess.run(["curl", "-sfL", url], capture_output=True, check=True).stdout


def listing(name):
    import json
    api = f"https://api.github.com/repos/microsoft/Microsoft-Rocketbox/contents/Assets/Avatars/Adults/{name}/Textures"
    return [f["name"] for f in json.loads(get(api)) if f["name"].endswith(".tga") and any(k in f["name"] for k in KEEP)
            and " " not in f["name"] and "wrinkle" not in f["name"]]


def fetch(name):
    dest = OUT / name
    (dest / "Textures").mkdir(parents=True, exist_ok=True)
    fbx = dest / f"{name}.fbx"
    if not fbx.exists():
        fbx.write_bytes(get(f"{RAW}/{name}/Export/{name}.fbx"))
    for tga in listing(name):
        png = dest / "Textures" / tga.replace(".tga", ".png")
        if png.exists():
            continue
        im = Image.open(io.BytesIO(get(f"{RAW}/{name}/Textures/{tga}")))
        im.thumbnail((1024, 1024))
        im.save(png)
    return name


with ThreadPoolExecutor(6) as ex:
    for done in ex.map(fetch, AVATARS):
        print(done)
