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
import bisect
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

FH, EYE = 6.2, 1.65
FPS = 24
STAIR = {"west": (-7.15, -4.85), "east": (10.25, 12.55)}          # the flights' x; y 9.88 (foot) .. -1.32 (top)
STAIR_FOOT, STAIR_TOP = 9.88, -1.32
GAP_Y = 12.48                                                       # middle of the glass box's side gap
LANE = {"west": -3.5, "east": 9.0}                                  # corridor lanes: outside the column rows (under the girders, x ~ -1.6 / 7.2), ~1.3 m from the stair openings
# south of the stairs the 2026 dressing has table rows along both sides (venue y -21.4 .. -37.6, chairs out to x -2.06
# and 7.30 on the aisle side) and the gate columns at y -19.3 (x -0.36..1.11 and 4.70..6.23)
GATE_Y, TABLES_Y = -19.3, (-37.6, -24.2)                            # (tables moved nearer the walls, past doors 5/8)
SIDE_AISLE = {"west": -5.2, "east": 10.3}                          # behind the tables, along the walls (rooms 5, 8)
CENTRE_X = 2.9                                                       # through the gate, down the central aisle (6, 7)
LOOK_AHEAD, LOOK_TAU = 4.0, 0.3
LOOK_S = 0.8                     # s: the camera looks where it will be this much later (at least LOOK_AHEAD m), so at
                                 # the ~10 s walks' speeds it starts turning into a corner early instead of whipping
HALL = {"laptop": {"pos": (2.4, 9.81, 1.7), "look": (2.4, 13.56, 1.7), "fov_v": 40.0},       # the fly-through's end
        "phone": {"pos": (5.6, 9.58, 1.5), "look": (5.6, 11.245, 1.5), "fov_v": 58.29}}   # (screen on the divider, 17/10)


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


def seat_pose(root, n, key="seats"):
    """the end still's camera: the seat (laptops) or the door totem (phones, key "doors_phone")"""
    d = json.loads((Path(root) / "data" / "photomatch" / "seats.json").read_text())
    s = d[key][str(n)]
    M = Matrix(s["matrix"])
    pose = {"pos": M.translation.copy(), "fwd": -(M.to_3x3() @ Vector((0, 0, 1))), "lens": s["lens"],
            "shift_x": s["shift_x"], "shift_y": s["shift_y"], "fit": s["sensor_fit"]}
    if key == "seats" and str(n) in d.get("walk_end", {}):      # the walk ends on the tighter crop of the still
        e = d["walk_end"][str(n)]
        pose.update(lens=e["lens"], shift_x=e["shift_x"], shift_y=e["shift_y"])
    return pose


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
    # first step: turning off the screen towards the stairwell's gap (since the screen moved onto the divider, 17/10,
    # the gap is ahead of the start, no longer behind it)
    # the gap is ahead of the start, no longer behind it); east of the screen the phone totem and its plant (hall_screen,
    # ~(5.6, 11.3) and (6.35, 10.8)) stand level with the gap, so the east walks pass south of them, the leaves >= 1 m from the lens (BRIEF checklist)
    if door["west"]:
        first = [(h[0] - 1.0, h[1] + 0.4)] if variant == "laptop" else [(h[0] - 0.6, h[1] + 0.3)]
    else:
        first = [(h[0] + 1.6, h[1] - 0.9), (7.9, h[1] - 0.5)] if variant == "laptop" else [(7.0, h[1] - 0.3), (7.9, h[1])]
    pts = [(h[0], h[1], h[2])] + [(x, y, EYE) for x, y in first] + [(inner, GAP_Y, EYE), (sx, GAP_Y, EYE),
           (sx, STAIR_FOOT, EYE), (sx, STAIR_TOP, FH + EYE), (sx, STAIR_TOP - 1.8, FH + EYE),
           (lane, STAIR_TOP - 3.6, FH + EYE)]
    north = yc > STAIR_TOP                                       # rooms 3 and 10: back north past the opening
    side_x = SIDE_AISLE[side]
    if north or yc > TABLES_Y[1]:                                # rooms 3, 4, 5, 8, 9, 10: the lane runs to the door
        # and turns in 2.5 m short of it (it ran 3 m past, beside the door totem, and doubled back: John 17/10, "it goes
        # to the right to the totem before going back left and in through the door")
        y_turn = yc + (-1 if north else 1) * 2.5
        if north or y_turn < STAIR_TOP - 3.6 - 1.0:
            pts.append((lane, y_turn, FH + EYE))
    else:                                                        # rooms 6, 7: through the gate, down the middle
        pts += [(lane, GATE_Y + 5.0, FH + EYE), (CENTRE_X, GATE_Y + 1.5, FH + EYE), (CENTRE_X, yc + 3.0, FH + EYE)]
    if variant == "phone":                                    # on to the door totem's still
        e = seat_pose(root, n, "doors_phone")["pos"]
        pts.append((e.x, e.y, e.z))
        return pts, door, e
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


WALK_T = 10.0                    # s: John (17/10): "much faster, ease in ease out, about 10 s"
EASE_IN, EASE_OUT = 5.0, 4.0     # m/s^2: the acceleration from the start and the braking into the end pose
OMEGA_MAX = math.radians(90.0)   # rad/s: the view never swings faster (at 10 s the turns off the screen and into the
#                                  room's door whipped, 17/10); the straights take up the time
STRAIGHT_UP = 1.25               # ... at most this much faster than without the turn limit (else the limit gives)


def speeds(pts):
    """relative speed at each sample (the solver in timing() scales them to the walk's duration). The time comes out
    of the least interesting parts first (John, 17/10): the hall at the start and the auditorium at the end run
    relatively faster than the stairs and the corridor"""
    v = []
    for p in pts:
        # the flight, the stairwell box and its doorway: the 90 deg turn between the side door and the foot of the stairs
        # ran at hall speed and whipped (17/10)
        on_stairs = (STAIR_TOP - 0.5 < p.y < STAIR_FOOT + 0.5 and (p.x < -4.6 or p.x > 10.2)) or \
            (p.z < FH and STAIR_FOOT - 0.5 < p.y < GAP_Y + 1.0 and (p.x < -3.3 or p.x > 8.7))
        in_room = p.x < -7.4 or p.x > 12.8
        upstairs = p.z > FH + 0.5
        if in_room:
            v.append(6.0)
        elif on_stairs:
            v.append(4.5)
        elif upstairs:
            v.append(9.0)
        else:
            v.append(9.0)
    return v


def smooth(w):
    return w * w * (3 - 2 * w)


def turn_caps(pts, step, look, blend):
    """absolute speed caps (m/s) per sample so the view turns at most OMEGA_MAX: the look direction by distance (the
    point `look` samples ahead, then blend(s, d) mixes in the start and end views) differenced every 0.2 m; each cap
    also holds over the metre before, so the camera has braked by the time it turns"""
    n = len(pts)
    stride = max(1, int(0.2 / step))
    idx = list(range(0, n, stride))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    D = []
    for i in idx:
        d = pts[min(n - 1, i + look)] - pts[i]
        D.append(blend(i * step, d.normalized() if d.length > 1e-4 else None))
    caps, pre = [1e9] * n, int(1.0 / step)
    for a in range(len(idx) - 1):
        ang = D[a].angle(D[a + 1], 0.0)
        if ang > 1e-6:
            c = OMEGA_MAX * (idx[a + 1] - idx[a]) * step / ang
            for i in range(max(0, idx[a] - pre), idx[a + 1] + 1):
                caps[i] = min(caps[i], c)
    return caps


def timing(pts, step, target=WALK_T, caps=None):
    """seconds at each sample: the relative speeds scaled so the walk takes `target` s, starting from rest and
    settling to rest (ease in and out at EASE_IN / EASE_OUT). With caps (turn_caps): the turns slow down and the
    straights make the time up, at most STRAIGHT_UP faster than without caps; where that isn't enough the caps rise
    (the duration wins: John wants ~10 s)"""
    base = speeds(pts)

    def run(k, c=None):
        vt = [b * k for b in base] if c is None else [min(b * k, c * cp) for b, cp in zip(base, caps)]
        vt[0], vt[-1] = 0.3, 0.05
        for i in range(1, len(vt)):
            vt[i] = min(vt[i], math.sqrt(vt[i - 1] ** 2 + 2 * EASE_IN * step))
        for i in range(len(vt) - 2, -1, -1):
            vt[i] = min(vt[i], math.sqrt(vt[i + 1] ** 2 + 2 * EASE_OUT * step))
        t, out = 0.0, [0.0]
        for i in range(1, len(pts)):
            t += step / max(0.05, 0.5 * (vt[i] + vt[i - 1]))
            out.append(t)
        return out

    def bisect_on(f, lo, hi):                          # the smallest x in lo..hi with f(x) <= target (f falls)
        for _ in range(40):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if f(m) > target else (lo, m)
        return hi
    k = bisect_on(lambda k: run(k)[-1], 0.2, 4.0)
    if caps is None:
        return run(k)
    k_max = k * STRAIGHT_UP
    if run(k_max, 1.0)[-1] <= target:
        return run(bisect_on(lambda kk: run(kk, 1.0)[-1], 0.2, k_max), 1.0)
    c = bisect_on(lambda cc: run(k_max, cc)[-1], 1.0, 20.0)
    print(f"ROOMWALK timing: turns up to {math.degrees(OMEGA_MAX) * c:.0f} deg/s to fit {target:.1f} s", flush=True)
    return run(k_max, c)


def camera(root, n, variant="laptop", first_frame=402, activate=True):
    """keys a camera along room n's walk from first_frame; returns it. activate: make it the scene's camera, set the
    frame range and the visibility swaps (False: a camera only for the crowd's placement, crowd_place.py)"""
    scene = bpy.context.scene
    pts_c, door, e = waypoints(root, n, variant)
    seat = seat_pose(root, n) if variant == "laptop" else seat_pose(root, n, "doors_phone")
    hall = HALL[variant]
    data = bpy.data.cameras.new(f"cam-room-{n}")
    data.sensor_fit, data.sensor_height, data.sensor_width = "VERTICAL", 24, 36
    hall_lens = 12 / math.tan(math.radians(hall["fov_v"] or 40.0) / 2)
    data.clip_start, data.clip_end = 0.05, 1000
    cam = bpy.data.objects.new(f"cam-room-{n}", data)
    scene.collection.objects.link(cam)
    step = 0.02
    pts = resample(polyline(pts_c), step)
    target = WALK_T
    if variant == "phone":                         # the shorter phone walks in proportion (sqrt: not crawling)
        lap = resample(polyline(waypoints(root, n, "laptop")[0]), 0.1)
        target = WALK_T * min(1.0, math.sqrt(step * (len(pts) - 1) / (0.1 * (len(lap) - 1))))
    L = step * (len(pts) - 1)
    look = int(LOOK_AHEAD / step)
    screen_dir = (Vector(hall["look"]) - Vector(hall["pos"])).normalized()
    end_dir = seat["fwd"].normalized() if seat else None

    def blend(s, d):                                               # the start and end views, as in the loop below
        d = (d or screen_dir).lerp(screen_dir, smooth(max(0.0, 1.0 - s / 3.0))).normalized()
        if end_dir is not None:
            d = d.lerp(end_dir, smooth(max(0.0, min(1.0, (s - (L - 5.0)) / 5.0)))).normalized()
        return d
    ts = timing(pts, step, target, turn_caps(pts, step, look, blend))
    T = ts[-1]
    nf = int(math.ceil(T * FPS)) + 1
    prev, prev_d, j = None, None, 0
    swing = (0.0, first_frame)                                     # the fastest the view turns (deg/s, frame)
    for f in range(nf):
        t = min(T, f / FPS)
        while j < len(pts) - 2 and ts[j + 1] < t:
            j += 1
        a = (t - ts[j]) / max(1e-9, ts[j + 1] - ts[j])
        p = pts[j].lerp(pts[j + 1], max(0.0, min(1.0, a)))
        s = (j + a) * step
        q = pts[min(len(pts) - 1, max(j + look, bisect.bisect_left(ts, t + LOOK_S)))]
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
        if prev_d is not None:
            swing = max(swing, (math.degrees(prev_d.angle(d, 0.0)) * FPS, first_frame + f))
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
    if not activate:
        return cam
    scene.frame_start, scene.frame_end = first_frame, first_frame + nf - 1
    scene.camera = cam
    up = next((i for i, (tt, pp) in enumerate(zip_frames(pts, ts, nf)) if pp.z > FH + 1.0), nf)
    inside = next((i for i, (tt, pp) in enumerate(zip_frames(pts, ts, nf))
                   if (door["west"] and pp.x < door["x"] - 0.6) or (not door["west"] and pp.x > door["x"] + 0.6)), nf)
    swap_visibility(first_frame, first_frame + max(0, up - 8), first_frame + max(0, inside - 2), first_frame + nf - 1)
    clearance(zip_frames(pts, ts, nf), first_frame, up, inside)
    print(f"ROOMWALK {n} {variant}: {L:.0f} m in {T:.1f} s, frames {scene.frame_start}..{scene.frame_end}", flush=True)
    print(f"ROOMWALK view: turns at most {swing[0]:.0f} deg/s (frame {swing[1]})", flush=True)
    return cam


# the walk back (John, 17/10: "about 10 s back to the main menu"): the forward route reversed from the seat (or the
# door totem) to the stairwell's gap, then round to the hall still's pose square on to the screen (phones: the totem),
# approaching it along its axis from the south, west of the hall column at (2.65, 5.17) and clear of the totem plant
BACK_APPROACH = {("east", "laptop"): [(8.6, 9.3), (5.0, 7.9), (2.4, 7.4)],     # wide of the totem plant (0.51 m at (7.7, 9.4))
                 ("west", "laptop"): [(-0.6, 8.2), (2.4, 7.2)],
                 ("east", "phone"): [(7.6, 8.4), (5.6, 7.6)],
                 ("west", "phone"): [(-0.6, 8.2), (4.4, 7.2), (5.6, 7.6)]}


def last_frame(cam):
    """the last keyed frame of a walk camera"""
    fc = cam.animation_data.action.layers[0].strips[0].channelbags[0].fcurves[0]
    return int(max(k.co.x for k in fc.keyframe_points))


def back_waypoints(root, n, variant="laptop"):
    pts, door, e = waypoints(root, n, variant)
    k = next(i for i, p in enumerate(pts) if abs(p[1] - GAP_Y) < 1e-6)       # the stairwell's gap, hall side
    side = "west" if door["west"] else "east"
    h = HALL[variant]["pos"]
    back = list(reversed(pts[k:])) + [(x, y, EYE) for x, y in BACK_APPROACH[(side, variant)]] + [(h[0], h[1], h[2])]
    return back, door, e


def camera_back(root, n, variant="laptop", first_frame=600, activate=True):
    """keys a camera along room n's walk back from first_frame (the forward walk's last frame, so the cut is seamless):
    from the seat's crop (phones: the door totem) out and down to the hall still, ending square on to the screen"""
    scene = bpy.context.scene
    pts_c, door, e = back_waypoints(root, n, variant)
    seat = seat_pose(root, n) if variant == "laptop" else seat_pose(root, n, "doors_phone")
    hall = HALL[variant]
    data = bpy.data.cameras.new(f"cam-back-{n}")
    data.sensor_fit, data.sensor_height, data.sensor_width = "VERTICAL", 24, 36
    hall_lens = 12 / math.tan(math.radians(hall["fov_v"] or 40.0) / 2)
    data.clip_start, data.clip_end = 0.05, 1000
    cam = bpy.data.objects.new(f"cam-back-{n}", data)
    scene.collection.objects.link(cam)
    step = 0.02
    pts = resample(polyline(pts_c), step)
    target = WALK_T
    if variant == "phone":
        lap = resample(polyline(back_waypoints(root, n, "laptop")[0]), 0.1)
        target = WALK_T * min(1.0, math.sqrt(step * (len(pts) - 1) / (0.1 * (len(lap) - 1))))
    L = step * (len(pts) - 1)
    look = int(LOOK_AHEAD / step)
    screen_dir = (Vector(hall["look"]) - Vector(hall["pos"])).normalized()
    start_dir = seat["fwd"].normalized()

    def blend(s, d):                                               # the start and end views, as in the loop below
        d = (d or screen_dir).lerp(start_dir, smooth(max(0.0, 1.0 - s / 4.0))).normalized()
        return d.lerp(screen_dir, smooth(max(0.0, min(1.0, (s - (L - 4.0)) / 4.0)))).normalized()
    ts = timing(pts, step, target, turn_caps(pts, step, look, blend))
    T = ts[-1]
    nf = int(math.ceil(T * FPS)) + 1
    prev, prev_d, j = None, None, 0
    swing = (0.0, first_frame)                                     # the fastest the view turns (deg/s, frame)
    for f in range(nf):
        t = min(T, f / FPS)
        while j < len(pts) - 2 and ts[j + 1] < t:
            j += 1
        a = (t - ts[j]) / max(1e-9, ts[j + 1] - ts[j])
        p = pts[j].lerp(pts[j + 1], max(0.0, min(1.0, a)))
        s = (j + a) * step
        q = pts[min(len(pts) - 1, max(j + look, bisect.bisect_left(ts, t + LOOK_S)))]
        d = (q - p).normalized() if (q - p).length > 1e-4 else (prev_d or screen_dir)
        w0 = max(0.0, 1.0 - s / 4.0)                               # leave the seat's view over the first 4 m
        w0 = w0 * w0 * (3 - 2 * w0)
        d = d.lerp(start_dir, w0).normalized()
        we = max(0.0, min(1.0, (s - (L - 4.0)) / 4.0))              # settle onto the screen over the last 4 m
        we = we * we * (3 - 2 * we)
        d = d.lerp(screen_dir, we).normalized()
        if LOOK_TAU and prev_d is not None:
            k = 1 - math.exp(-(1 / FPS) / LOOK_TAU)
            k = k + (1 - k) * max(we, w0)
            d = prev_d.lerp(d, k).normalized()
        if prev_d is not None:
            swing = max(swing, (math.degrees(prev_d.angle(d, 0.0)) * FPS, first_frame + f))
        prev_d = d
        quat = d.to_track_quat("-Z", "Y")
        rot = quat.to_euler("XYZ", prev) if prev else quat.to_euler("XYZ")
        prev = rot
        rot0 = rot0 if f else rot
        cam.location, cam.rotation_euler = p, rot
        fr = first_frame + f
        cam.keyframe_insert("location", frame=fr)
        cam.keyframe_insert("rotation_euler", frame=fr)
        data.lens = seat["lens"] + (hall_lens - seat["lens"]) * (1 - w0)       # the seat's crop back to the hall lens
        data.shift_x, data.shift_y = seat["shift_x"] * w0, seat["shift_y"] * w0
        data.keyframe_insert("lens", frame=fr)
        data.keyframe_insert("shift_x", frame=fr)
        data.keyframe_insert("shift_y", frame=fr)
    for fr, pos, fwd, near in ((first_frame, seat["pos"], start_dir, rot0),
                               (first_frame + nf - 1, Vector(hall["pos"]), screen_dir, prev)):
        cam.location = pos                                         # both ends exactly on the stills, each euler kept
        cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler("XYZ", near)   # next to its neighbour's (the first
        # frame took the last's and could land a turn away: a 360 deg spin blurred into frames 1-2, room 3, 18/10)
        cam.keyframe_insert("location", frame=fr)
        cam.keyframe_insert("rotation_euler", frame=fr)
    if not activate:
        return cam
    scene.frame_start, scene.frame_end = first_frame, first_frame + nf - 1
    scene.camera = cam
    track = zip_frames(pts, ts, nf)
    out = next((i for i, (tt, pp) in enumerate(track)
                if (door["west"] and pp.x > door["x"] + 0.6) or (not door["west"] and pp.x < door["x"] - 0.6)), nf)
    down = next((i for i, (tt, pp) in enumerate(track) if i > out and pp.z < FH + 1.0), nf)   # (the seat itself can
    # sit below floor 1's level on the rake: only count the stairs, after the door)
    swap_visibility_back(first_frame, first_frame + max(0, out - 2), first_frame + min(nf - 1, down + 8),
                         first_frame + nf - 1)
    rev = list(reversed(track))                                    # clearance() thinks forwards
    up_r = next((i for i, (tt, pp) in enumerate(rev) if pp.z > FH + 1.0), nf)
    in_r = nf - out
    clearance(rev, first_frame, up_r, in_r, back=True)
    print(f"ROOMWALK back {n} {variant}: {L:.0f} m in {T:.1f} s, frames {scene.frame_start}..{scene.frame_end}", flush=True)
    print(f"ROOMWALK back view: turns at most {swing[0]:.0f} deg/s (frame {swing[1]})", flush=True)
    return cam


def swap_visibility_back(f0, f_out, f_down, f1):
    """the walk back's swaps (see swap_visibility): the hall side only from the room's door on, the auditoriums only
    until the camera is down the stairs"""
    def keys(ob, on_from, on_to):
        for f, hidden in ((f0, not (on_from <= f0 <= on_to)), (on_from, False), (on_to + 1, True)):
            if f0 <= f <= f1 + 1:
                ob.hide_render = hidden
                ob.keyframe_insert("hide_render", frame=f)
    aud = bpy.data.collections.get("auditoriums")
    for ob in (aud.objects if aud else []):
        keys(ob, f0 - 10, f_down)
    for name in HALL_SIDE:
        c = bpy.data.collections.get(name)
        for ob in (c.objects if c else []):
            if ob.type in ("MESH", "LIGHT", "FONT", "CURVE"):
                keys(ob, f_out, f1 + 10)
    bpy.context.scene.frame_set(f0)
    print(f"ROOMWALK back visibility: the hall side from frame {f_out}, the auditoriums until {f_down}", flush=True)


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
    bpy.context.scene.frame_set(f0)            # keying leaves each property at its last key: back to the start's state
    print(f"ROOMWALK visibility: auditoriums from frame {f_up}, the hall side until {f_in}", flush=True)


CLEAR_MIN = 0.45                 # m from the camera to the nearest surface: closer is a brush the eye catches


def clearance(track, f0, up, inside, back=False):
    """the camera's distance to the nearest surface each frame, against what it can actually be near: the hall side,
    stairs and upstairs before the doorway, the stairs, upstairs and the auditorium after the stair top (the plan's
    rakes overlap the hall, so one model would report false brushes). Prints the tightest frames."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()

    def bvh(colls):
        verts, polys, off = [], [], 0
        for cn in colls:
            c = bpy.data.collections.get(cn)
            for ob in (c.all_objects if c else []):
                if ob.type != "MESH" or len(ob.data.polygons) > 200000:   # the street trees and plant models: far
                    continue                                               # from every walk, and 34M triangles
                me = ob.evaluated_get(dg).to_mesh()
                me.calc_loop_triangles()
                n = len(me.vertices)
                if n and me.loop_triangles:
                    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
                    M = np.array(ob.matrix_world); co = co @ M[:3, :3].T + M[:3, 3]
                    tri = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
                    verts.append(co); polys.append(tri.reshape(-1, 3) + off); off += n
                ob.evaluated_get(dg).to_mesh_clear()
        return BVHTree.FromPolygons(np.concatenate(verts).tolist(), np.concatenate(polys).tolist(), all_triangles=True)
    below = bvh(HALL_SIDE + ("stairs", "upstairs", "door_totems"))
    above = bvh(("stairs", "upstairs", "auditoriums", "door_totems"))
    worst = []
    for i, (t, p) in enumerate(track):
        d = min(tree.find_nearest(p)[3] for tree in ([below] if i < up else []) + ([above] if i >= up - 30 else []) +
                ([below] if up - 30 <= i < inside else []))
        worst.append((d, f0 + (len(track) - 1 - i if back else i)))
    worst.sort()
    tight = [(round(d, 2), f) for d, f in worst if d < CLEAR_MIN]
    print(f"ROOMWALK clearance: min {worst[0][0]:.2f} m at frame {worst[0][1]}; {len(tight)} frames under {CLEAR_MIN} m"
          + (f": {tight[:8]}" if tight else ""), flush=True)


def all_paths(root, variants=("laptop", "phone")):
    """every room walk's ground path (x, y), for the crowd's clearance and visibility"""
    out = []
    for n in (3, 4, 5, 6, 7, 8, 9, 10):
        for var in variants:
            for wp in (waypoints, back_waypoints):
                pts, _, _ = wp(root, n, var)
                out.append([(p.x, p.y) for p in resample(polyline(pts), 0.25)])
    return out
