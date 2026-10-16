"""The walk from the hall still to a room's seat, through the photo-matched venue (John, 16/10: new camera paths through
the new model, ending in exactly the chairs of the published seat stills).

Route (in venue coordinates; west rooms 3-6 take the west stair, east rooms 7-10 the east one):
  hall still (the fly-through's last pose)  ->  a step back from the screen, turning towards the stair
  ->  in front of the gap in the stairwell's glass side wall (y 11.58..13.38, facing the middle of the hall)
  ->  through it onto the landing  ->  up the middle of the flight (34 steps, y 9.88 -> -1.32, rising to floor 1)
  ->  along the corridor lane between the stair opening and the column row  ->  in front of the door
  ->  through the doorway  ->  the top of the raked floor at the room's aisle  ->  down the aisle to the seat's row
  ->  along the row  ->  the seat still's pose (data/photomatch/seats.json: position, direction, lens, shift).
The in-room legs are the old walk's (walk_paths.py: the auditoriums are the old scene's, auditoriums.py).

Motion (the fly-through's grammar John approved): no pauses, speeds blended between keys with acceleration and braking
limits, the view eased from the screen to the way ahead and onto the seat's view, eulers kept continuous (motion blur
never tumbles). The clip starts on the fly-through's last frame, so the crowd's clock carries on from the hall still.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

FH, EYE = 6.2, 1.65
FPS = 30
STAIR = {"west": (-7.15, -4.85), "east": (10.25, 12.55)}          # the flights' x; y 9.88 (foot) .. -1.32 (top)
STAIR_FOOT, STAIR_TOP = 9.88, -1.32
GAP_Y = 12.48                                                       # middle of the glass box's side gap
LANE = {"west": -2.0, "east": 7.3}                                  # corridor lanes: ~1 m clear of the columns either side
ACCEL, DECEL, LOOK_AHEAD, LOOK_TAU = 2.2, 1.8, 4.0, 0.3
HALL = {"laptop": {"pos": (2.4, 14.08, 1.7), "look": (2.4, 17.83, 1.7), "fov_v": 40.0},
        "phone": {"pos": (5.6, 13.85, 1.5), "look": (5.6, 15.515, 1.5), "fov_v": None}}


def venue_json(root):
    return json.loads((Path(root) / "data" / "venue" / "venue.json").read_text())["venue"]


def door_for(v, n):
    """door centre on the corridor wall (build_scene.py's rule) and which side the room is on"""
    r = next(r for r in v["rooms"] if r["id"] == f"aud-{n}")
    b = r["bounds"]
    yc = b["y"] + r["doorMargin"] + 1.25 if r["doorSide"] == "low" else b["y"] + b["h"] - r["doorMargin"] - 1.25
    west = b["x"] + b["w"] <= -7.0
    # face: from the wall towards the corridor (build_scene.py's door["face"]): +1 for west rooms, -1 for east
    return {"x": -7.15 if west else 12.55, "y": yc, "west": west, "face": 1 if west else -1, "bounds": b}


def aisle_y(v, n, door):
    """the aisle by the door: halfway between the side wall and the first seats (build_scene.aisle_y_for)"""
    b = door["bounds"]
    seats = [d["bounds"] for d in v["decor"] if d.get("material") == "seat" and d.get("floor") == 1
             and b["x"] <= d["bounds"]["x"] <= b["x"] + b["w"] and b["y"] <= d["bounds"]["y"] <= b["y"] + b["h"]]
    r = next(r for r in v["rooms"] if r["id"] == f"aud-{n}")
    if r["doorSide"] == "low":
        return (b["y"] + min(s["y"] for s in seats)) / 2
    return (max(s["y"] + s["h"] for s in seats) + b["y"] + b["h"]) / 2


def rake_floor(v, n):
    rake = next(ln for ln in v["links"] if ln["id"] == f"rake-{n}")
    rb = rake["bounds"]

    def z(x):
        u = min(1.0, max(0.0, (x - rb["x"]) / rb["w"]))
        u = u if rake["ascending"] else 1 - u
        return FH + rake["base"] + rake["rise"] * u
    return z, rb


def seat_pose(root, n):
    s = json.loads((Path(root) / "data" / "photomatch" / "seats.json").read_text())["seats"][str(n)]
    M = Matrix(s["matrix"])
    return {"pos": M.translation.copy(), "fwd": -(M.to_3x3() @ Vector((0, 0, 1))), "lens": s["lens"],
            "shift_x": s["shift_x"], "shift_y": s["shift_y"], "fit": s["sensor_fit"]}


def waypoints(root, n, variant="laptop"):
    """the route's corner points (x, y, eye z) for room n"""
    v = venue_json(root)
    door = door_for(v, n)
    side = "west" if door["west"] else "east"
    xa, xb = STAIR[side]
    sx = (xa + xb) / 2
    face, wx, yc = door["face"], door["x"], door["y"] - (0.4 if n == 3 else 0.0)
    lane = LANE[side]
    h = HALL[variant]["pos"]
    inner = xb + 1.4 if door["west"] else xa - 1.4              # in the hall, level with the glass box's gap
    toward = -1 if door["west"] else 1
    first = (h[0] + 0.9 * toward, h[1] - 0.9) if variant == "laptop" else (h[0] - 0.4, h[1] - 1.0)
    pts = [(h[0], h[1], h[2]), (first[0], first[1], EYE), (inner, GAP_Y, EYE), (sx, GAP_Y, EYE),
           (sx, STAIR_FOOT, EYE), (sx, STAIR_TOP, FH + EYE), (sx, STAIR_TOP - 1.8, FH + EYE),
           (lane, STAIR_TOP - 3.6, FH + EYE)]
    north = yc > STAIR_TOP                                       # rooms 3 and 10: back north past the opening
    pts.append((lane, yc - (-1 if north else 1) * 3.0, FH + EYE))
    if variant == "phone":
        return pts, door, None
    zf, rb = rake_floor(v, n)
    high = rb["x"] + rb["w"] if door["west"] else rb["x"]
    ay = aisle_y(v, n, door)
    e = seat_pose(root, n)["pos"]
    pts += [(wx + face * 2.4, yc, FH + EYE), (wx - face * 1.8, yc, FH + EYE), (high + face * 0.7, ay, zf(high + face * 0.7) + EYE),
            (e.x - face * 0.4, ay, e.z + 0.7), (e.x - face * 0.4, e.y, e.z + 0.7), (e.x, e.y, e.z)]
    return pts, door, e


def polyline(pts, fillet=1.6):
    """corner points rounded with quadratic Beziers, as a dense 3D polyline"""
    P = [Vector(p) for p in pts]
    out = [P[0]]
    for a, b, c in zip(P, P[1:], P[2:]):
        d1, d2 = (b - a), (c - b)
        r = min(fillet, d1.length / 2, d2.length / 2)
        p0, p1 = b - d1.normalized() * r, b + d2.normalized() * r
        out.append(p0)
        for i in range(1, 10):
            t = i / 10
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t * t * p1)
        out.append(p1)
    out.append(P[-1])
    return out


def resample(poly, step):
    seg = [(poly[i + 1] - poly[i]).length for i in range(len(poly) - 1)]
    total, res, i, acc = sum(seg), [], 0, 0.0
    for k in range(int(total / step) + 1):
        s = k * step
        while i < len(seg) - 1 and acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = (s - acc) / seg[i] if seg[i] else 0
        res.append(poly[i].lerp(poly[i + 1], min(1.0, t)))
    res.append(poly[-1])
    return res


def speeds(pts, n_pts_marks):
    """target speed at each sample: a calm start, quicker on the open stretches, careful on the stairs and through the
    door, slow down the aisle (m/s)"""
    v = []
    for p in pts:
        on_stairs = STAIR_TOP - 0.5 < p.y < STAIR_FOOT + 0.5 and (p.x < -4.6 or p.x > 10.2)
        in_room = p.x < -7.4 or p.x > 12.8
        upstairs = p.z > FH + 0.5
        if in_room:
            v.append(3.0)
        elif on_stairs:
            v.append(3.2)
        elif upstairs:
            v.append(7.0)
        else:
            v.append(4.5)
    return v


def timing(pts, step):
    vt = speeds(pts, None)
    vt[0], vt[-1] = 0.6, 0.05
    for i in range(1, len(vt)):
        vt[i] = min(vt[i], math.sqrt(vt[i - 1] ** 2 + 2 * ACCEL * step))
    for i in range(len(vt) - 2, -1, -1):
        vt[i] = min(vt[i], math.sqrt(vt[i + 1] ** 2 + 2 * DECEL * step))
    t, out = 0.0, [0.0]
    for i in range(1, len(pts)):
        t += step / max(0.05, 0.5 * (vt[i] + vt[i - 1]))
        out.append(t)
    return out


def camera(root, n, variant="laptop", first_frame=402):
    """keys the scene camera along room n's walk from first_frame; returns the camera"""
    scene = bpy.context.scene
    pts_c, door, e = waypoints(root, n, variant)
    seat = seat_pose(root, n) if variant == "laptop" else None
    hall = HALL[variant]
    data = bpy.data.cameras.new(f"cam-room-{n}")
    data.sensor_fit, data.sensor_height, data.sensor_width = "VERTICAL", 24, 36
    hall_lens = 12 / math.tan(math.radians(hall["fov_v"] or 40.0) / 2)
    data.clip_start, data.clip_end = 0.05, 1000
    cam = bpy.data.objects.new(f"cam-room-{n}", data)
    scene.collection.objects.link(cam)
    step = 0.02
    pts = resample(polyline(pts_c), step)
    ts = timing(pts, step)
    T = ts[-1]
    nf = int(math.ceil(T * FPS)) + 1
    L = step * (len(pts) - 1)
    look = int(LOOK_AHEAD / step)
    screen_dir = (Vector(hall["look"]) - Vector(hall["pos"])).normalized()
    end_dir = seat["fwd"].normalized() if seat else None
    prev, prev_d, j = None, None, 0
    for f in range(nf):
        t = min(T, f / FPS)
        while j < len(pts) - 2 and ts[j + 1] < t:
            j += 1
        a = (t - ts[j]) / max(1e-9, ts[j + 1] - ts[j])
        p = pts[j].lerp(pts[j + 1], max(0.0, min(1.0, a)))
        s = (j + a) * step
        q = pts[min(len(pts) - 1, j + look)]
        d = (q - p).normalized() if (q - p).length > 1e-4 else (prev_d or screen_dir)
        w0 = max(0.0, 1.0 - s / 3.0)                               # leave the screen's view over the first 3 m
        d = d.lerp(screen_dir, w0 * w0 * (3 - 2 * w0)).normalized()
        we = 0.0
        if end_dir is not None:
            we = max(0.0, min(1.0, (s - (L - 5.0)) / 5.0))          # settle onto the seat's view over the last 5 m
            we = we * we * (3 - 2 * we)
            d = d.lerp(end_dir, we).normalized()
        if LOOK_TAU and prev_d is not None:
            k = 1 - math.exp(-(1 / FPS) / LOOK_TAU)
            k = k + (1 - k) * max(we, w0)
            d = prev_d.lerp(d, k).normalized()
        prev_d = d
        quat = d.to_track_quat("-Z", "Y")
        rot = quat.to_euler("XYZ", prev) if prev else quat.to_euler("XYZ")
        prev = rot
        cam.location, cam.rotation_euler = p, rot
        fr = first_frame + f
        cam.keyframe_insert("location", frame=fr)
        cam.keyframe_insert("rotation_euler", frame=fr)
        if seat:                                                   # the hall still's lens to the seat's lens and shift
            data.lens = hall_lens + (seat["lens"] - hall_lens) * we
            data.shift_x, data.shift_y = seat["shift_x"] * we, seat["shift_y"] * we
            data.keyframe_insert("lens", frame=fr)
            data.keyframe_insert("shift_x", frame=fr)
            data.keyframe_insert("shift_y", frame=fr)
    if seat:                                                       # the last frame is the seat still exactly
        cam.location = seat["pos"]
        quat = seat["fwd"].to_track_quat("-Z", "Y")
        cam.rotation_euler = quat.to_euler("XYZ", prev)
        cam.keyframe_insert("location", frame=first_frame + nf - 1)
        cam.keyframe_insert("rotation_euler", frame=first_frame + nf - 1)
    scene.frame_start, scene.frame_end = first_frame, first_frame + nf - 1
    scene.camera = cam
    up = next((i for i, (tt, pp) in enumerate(zip_frames(pts, ts, nf)) if pp.z > FH + 1.0), nf)
    inside = next((i for i, (tt, pp) in enumerate(zip_frames(pts, ts, nf))
                   if (door["west"] and pp.x < door["x"] - 0.6) or (not door["west"] and pp.x > door["x"] + 0.6)), nf)
    swap_visibility(first_frame, first_frame + max(0, up - 8), first_frame + max(0, inside - 2), first_frame + nf - 1)
    print(f"ROOMWALK {n} {variant}: {L:.0f} m in {T:.1f} s, frames {scene.frame_start}..{scene.frame_end}", flush=True)
    return cam


def zip_frames(pts, ts, nf):
    """(time, position) per frame along the resampled path"""
    T, j, out = ts[-1], 0, []
    for f in range(nf):
        t = min(T, f / FPS)
        while j < len(pts) - 2 and ts[j + 1] < t:
            j += 1
        a = (t - ts[j]) / max(1e-9, ts[j + 1] - ts[j])
        out.append((t, pts[j].lerp(pts[j + 1], max(0.0, min(1.0, a)))))
    return out


HALL_SIDE = ("outside", "entrance", "hollywood", "hall_screen")


def swap_visibility(f0, f_up, f_in, f1):
    """the plan's auditoriums dip into the hall's volume (their rakes go 3-4 m below floor 1): show the auditoriums
    only once the camera is upstairs, and the hall side only until it's through the room's door (nothing of either
    is visible from the other)"""
    def keys(ob, on_from, on_to):
        for f, hidden in ((f0, not (on_from <= f0 <= on_to)), (on_from, False), (on_to + 1, True)):
            if f0 <= f <= f1 + 1:
                ob.hide_render = hidden
                ob.keyframe_insert("hide_render", frame=f)
    aud = bpy.data.collections.get("auditoriums")
    for ob in (aud.objects if aud else []):
        keys(ob, f_up, f1 + 10)
    for name in HALL_SIDE:
        c = bpy.data.collections.get(name)
        for ob in (c.objects if c else []):
            if ob.type in ("MESH", "LIGHT", "FONT", "CURVE"):
                keys(ob, f0 - 10, f_in)
    print(f"ROOMWALK visibility: auditoriums from frame {f_up}, the hall side until {f_in}", flush=True)


def all_paths(root, variants=("laptop", "phone")):
    """every room walk's ground path (x, y), for the crowd's clearance and visibility"""
    out = []
    for n in (3, 4, 5, 6, 7, 8, 9, 10):
        for var in variants:
            pts, _, _ = waypoints(root, n, var)
            out.append([(p.x, p.y) for p in resample(polyline(pts), 0.25)])
    return out
