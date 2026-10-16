"""The sanity report after a venue build (scripts/photomatch/BRIEF.md, step 2): numbers in text, before any render.

- floating: a mesh whose bounding box is more than TOUCH from every other mesh's box and from the floors
  (a lamp hung by nothing, a sign off its wall, a prop in mid-air). Boxes are coarse: a hit is a lead to look at,
  and a big box (a wall, a floor) can hide a small gap; nothing is moved automatically.
- crowd: everyone's distance to both camera paths, their feet against the floor under them, and the closest pair.
- ranking (John, 16/10: "near the camera details matter, far away only if obviously broken from afar"): every
  finding gets its largest size on screen (px at the render width) and how long it is in view along the walk
  camera; FUDGE marks what is small and brief, and those are not worth fixing.
Prints SANITY lines; the build fails (exit code) only when FAIL_ON is set and something is found.
"""
import math

import bpy
import numpy as np

TOUCH = 0.02
FUDGE_PX, FUDGE_S = 12, 0.5     # smaller than this on screen, or in view for less than this: fudgeable
FAIL_ON = False


def boxes(obs):
    out = np.empty((len(obs), 6))
    for i, ob in enumerate(obs):
        M = np.array(ob.matrix_world)
        c = np.array([list(v) + [1.0] for v in ob.bound_box]) @ M.T
        out[i, :3], out[i, 3:] = c[:, :3].min(0), c[:, :3].max(0)
    return out


def floating():
    obs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "FONT", "CURVE") and not o.hide_render
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
            found.append((obs[i].name, float(gap.min()), tuple(np.round((lo[i] + hi[i]) / 2, 2)),
                          float(np.linalg.norm(hi[i] - lo[i]))))
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


def camera_track(step=2):
    """the walk camera's position and view direction every `step` frames, read from its curves (no scene
    evaluation, so the crowd isn't posed for every sample), and its focal length in pixels"""
    scene = bpy.context.scene
    cam = bpy.data.objects.get("cam-walk")
    if cam is None or not cam.animation_data or not cam.animation_data.action:
        return None
    act = cam.animation_data.action
    fcs = {}
    for l in act.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    fcs[(fc.data_path, fc.array_index)] = fc
    from mathutils import Euler, Vector
    track = []
    for f in range(scene.frame_start, scene.frame_end + 1, step):
        loc = Vector([fcs[("location", i)].evaluate(f) for i in range(3)])
        rot = Euler([fcs[("rotation_euler", i)].evaluate(f) for i in range(3)], "XYZ")
        fwd = rot.to_matrix() @ Vector((0, 0, -1))
        track.append((np.array(loc), np.array(fwd)))
    fov_v = 2 * math.atan(12 / cam.data.lens)                    # sensor fit vertical, 24 mm
    res_y = scene.render.resolution_y * scene.render.resolution_percentage / 100
    aspect = scene.render.resolution_x / scene.render.resolution_y
    half_h = math.atan(math.tan(fov_v / 2) * aspect)
    return track, res_y / 2 / math.tan(fov_v / 2), half_h, step / scene.render.fps


def on_screen(centre, size, cam):
    """(largest size on screen in px, seconds in view, nearest distance in m) along the walk"""
    track, f_px, half_h, dt = cam
    best_px, t_in, near = 0.0, 0.0, float("inf")
    c = np.array(centre)
    for loc, fwd in track:
        v = c - loc
        d = float(np.linalg.norm(v))
        near = min(near, d)
        if d < 1e-3:
            continue
        ang = math.acos(max(-1.0, min(1.0, float(v @ fwd) / d)))
        if ang < half_h + math.atan(size / 2 / d):               # some part of it can be in the frame
            t_in += dt
            best_px = max(best_px, size / d * f_px)
    return best_px, t_in, near


def report():
    fl = floating()
    cam = camera_track()
    rows = []
    for name, gap, c, size in fl:
        px, t, near = on_screen(c, size, cam) if cam else (float("nan"), float("nan"), float("nan"))
        rows.append((px, name, gap, c, t, near))
    rows.sort(key=lambda r: -(r[0] if r[0] == r[0] else 0))
    fix = 0
    for px, name, gap, c, t, near in rows[:40]:
        fudge = cam is not None and (px < FUDGE_PX or t < FUDGE_S)
        fix += 0 if fudge else 1
        print(f"SANITY floating {'FUDGE ' if fudge else 'FIX   '}{name}: {gap * 100:.0f} cm from anything, up to {px:.0f} px "
              f"on screen, {t:.1f} s in view, nearest {near:.1f} m, at {tuple(float(x) for x in c)}", flush=True)
    print(f"SANITY floating worth fixing: {fix} of {len(fl)}", flush=True)
    cr = crowd_report()
    for line in cr:
        print(f"SANITY crowd {line}", flush=True)
    print(f"SANITY {len(fl)} floating, {len(cr)} crowd issues", flush=True)
    if FAIL_ON and (fl or cr):
        raise RuntimeError("sanity report not clean")
