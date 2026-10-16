"""The sanity report after a venue build (scripts/photomatch/BRIEF.md, step 2): numbers in text, before any render.

- floating: a mesh whose bounding box is more than TOUCH from every other mesh's box and from the floors
  (a lamp hung by nothing, a sign off its wall, a prop in mid-air). Boxes are coarse: a hit is a lead to look at,
  and a big box (a wall, a floor) can hide a small gap; nothing is moved automatically.
- crowd: everyone's distance to both camera paths, their feet against the floor under them, and the closest pair.
Prints SANITY lines; the build fails (exit code) only when FAIL_ON is set and something is found.
"""
import math

import bpy
import numpy as np

TOUCH = 0.02
FAIL_ON = False


def boxes(obs):
    out = np.empty((len(obs), 6))
    for i, ob in enumerate(obs):
        M = np.array(ob.matrix_world)
        c = np.array([list(v) + [1.0] for v in ob.bound_box]) @ M.T
        out[i, :3], out[i, 3:] = c[:, :3].min(0), c[:, :3].max(0)
    return out


def floating():
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render
           and not o.name.startswith("crowd") and not any(c.hide_render for c in o.users_collection)]
    if not obs:
        return []
    B = boxes(obs)
    lo, hi = B[:, :3], B[:, 3:]
    found = []
    for i in range(len(obs)):
        gap = np.maximum(0, np.maximum(lo - hi[i], lo[i] - hi)).max(1)       # box-to-box gap (Chebyshev)
        gap[i] = np.inf
        if gap.min() > TOUCH:
            found.append((obs[i].name, float(gap.min()), tuple(np.round((lo[i] + hi[i]) / 2, 2))))
    return found


def crowd_report():
    try:
        import pm_areas.crowd as C
        import pm_areas.crowd_place as CP
    except ImportError:
        return []
    people = [o for o in bpy.context.scene.objects if o.type == "EMPTY" and o.name.startswith("crowd-")
              and "-" not in o.name[6:]]
    if not people:
        return []
    import pathlib
    paths = CP.camera_paths(C.ROOT if C.ROOT else pathlib.Path("."))
    issues = []
    xy = np.array([(o.location.x, o.location.y) for o in people])
    for o, (x, y) in zip(people, xy):
        d = CP.path_dist(paths, x, y)
        if d < 1.0 + CP.BODY_R:
            issues.append(f"{o.name} {d:.2f} m from a camera path")
    if len(xy) > 1:
        D = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
        np.fill_diagonal(D, np.inf)
        i, j = np.unravel_index(np.argmin(D), D.shape)
        print(f"SANITY crowd: {len(people)} people, closest pair {people[i].name} / {people[j].name} "
              f"{D[i, j]:.2f} m", flush=True)
    return issues


def report():
    fl = floating()
    for name, gap, c in sorted(fl, key=lambda t: -t[1])[:40]:
        print(f"SANITY floating {name}: {gap * 100:.0f} cm from anything, at {c}", flush=True)
    cr = crowd_report()
    for line in cr:
        print(f"SANITY crowd {line}", flush=True)
    print(f"SANITY {len(fl)} floating, {len(cr)} crowd issues", flush=True)
    if FAIL_ON and (fl or cr):
        raise RuntimeError("sanity report not clean")
