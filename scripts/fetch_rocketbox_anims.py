"""Download a curated set of the Microsoft Rocketbox library's own motion-capture clips (MIT licence, made for the
same Bip01 rig as data/models/rocketbox/) into data/models/rocketbox_anims/ (gitignored). Resume-safe: files that
are already there with the right size are skipped.

    python3 scripts/fetch_rocketbox_anims.py

Source: github.com/microsoft/Microsoft-Rocketbox, Assets/Animations/all_animations_max_motextr_static (in place)
and all_animations_max_motextr_xy (walks, with root motion in the ground plane).
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "models" / "rocketbox_anims"
API = "https://api.github.com/repos/microsoft/Microsoft-Rocketbox/contents/Assets/Animations/"
# clip names without the f_/m_ prefix and the .max.fbx suffix, as regular expressions
STATIC = [r"idle_neutral_0[1-5]", r"idle_breathe_01", r"idle_look_around_0[12]", r"idle_waiting(_01)?",
          r"idle_touch_face(_01)?", r"gestic_talk_neutral_0[1-3]", r"gestic_talk_relaxed_0[12]",
          r"gestic_talk_self-assured_01", r"gestic_listen_neutral_0[1-3]", r"gestic_listen_accept_0[12]",
          r"gestic_listen_relaxed", r"gestic_laugh_low", r"gestic_thoughtful", r"gestic_shrug_0[12]"]
# No clips that mime holding something (phones, cups, bags, documents, newspapers, umbrellas, trolleys, headphones):
# John, 15/10: props in mocap hands looked worse than empty hands, and an empty-handed mime looks wrong.
XY = [r"walk_neutral_0[1-3]", r"walk_stroll_0[12]", r"walk_slow_0[12]"]


def get(url):
    return subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", url], capture_output=True, check=True).stdout


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    picked = []
    for folder, pats in (("all_animations_max_motextr_static", STATIC), ("all_animations_max_motextr_xy", XY)):
        listing = json.loads(get(API + folder))
        for e in listing:
            m = re.fullmatch(r"([fm])_(.+)\.max\.fbx", e["name"])
            if m and any(re.fullmatch(p, m.group(2)) for p in pats):
                picked.append((e["name"], e["download_url"], e["size"]))
    for name, url, size in picked:
        dest = OUT / name.replace(".max.fbx", ".fbx")
        if dest.exists() and dest.stat().st_size == size:
            continue
        data = get(url)
        if len(data) != size:
            print(f"{name}: got {len(data)} bytes, expected {size}; skipping")
            continue
        dest.write_bytes(data)
        print(f"{dest.name} ({size // 1024} kB)")
    (OUT / "SOURCE.txt").write_text("Microsoft Rocketbox animations, MIT licence: "
                                    "https://github.com/microsoft/Microsoft-Rocketbox (Assets/Animations)\n")
    print(f"{len(picked)} clips in {OUT}")


if __name__ == "__main__":
    main()
