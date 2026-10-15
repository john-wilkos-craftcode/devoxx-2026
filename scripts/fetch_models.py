"""Download the 3D models the Blender scene uses into data/models/<asset>/ (gitignored).

Poly Haven models (CC0) come as a .blend with its textures beside it; build_scene.py appends their objects.

    python3 scripts/fetch_models.py
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "models"

POLYHAVEN = [
    "pachira_aquatica_01",     # money trees, four sizes up to 1.9 m: the tall planters by the hall screen and totem
    "calathea_orbifolia_01",   # low broad-leaved clumps at their feet
    "island_tree_02",          # young broadleaf trees along the forecourt's verge (the Street View photos)
    "island_tree_03",
    "tree_small_02",
    "shrub_02",                # low planting in the verge
]


def get(url):
    return subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", url], capture_output=True, check=True).stdout


for asset in POLYHAVEN:
    dest = OUT / asset
    if (dest / f"{asset}.blend").exists():
        continue
    blend = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))["blend"]["2k"]["blend"]
    for rel, f in blend.get("include", {}).items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(get(f["url"]))
    (dest / f"{asset}.blend").write_bytes(get(blend["url"]))
    (dest / "SOURCE.txt").write_text(f"polyhaven {asset} (CC0) https://polyhaven.com/a/{asset}\n")
    print(f"{asset}: polyhaven")
# a partly cloudy sky for the forecourt (the walk in starts outside)
HDRI = "kloofendal_48d_partly_cloudy_puresky"
sky = ROOT / "data" / "textures" / "hdri" / f"{HDRI}_2k.exr"
if not sky.exists():
    sky.parent.mkdir(parents=True, exist_ok=True)
    sky.write_bytes(get(json.loads(get(f"https://api.polyhaven.com/files/{HDRI}"))["hdri"]["2k"]["exr"]["url"]))
    print(f"{HDRI}: polyhaven hdri")
print(f"models in {OUT}")
