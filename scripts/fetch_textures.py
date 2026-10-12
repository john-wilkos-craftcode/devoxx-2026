"""Download the CC0 PBR texture sets the Blender scene uses into data/textures/<name>/ (gitignored).

Each set ends up as color.jpg, rough.jpg and normal.jpg (OpenGL convention), whatever the source calls
them. Sources: ambientCG (zip per set) and Poly Haven (file per map), both CC0.

    python3 scripts/fetch_textures.py
"""
import io
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "textures"

# name in the scene -> source
SETS = {
    "carpet": ("ambientcg", "Carpet016"),       # fibre detail; colour and the 50 cm tiles are done in the shader
    "curtain": ("polyhaven", "terlenka"),        # beige drape fabric
}


def get(url):
    return subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", url], capture_output=True, check=True).stdout


def ambientcg(asset, dest):
    z = zipfile.ZipFile(io.BytesIO(get(f"https://ambientcg.com/get?file={asset}_2K-JPG.zip")))
    for member, name in (("_Color.jpg", "color.jpg"), ("_Roughness.jpg", "rough.jpg"), ("_NormalGL.jpg", "normal.jpg")):
        src = next(n for n in z.namelist() if n.endswith(member))
        (dest / name).write_bytes(z.read(src))


def polyhaven(asset, dest):
    files = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))
    for key, name in (("Diffuse", "color.jpg"), ("Rough", "rough.jpg"), ("nor_gl", "normal.jpg")):
        (dest / name).write_bytes(get(files[key]["2k"]["jpg"]["url"]))


for name, (source, asset) in SETS.items():
    dest = OUT / name
    if (dest / "normal.jpg").exists():
        continue
    dest.mkdir(parents=True, exist_ok=True)
    {"ambientcg": ambientcg, "polyhaven": polyhaven}[source](asset, dest)
    (dest / "SOURCE.txt").write_text(f"{source} {asset} (CC0)\n")
    print(f"{name}: {source} {asset}")
print(f"textures in {OUT}")
