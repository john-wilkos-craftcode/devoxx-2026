"""Floor 1: a portrait schedule totem beside each walk room's door, where the phone walks end (the door-phone stills of
build_scene.py: data/photomatch/seats.json "doors_phone"). Each stands 1.7 m in front of its still's camera, square on
to it, the same build as the hall's phone totem (hall_screen.py): 0.70 x 1.42 m screen, bezel, post, foot.
"""
import json
from pathlib import Path

from mathutils import Matrix, Vector

import pm_lib as L

FH, DIST, W, H = 6.2, 1.7, 0.70, 1.42
CORNERS = {}                                         # room -> the screen's corners (the stills' overlay, photomatch_scene)


def build(root, unified=True):
    doors = json.loads((Path(root) / "data" / "photomatch" / "seats.json").read_text()).get("doors_phone", {})
    frame = L.mat("totem-frame", 0x16171b, 0.4, metal=0.5)
    screen = L.emissive("totem-screen", 0x3d6fd8, 2.2)
    for n, d in doors.items():
        M = Matrix(d["matrix"])
        c = M.translation
        fwd = -(M.to_3x3() @ Vector((0, 0, 1)))
        fwd.z = 0
        fwd.normalize()
        p = c + fwd * DIST                                       # the screen's centre, at the camera's height
        side = Vector((-fwd.y, fwd.x, 0))
        def at(u, v, w=0.0):
            q = p + side * u + fwd * w
            return (q.x, q.y, v)
        z0, z1 = c.z - H / 2, c.z + H / 2
        CORNERS[n] = [at(-W / 2, z0), at(W / 2, z0), at(W / 2, z1), at(-W / 2, z1)]
        L.mesh_obj(f"door-totem-{n}", [at(-W / 2, z0, -0.005), at(W / 2, z0, -0.005), at(W / 2, z1, -0.005), at(-W / 2, z1, -0.005)],
                   [(0, 1, 2, 3)], screen)
        b = 0.05
        corners = [at(-W / 2 - b, z0 - 0.09), at(W / 2 + b, z0 - 0.09), at(W / 2 + b, z1 + b), at(-W / 2 - b, z1 + b)]
        back = [at(-W / 2 - b, z0 - 0.09, 0.06), at(W / 2 + b, z0 - 0.09, 0.06), at(W / 2 + b, z1 + b, 0.06), at(-W / 2 - b, z1 + b, 0.06)]
        L.mesh_obj(f"door-totem-{n}-bezel", corners + back,
                   [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], frame)
        q0, q1 = at(0, FH, 0.08), at(0, z0 - 0.09, 0.08)
        L.tube(f"door-totem-{n}-post", q0, q1, 0.05, frame, segs=12)
        L.cylinder(f"door-totem-{n}-foot", q0[0], q0[1], FH, FH + 0.04, 0.3, frame, segs=24)
    print(f"DOOR TOTEMS {sorted(doors, key=int)}", flush=True)
