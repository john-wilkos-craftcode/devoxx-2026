"""The whole venue as one model, for the fly-through: the photo-matched areas built together in venue coordinates
(data/venue/venue.json's frame: metres, +x east, +y north, z up, hall floor z = 0, reception and forecourt 1.2).

Who builds what (each area's build(root, unified=True) keeps to its part):
  outside   the forecourt, street and the whole facade skin (glass, doors, sign); also the daylight (lighting())
  entrance  the reception interior, y -60.4 .. -37.4
  hollywood the threshold landing, the hall steps and the Hollywood hall from y -37.4 northwards
  hall_screen the schedule screen on the north wall, its plants, ivy and the phone totem (from build_scene.py)
  stairs    the two side stairs from the hall up to floor 1 (treads, shaft, balustrades), for the room walks
  upstairs  the floor-1 corridor, photo-matched round rooms 6/7 (2026 photos) and extended along the plan to its north
            end with columns and fabric cones measured from the Street View (2020), portals at every room door
The side-aisle close-up sets are not on any walk and stay out.

The walk (data/photomatch/walk.json): from the forecourt in through a ground-floor door west of the grand stair, north
along the queue with the stair and the reception under it on the right, down the hall steps, along the Hollywood aisle
between the booth islands to the schedule screen on the far north wall between the stairwells.
"""
import importlib
import json
import math

import bpy
from mathutils import Vector

PARTS = ("outside", "entrance", "hollywood", "hall_screen", "stairs", "upstairs", "auditoriums", "door_totems")
VIEW_TRANSFORM = "AgX"
LOOK = "AgX - Medium High Contrast"
EXPOSURE = 0.0
FPS = 24                                            # John 17/10: 24 fps for everything (website ambiance)
SPEED, EYE = 4.5, 1.65
SLOW, ACCEL, DECEL, LOOK_AHEAD, HOLD = [], 2.5, 1.2, 5.0, 1.0
START_LOOK, START_LOOK_M, END_FOV_V, END_EYE_Z = None, 9.0, None, None
SPEED_KEYS, LOOK_TAU, DURATION = [], 0.0, None
VARIANT = "laptop"                                  # or "phone" (set by the runner's --variant)
CROWD = False                                       # the crowd (pm_areas/crowd.py), set by the runner's --crowd
ROOM = None                                         # a room walk (pm_areas/room_walk.py) instead of the fly-through: --room
BACK = False                                        # with ROOM: the walk back from the room to the hall still: --back
TOTEM = None                                        # with ROOM, laptops: "to" the door totem, "in" from it to the seat,
#                                                     "back" from it to the hall still: --totem
FOV_V, WALK_SIZE, DOF_END = 44.5, (16, 9), None

WALK, SCREEN, FILLET = [], (0, 0, 0), 2.5         # from data/photomatch/walk.json


def floor_z(x, y):
    """the camera's floor: forecourt and reception at 1.2, the hall at 0. Over the hall steps (y -34.4 .. -32.44) the
    camera glides down over a longer stretch (y -36.5 .. -30.5) so a fast pass doesn't drop like a lift"""
    if y < -36.5:
        return 1.2
    if y > -30.5:
        return 0.0
    t = (y + 36.5) / 6.0
    return 1.2 * (1 - t * t * (3 - 2 * t))


def load_walk(root):
    global WALK, SCREEN, SPEED, EYE, FILLET, SLOW, ACCEL, DECEL, LOOK_AHEAD, HOLD, START_LOOK, START_LOOK_M, END_FOV_V, END_EYE_Z
    w = json.loads((root / "data" / "photomatch" / "walk.json").read_text())
    WALK, SCREEN = [tuple(p) for p in w["points"]], tuple(w["screen"])
    SPEED, EYE, FILLET, SLOW = w["speed"], w["eye"], w["fillet"], w.get("slow", [])
    ACCEL, DECEL = w.get("accel", ACCEL), w.get("decel", DECEL)
    LOOK_AHEAD, HOLD = w.get("look_ahead", LOOK_AHEAD), w.get("hold", HOLD)
    START_LOOK, START_LOOK_M = w.get("start_look"), w.get("start_look_m", START_LOOK_M)
    END_FOV_V, END_EYE_Z = w.get("end_fov_v"), w.get("end_eye_z")
    global SPEED_KEYS, LOOK_TAU, DURATION
    SPEED_KEYS, LOOK_TAU = w.get("speed_keys", []), w.get("look_tau", 0.0)
    DURATION = w.get("duration")
    global FOV_V, WALK_SIZE, DOF_END
    lap = w.get("laptop", {})
    WALK_SIZE = tuple(lap.get("size", WALK_SIZE))
    FOV_V = math.degrees(2 * math.atan(math.tan(math.radians(lap.get("fov_h", 72)) / 2) * WALK_SIZE[1] / WALK_SIZE[0]))
    if VARIANT == "phone":                          # the same path, branching late to drift onto the totem
        ph = w["phone"]
        WALK = WALK[:ph["branch_after"] + 1] + [tuple(p) for p in ph["points_tail"]]
        SCREEN, END_EYE_Z, END_FOV_V = tuple(ph["screen"]), ph["end_eye_z"], ph["end_fov_v"]
        FOV_V, WALK_SIZE, DOF_END = ph["fov_v"], tuple(ph["size"]), ph.get("dof_end")


def build(root, unified=True):
    load_walk(root)
    scene = bpy.context.scene
    for name in PARTS:
        before = set(bpy.data.objects)
        mod = importlib.import_module(f"pm_areas.{name}")
        try:
            mod.build(root, unified=True)
        except TypeError:                      # an area without a unified mode yet: build it as it is
            print(f"VENUE {name} has no unified mode yet")
            mod.build(root)
        coll = bpy.data.collections.new(name)
        scene.collection.children.link(coll)
        for ob in set(bpy.data.objects) - before:
            users = list(ob.users_collection)
            if not users:                    # loaded as a template (plant models), not placed: leave it out
                continue
            for c in users:
                c.objects.unlink(ob)
            coll.objects.link(ob)
    for ob in list(bpy.data.collections["hollywood"].objects):      # hall_screen brings the screen
        if ob.name.startswith("schedule-screen"):
            bpy.data.objects.remove(ob)
    hs = importlib.import_module("pm_areas.hall_screen")
    hall, phone = hs.cameras()
    hs.fit_plants({"cam-hall": hall, "cam-hall-phone": phone})
    out = importlib.import_module("pm_areas.outside")
    if hasattr(out, "lighting"):
        out.lighting(root)
    cam = walk_camera()
    if ROOM:                                   # the room walk starts where the fly-through ends (the hall still)
        start = bpy.context.scene.frame_end
        cam.name = "cam-flythrough"
        RW = importlib.import_module("pm_areas.room_walk")
        if TOTEM:                              # the totem walks: "in" and "back" start on "to"'s last frame
            to = RW.camera(root, ROOM, VARIANT, first_frame=start, activate=TOTEM == "to", end="totem")
            if TOTEM == "to":
                rw = to
            else:
                start = RW.last_frame(to)
                bpy.data.objects.remove(to)
                rw = RW.camera(root, ROOM, VARIANT, first_frame=start, start="totem") if TOTEM == "in" else \
                    RW.camera_back(root, ROOM, VARIANT, first_frame=start, start="totem")
        elif BACK:                             # the walk back starts on the forward walk's last frame
            fw = RW.camera(root, ROOM, VARIANT, first_frame=start, activate=False)
            start = RW.last_frame(fw)
            bpy.data.objects.remove(fw)
            rw = RW.camera_back(root, ROOM, VARIANT, first_frame=start)
        else:
            rw = RW.camera(root, ROOM, VARIANT, first_frame=start)
        rw.name = "cam-walk"
    if CROWD:                                  # last: placement looks through the walk camera (who is ever seen)
        importlib.import_module("pm_areas.crowd").build(root, unified=True)
    try:                                       # BRIEF.md step 2: numbers before any render
        importlib.import_module("pm_areas.sanity").report()
    except Exception as e:                     # a report, never a reason to lose a render
        print(f"SANITY report failed: {e!r}", flush=True)


def path_points():
    """the waypoints with rounded corners, as a dense polyline on the ground"""
    pts = [Vector((x, y, 0)) for x, y in WALK]
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        d1, d2 = (b - a).normalized(), (c - b).normalized()
        r = min(FILLET, (b - a).length / 2, (c - b).length / 2)
        p0, p1 = b - d1 * r, b + d2 * r
        out.append(p0)
        for i in range(1, 12):                       # quadratic Bezier through the corner
            t = i / 12
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t * t * p1)
        out.append(p1)
    out.append(pts[-1])
    return out


def resample(poly, step):
    seg = [(poly[i + 1] - poly[i]).length for i in range(len(poly) - 1)]
    total = sum(seg)
    n = int(total / step)
    res, i, acc = [], 0, 0.0
    for k in range(n + 1):
        s = k * step
        while i < len(seg) - 1 and acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = (s - acc) / seg[i] if seg[i] else 0
        res.append(poly[i].lerp(poly[i + 1], min(1.0, t)))
    return res


def timing(pts, step):
    """seconds at each sample: a speed ramp along the path. SPEED_KEYS give the speed (m/s) at points of the walk,
    blended smoothly in between; then a forward and a backward pass limit acceleration and braking (so the camera
    never jolts), and it starts from a slow drift and settles to a stop at the end"""
    n = len(pts)
    if SPEED_KEYS:
        keys = []
        for x, y, v in SPEED_KEYS:
            i = min(range(n), key=lambda k: (pts[k].x - x) ** 2 + (pts[k].y - y) ** 2)
            keys.append((i, v))
        keys.sort()
        vt = []
        for i in range(n):
            if i <= keys[0][0]:
                vt.append(keys[0][1])
                continue
            if i >= keys[-1][0]:
                vt.append(keys[-1][1])
                continue
            for (i0, v0), (i1, v1) in zip(keys, keys[1:]):
                if i0 <= i <= i1:
                    u = (i - i0) / max(1, i1 - i0)
                    vt.append(v0 + (v1 - v0) * u * u * (3 - 2 * u))
                    break
    else:
        vt = [SPEED] * n
    base = vt

    def run(k):
        vt = [v * k for v in base]
        vt[-1] = 0.05                                      # settle to a stop; the start speed is the first key
        for i in range(1, n):                              # acceleration limit
            vt[i] = min(vt[i], math.sqrt(vt[i - 1] ** 2 + 2 * ACCEL * step))
        for i in range(n - 2, -1, -1):                     # braking limit
            vt[i] = min(vt[i], math.sqrt(vt[i + 1] ** 2 + 2 * DECEL * step))
        t, out = 0.0, [0.0]
        for i in range(1, n):
            t += step / max(0.05, 0.5 * (vt[i] + vt[i - 1]))
            out.append(t)
        return out
    if not DURATION:
        return run(1.0)
    lo, hi = 0.2, 4.0                                      # walk.json "duration" (John, 17/10: ~10 s): scale the
    for _ in range(40):                                    # speed keys until the move (before the hold) takes that
        k = (lo + hi) / 2
        if run(k)[-1] > DURATION - HOLD:
            lo = k
        else:
            hi = k
    return run(hi)


def walk_camera():
    """a camera keyed every frame along the walk (eulers kept compatible frame to frame, so motion blur never
    tumbles): a quick fly-through that eases off at the door and the steps and settles on the screen, then holds"""
    scene = bpy.context.scene
    data = bpy.data.cameras.new("cam-walk")
    data.sensor_fit, data.sensor_height = "VERTICAL", 24
    data.lens = 12 / math.tan(math.radians(FOV_V) / 2)
    data.clip_start, data.clip_end = 0.05, 1000
    cam = bpy.data.objects.new("cam-walk", data)
    scene.collection.objects.link(cam)
    step = 0.02
    pts = resample(path_points(), step)
    n = len(pts)
    L = step * (n - 1)
    ts = timing(pts, step)
    T = ts[-1]
    nf = int(math.ceil(T * FPS)) + 1
    hold = int(HOLD * FPS)
    prev, j, prev_d = None, 0, None
    look = int(LOOK_AHEAD / step)
    for f in range(nf + hold):
        t = min(T, f / FPS)
        while j < n - 2 and ts[j + 1] < t:
            j += 1
        a = (t - ts[j]) / max(1e-9, ts[j + 1] - ts[j])
        p = pts[j].lerp(pts[j + 1], max(0.0, min(1.0, a)))
        s = (j + a) * step
        w = max(0.0, min(1.0, (s - (L - 16.0)) / 12.0))
        we = w * w * (3 - 2 * w)
        eye_h = floor_z(p.x, p.y) + EYE
        if END_EYE_Z is not None:
            eye_h += (END_EYE_Z - eye_h) * we
        eye = Vector((p.x, p.y, eye_h))
        q = pts[min(n - 1, j + look)]
        tgt = Vector((q.x, q.y, floor_z(q.x, q.y) + EYE - 0.2))
        tgt = tgt.lerp(Vector(SCREEN), we)
        if START_LOOK:                              # open on the building and its sign, then level out
            w0 = max(0.0, 1.0 - s / START_LOOK_M)
            tgt = tgt.lerp(Vector(START_LOOK), w0 * w0 * (3 - 2 * w0))
        d = (tgt - eye).normalized()
        if LOOK_TAU and prev_d is not None:
            k = 1 - math.exp(-(1 / FPS) / LOOK_TAU)
            k = k + (1 - k) * we                         # no lag as it settles on the screen
            d = prev_d.lerp(d, k).normalized()
        prev_d = d
        quat = d.to_track_quat("-Z", "Y")
        rot = quat.to_euler("XYZ", prev) if prev else quat.to_euler("XYZ")
        prev = rot
        cam.location, cam.rotation_euler = eye, rot
        if END_FOV_V:                               # land on the still's lens (the hall still: 40 deg vertical)
            v = math.radians(FOV_V) + (math.radians(END_FOV_V) - math.radians(FOV_V)) * we
            data.lens = 12 / math.tan(v / 2)
            data.keyframe_insert("lens", frame=f + 1)
        if DOF_END:                                 # the phone still's shallow focus on the totem
            data.dof.use_dof = True
            data.dof.focus_distance = max(0.3, (Vector(SCREEN) - eye).length)
            data.dof.aperture_fstop = 22.0 + (DOF_END[1] - 22.0) * we
            data.dof.keyframe_insert("focus_distance", frame=f + 1)
            data.dof.keyframe_insert("aperture_fstop", frame=f + 1)
        cam.keyframe_insert("location", frame=f + 1)
        cam.keyframe_insert("rotation_euler", frame=f + 1)
    for fc in cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, "fcurves") else []:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    scene.frame_start, scene.frame_end = 1, nf + hold
    scene.render.fps = FPS
    scene.camera = cam
    print(f"WALK {L:.0f} m in {T:.1f} s + {HOLD:.1f} s hold: {scene.frame_end} frames")
    return cam
