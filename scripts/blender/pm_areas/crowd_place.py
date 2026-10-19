"""Where the venue crowd stands (called by crowd.build(root, unified=True), after the other areas are built).

Zones (NEXT.md, John's layout): the queue in the belt snake west of the grand stair (dense, three lanes, not single
file), a few at the reception counters, groups on the threshold landing, the open floor below the hall steps dense
(groups round the fridges too), the booth fronts along the middle aisle, then sparse towards the screen (high
tables, the far islands). Nothing on the steps, nothing in the end view onto the screen or the totem.

Every spot is checked against the built venue (one BVH of all its meshes): a floor at the zone's height under it,
nothing solid within a body's radius from ankle to head height, nothing overhead below 2 m, not inside a solid. People
keep >= 1 m clear of both camera paths (laptop and phone; centre distance CAM_CLEAR = body + 1 m + elbow room), and
walkers keep that clear over their whole sweep (their anchors extrapolate linearly, so they walk for the whole shot).
"""
import json
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import pm_areas.crowd as C

CAM_CLEAR = 1.4                 # person centre to the camera's path (m)
BODY_R = 0.36                   # nothing solid within this of a person's centre
GAP = 0.75                      # between two people's centres (0.62 let gesturing arms overlap)
CLONE_R = 12.0                  # the same avatar not twice within this (6 m still showed one model 3x in a long view)
SOLO_GAP = 2.5                  # someone on their own: this clear of anyone else, so two singles never read as an
                                # awkward pair (19/10: two at right angles, one staring at the other's back)
ENDING = 72                     # frames: the slow last 3 s of a clip, where the eye settles; doubles there reported
HORIZON = 450                   # frames the walkers must stay clear over (the fly-through is ~400)
REPORT = {}


# ---------------------------------------------------------------------------------- the venue as one BVH
def _see_through(ob):
    """glass and other transmissive or transparent materials: the camera sees people through them"""
    for slot in ob.material_slots:
        m = slot.material
        if not (m and m.use_nodes):
            continue
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                tw = n.inputs.get("Transmission Weight")
                al = n.inputs.get("Alpha")
                if (tw and tw.default_value > 0.01) or (al and al.default_value < 0.99):
                    return True
            if n.type in ("BSDF_GLASS", "BSDF_TRANSPARENT", "BSDF_REFRACTION"):
                return True
    return False


SEE_THROUGH = None               # per triangle of the venue BVH: True where it's glass


def venue_bvh():
    global SEE_THROUGH
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, off = [], [], 0
    glass = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.hide_render or ob.name.startswith("crowd"):
            continue
        if any(c.hide_render for c in ob.users_collection):
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n, nt = len(me.vertices), len(me.loop_triangles)
        if n and nt:
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            M = np.array(ob.matrix_world, np.float32)
            co = co @ M[:3, :3].T + M[:3, 3]
            tri = np.empty(nt * 3, np.int32)
            me.loop_triangles.foreach_get("vertices", tri)
            verts.append(co)
            polys.append(tri.reshape(-1, 3) + off)
            glass.append(np.full(nt, _see_through(ob)))
            off += n
        ev.to_mesh_clear()
    V = np.concatenate(verts)
    P = np.concatenate(polys)
    SEE_THROUGH = np.concatenate(glass)
    print(f"CROWD venue BVH: {len(P)} triangles", flush=True)
    return BVHTree.FromPolygons(V.tolist(), P.tolist(), all_triangles=True)


DIRS = [Vector((math.cos(a), math.sin(a), 0)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
DOWN, UP = Vector((0, 0, -1)), Vector((0, 0, 1))


def free(bvh, x, y, zf, r=BODY_R):
    """a person fits at (x, y) on a floor at zf"""
    loc, nrm, _, _ = bvh.ray_cast(Vector((x, y, zf + 0.6)), DOWN, 1.0)
    if loc is None or abs(loc.z - zf) > 0.06 or nrm.z < 0.7:
        return False
    loc, nrm, _, d = bvh.ray_cast(Vector((x, y, zf + 0.05)), UP, 50.0)
    if loc is not None and (nrm.z > 0.3 or d < 1.95):             # inside a solid, or something low overhead
        return False
    for h in (0.15, 0.6, 1.0, 1.45, 1.8):
        o = Vector((x, y, zf + h))
        for d in DIRS:
            if bvh.ray_cast(o, d, r)[0] is not None:
                return False
    # the footprint: straight down from 2.1 m over the body's circle, the first thing hit must be the floor (a high
    # table's top or frame between the horizontal rays let a person stand inside it, 16/10 critic)
    for k in range(17):
        rr = 0.0 if k == 0 else (r * 0.85 if k <= 8 else r * 0.45)
        a = (k % 8) * math.pi / 4 + (0.0 if k <= 8 else math.pi / 8)
        loc = bvh.ray_cast(Vector((x + rr * math.cos(a), y + rr * math.sin(a), zf + 2.1)), DOWN, 2.3)[0]
        if loc is None or loc.z > zf + 0.06:
            return False
    return True


# ---------------------------------------------------------------------------------- the camera paths
def camera_paths(root):
    import pm_areas.venue as V
    w = json.loads((root / "data" / "photomatch" / "walk.json").read_text())
    saved = V.WALK, V.FILLET
    V.FILLET = w["fillet"]
    pts = [tuple(p) for p in w["points"]]
    V.WALK = pts
    lap = [(p.x, p.y) for p in V.path_points()]
    ph = w["phone"]
    V.WALK = pts[:ph["branch_after"] + 1] + [tuple(p) for p in ph["points_tail"]]
    phone = [(p.x, p.y) for p in V.path_points()]
    V.WALK, V.FILLET = saved
    import pm_areas.room_walk as RW
    segs = []
    for poly in [lap, phone] + RW.all_paths(root):
        segs += list(zip(poly, poly[1:]))
    return np.array([[a[0], a[1], b[0], b[1]] for a, b in segs])


def path_dist(S, x, y):
    ax, ay, bx, by = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-9), 0, 1)
    return float(np.min(np.hypot(ax + t * dx - x, ay + t * dy - y)))


# ---------------------------------------------------------------------------------- what the camera sees
VIS_MARGIN = math.radians(10)   # past the frame edges: shadows and blur of people just outside still show
VIS_PAD = 10                    # frames kept on either side of a visible stretch (blur samples, no pop-in at whips)
VIS_RANGE = 60.0                # m: past this a person in the frame is a few pixels; nearer, the render switch-on goes
                                # by the frame alone, not by line of sight (John 17/10: people popped in on the walk
                                # back where a wrong occlusion verdict switched them on late: "make sure the crowd
                                # loads before the camera points their way")
VIS_STEP = 2                    # test every 2nd frame (the pad covers the gaps)


class View:
    """the walk camera frame by frame (read from its curves): which frames see a point, past the venue's walls"""
    def __init__(self, bvh, cam=None):
        import pm_areas.venue as V
        scene = bpy.context.scene
        cam = cam or bpy.data.objects["cam-walk"]
        fcs = {}
        for owner in (cam, cam.data):
            ad = owner.animation_data
            if ad and ad.action:
                for l in ad.action.layers:
                    for st in l.strips:
                        for cb in st.channelbags:
                            for fc in cb.fcurves:
                                fcs[(fc.data_path, fc.array_index)] = fc
        from mathutils import Euler
        self.bvh = bvh
        keys = [k.co.x for k in fcs[("location", 0)].keyframe_points]
        self.f0, self.f1 = int(min(keys)), int(max(keys))
        self.frames = list(range(self.f0, self.f1 + 1, VIS_STEP))
        locs, axes, tans = [], [], []
        aspect = V.WALK_SIZE[0] / V.WALK_SIZE[1]
        for f in self.frames:
            loc = [fcs[("location", i)].evaluate(f) for i in range(3)]
            R = Euler([fcs[("rotation_euler", i)].evaluate(f) for i in range(3)], "XYZ").to_matrix()
            lens = fcs[("lens", 0)].evaluate(f) if ("lens", 0) in fcs else cam.data.lens
            tv = math.tan(math.atan(12 / lens) + VIS_MARGIN)                 # vertical sensor fit, 24 mm
            th = math.tan(math.atan(12 / lens * aspect) + VIS_MARGIN)
            locs.append(loc)
            axes.append([list(R.col[0]), list(R.col[1]), list(-R.col[2])])  # right, up, forward
            tans.append((th, tv))
        self.loc, self.axes, self.tans = np.array(locs), np.array(axes), np.array(tans)

    def clear(self, o, d, dist):
        return _clear(self.bvh, o, d, dist)

    def seen(self, pts_at, occlusion=True):
        """frames (sampled) in which any of a person's points is in the widened frame and not behind the venue;
        pts_at(f) gives the points (n x 3) at frame f. occlusion=False: in the widened frame within VIS_RANGE, walls
        or not (the render switch-on: being on early costs render time, being on late is a pop)"""
        out = []
        for i, f in enumerate(self.frames):
            P = pts_at(f)
            v = P - self.loc[i]
            right, up, fwd = self.axes[i]
            z = v @ fwd
            ok = z > 0.2
            if not ok.any():
                continue
            th, tv = self.tans[i]
            inside = ok & (np.abs(v @ right) < th * z) & (np.abs(v @ up) < tv * z)
            for k in np.nonzero(inside)[0]:
                d = float(np.linalg.norm(v[k]))
                if not occlusion:
                    if d < VIS_RANGE:
                        out.append(f)
                        break
                    continue
                dirv = Vector(v[k] / d)
                if self.clear(Vector(self.loc[i]), dirv, d - 0.25):
                    out.append(f)
                    break
        return out


def _clear(bvh, o, d, dist):
    """nothing opaque on the ray (glass doesn't count: people show through the facade)"""
    for _ in range(8):
        loc, _n, idx, hd = bvh.ray_cast(o, d, dist)
        if loc is None:
            return True
        if SEE_THROUGH is None or not SEE_THROUGH[idx]:
            return False
        o, dist = loc + d * 0.01, dist - hd - 0.01
        if dist <= 0:
            return True
    return False


def other_views(bvh, root):
    """every walk camera other than the active one, for placing one crowd that every clip shares: the fly-through and
    the eight room walks there and back of this variant (temporary cameras, removed once their views are measured)"""
    import pm_areas.venue as V
    import pm_areas.room_walk as RW
    fly = bpy.data.objects.get("cam-flythrough") or bpy.data.objects.get("cam-walk")
    keys = [k.co.x for k in fly.animation_data.action.layers[0].strips[0].channelbags[0].fcurves[0].keyframe_points]
    fly_end = int(max(keys))
    views, tmp = [], []
    if fly.name == "cam-flythrough":
        views.append(View(bvh, fly))
    for n in (3, 4, 5, 6, 7, 8, 9, 10):              # each room's walk there and its walk back (17/10)
        c = RW.camera(root, n, V.VARIANT, first_frame=fly_end, activate=False)
        tmp.append(c)
        if not (V.ROOM == n and not V.BACK):
            views.append(View(bvh, c))
        b = RW.camera_back(root, n, V.VARIANT, first_frame=RW.last_frame(c), activate=False)
        tmp.append(b)
        if not (V.ROOM == n and V.BACK):
            views.append(View(bvh, b))
    for c in tmp:
        bpy.data.objects.remove(c)
    print(f"CROWD views: the active camera + {len(views)} others", flush=True)
    return views


def body_points(x, y, zf):
    return np.array([(x, y, zf + 0.25), (x, y, zf + 1.0), (x, y, zf + 1.65), (x + 0.25, y, zf + 1.2), (x - 0.25, y, zf + 1.2)])


# ---------------------------------------------------------------------------------- placing
class Placer:
    def __init__(self, crowd, root):
        import time
        self.crowd, self.rng = crowd, crowd.rng
        t0 = time.time()
        self.bvh = venue_bvh()
        t1 = time.time()
        self.paths = camera_paths(root)
        self.spots = []                                  # (x, y) of everyone placed, walkers' sweeps sampled
        self.looks = []                                  # (x, y, avatar) for keeping clones apart
        self.view = View(self.bvh) if "cam-walk" in bpy.data.objects else None
        self.others = other_views(self.bvh, root) if self.view else []
        # --both (venue.BOTH): the walk back renders from this build too. It only widens the render switch-on
        # (seen_at); every placement decision still goes by the walk there's camera, so the people are the ones a
        # separate build of either clip places (the counts per zone match clip to clip in the 18/10 logs)
        back = bpy.data.objects.get("cam-walk-back")
        self.back = View(self.bvh, back) if self.view and back else None
        print(f"CROWD timing: venue BVH {t1 - t0:.0f} s, camera views {time.time() - t1:.0f} s", flush=True)
        self.unseen = 0                                  # spots skipped: no walk camera ever sees them
        self.zone = ""

    def end_view(self, x, y):
        """the last stretch looks onto the screen (laptop) and the totem (phone): keep it empty"""
        return y > 6.5 and -3.0 < x < 9.5

    def ok(self, x, y, zf, gap=GAP):
        if self.end_view(x, y) or path_dist(self.paths, x, y) < CAM_CLEAR:
            return False
        if any((x - sx) ** 2 + (y - sy) ** 2 < gap * gap for sx, sy in self.spots):
            return False
        return free(self.bvh, x, y, zf)

    def pick(self, role, x, y, sex=None):
        """an avatar and clip for a role: an avatar nobody within CLONE_R wears, else the one whose nearest double is
        farthest. 20 avatars for ~240 people: in the busy hall 'none within CLONE_R' often runs out, and the old
        fallback (whatever the 12th draw gave) stood two identical women side by side at the fly-through's end (John
        19/10). Clones show in looks far more than in motion (McDonnell et al., 'Clone attack!', 2008)."""
        crowd, rng = self.crowd, self.rng
        pool = [t for t in crowd.templates if sex is None or t["sex"] == sex]
        rng.shuffle(pool)
        def nearest(t):
            return min(((sx - x) ** 2 + (sy - y) ** 2 for sx, sy, n in self.looks if n == t["name"]), default=1e18)
        free_ = [t for t in pool if nearest(t) >= CLONE_R ** 2]
        tmpl = free_[0] if free_ else max(pool, key=nearest)
        clips = [c for c in C.CLIPS[role] if f'{tmpl["sex"]}_{c}' in crowd.clips]
        clip = f'{tmpl["sex"]}_{rng.choice(clips)}' if clips else f'{tmpl["sex"]}_idle_neutral_01'
        return tmpl, clip

    def seen_at(self, x, y, zf):
        """frames the active camera sees the spot; None without a camera. A spot no walk camera sees at all comes back
        as [] (skipped); a spot only other clips see comes back as [None] (placed, hidden in this clip)"""
        if self.view is None:
            return None
        pts = body_points(x, y, zf)
        if self.view.seen(lambda f: pts):                          # placed where some clip has a line of sight,
            vis = self.view.seen(lambda f: pts, occlusion=False)   # switched on whenever this clip's frame holds it
        elif any(v.seen(lambda f: pts) for v in self.others):
            vis = self.view.seen(lambda f: pts, occlusion=False) or [None]
        else:
            return []
        return vis

    def widen(self, vis, at):
        """--both: the render switch-on frames widened by the walk back's camera (at(f): the person's points at
        frame f); after the skip decision, so forced group members and walkers get them too"""
        if self.back is None or vis is None:
            return vis
        more = self.back.seen(at, occlusion=False)
        return sorted({f for f in vis if f is not None} | set(more)) if more else vis

    def put(self, role, x, y, zf, yaw, sex=None, force=False):
        """place someone; False (and nobody placed) when the camera never sees the spot, unless forced (a group
        member whose group is seen)"""
        crowd, rng = self.crowd, self.rng
        vis = self.seen_at(x, y, zf)
        if vis is not None and not vis and not force:
            self.unseen += 1
            return False
        vis = self.widen(vis, lambda f: body_points(x, y, zf))
        tmpl, clip = self.pick(role, x, y, sex)
        crowd.person(tmpl, clip, x, y, zf, yaw, offset=rng.randrange(0, 600), speed=rng.uniform(0.9, 1.1),
                     height=rng.uniform(0.96, 1.04), badge=rng.random() < 0.85, role=role,
                     backpack=rng.random() < C.BACKPACK_SHARE)
        self.looks.append((x, y, tmpl["name"]))
        crowd.people[-1]["avatar"], crowd.people[-1]["at"] = tmpl["name"], (x, y)
        crowd.people[-1]["near_cam"] = path_dist(self.paths, x, y)
        crowd.people[-1]["vis"] = vis
        self.spots.append((x, y))
        REPORT[self.zone] = REPORT.get(self.zone, 0) + 1
        return True

    def face_something(self, x, y):
        """someone on their own faces the walkway, watching people go by: a purpose a viewer reads at a glance.
        (Facing the nearest person made one-sided pairs: a stare at someone's back or side, 19/10. Conversations are
        groups, which face their own centre: a ring, face to face or an L round a shared space, Kendon's F-formations.)"""
        S = self.paths
        ax, ay, bx, by = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
        dx, dy = bx - ax, by - ay
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-9), 0, 1)
        px, py = ax + t * dx, ay + t * dy
        i = int(np.argmin(np.hypot(px - x, py - y)))
        return self.facing(px[i] - x, py[i] - y)

    @staticmethod
    def facing(dx, dy):
        return math.atan2(dx, -dy)

    def group(self, cx, cy, zf, n=None):
        """2-4 people round a centre facing it (one talks, the others listen); all or nothing. Each group keeps its
        own distance from the camera's path (1.4-2.4 m), so the walkway's edge isn't a line of people"""
        rng = self.rng
        if path_dist(self.paths, cx, cy) < CAM_CLEAR + rng.uniform(0.6, 1.4):
            return False
        n = n or rng.choice((2, 2, 3, 3, 3, 4))
        rad = 0.42 + 0.09 * n
        a0 = rng.uniform(0, 2 * math.pi)
        spots = []
        for k in range(n):
            a = a0 + 2 * math.pi * k / n + rng.uniform(-0.25, 0.25)
            r = rad * rng.uniform(0.92, 1.1)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if not self.ok(x, y, zf) or any((x - p) ** 2 + (y - q) ** 2 < GAP ** 2 for p, q, _ in spots):
                return False
            spots.append((x, y, self.facing(cx - x, cy - y) + rng.uniform(-0.2, 0.2)))
        if self.view is not None and not any(self.seen_at(x, y, zf) for x, y, _ in spots):   # one crowd for every clip
            self.unseen += n
            return False
        talker = rng.randrange(n)
        for k, (x, y, yaw) in enumerate(spots):
            self.put("talk" if k == talker or (n == 2 and rng.random() < 0.5) else "listen", x, y, zf, yaw, force=True)
        return True

    def scatter(self, box, zf, groups, singles=0, single_role="idle", face=None, tries=400):
        """groups and singles at random spots in an (x0, y0, x1, y1) box; face(x, y) -> yaw for singles"""
        rng = self.rng
        x0, y0, x1, y1 = box
        placed = 0
        for _ in range(tries):
            if placed >= groups:
                break
            if self.group(rng.uniform(x0, x1), rng.uniform(y0, y1), zf):
                placed += 1
        s = 0
        for _ in range(tries):
            if s >= singles:
                break
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if self.ok(x, y, zf, gap=SOLO_GAP):
                yaw = face(x, y) if face else self.face_something(x, y)
                if self.put(single_role, x, y, zf, yaw + rng.uniform(-0.3, 0.3)):
                    s += 1

    def walker(self, x, y, zf, heading, bounds):
        """someone walking along heading (radians, 0 = +y) from (x, y); the whole sweep over HORIZON frames stays
        inside bounds and clear"""
        crowd, rng = self.crowd, self.rng
        tmpl, clip = self.pick("walk", x, y)
        speed = rng.uniform(0.9, 1.1)
        v = (crowd.clips[clip].get("speed", 1.2) or 1.2) * speed
        L = v * HORIZON / C.FPS
        dx, dy = math.sin(heading), math.cos(heading)
        bx0, by0, bx1, by1 = bounds
        n = max(2, int(L / 0.5))
        pts = [(x + dx * L * k / n, y + dy * L * k / n) for k in range(n + 1)]
        if not all(bx0 <= px <= bx1 and by0 <= py <= by1 for px, py in pts):
            return False
        for px, py in pts:
            if not self.ok(px, py, zf, gap=0.8):
                return False
        frames = 1 + L / v * C.FPS
        vis = None
        if self.view is not None:
            ex, ey = pts[-1]
            def at(f):
                t = (f - 1) / max(1.0, frames - 1)
                return body_points(x + (ex - x) * t, y + (ey - y) * t, zf)
            if not (self.view.seen(at) or any(v.seen(at) for v in self.others)):
                self.unseen += 1
                return False
            vis = self.widen(self.view.seen(at, occlusion=False) or [None], at)
        crowd.person(tmpl, clip, x, y, zf, self.facing(dx, dy), offset=rng.randrange(0, 600), speed=speed,
                     height=rng.uniform(0.96, 1.04), walk=((x, y), pts[-1], frames), badge=rng.random() < 0.85,
                     role="walk", backpack=rng.random() < C.BACKPACK_SHARE)
        crowd.people[-1]["avatar"], crowd.people[-1]["at"] = tmpl["name"], (x, y)
        crowd.people[-1]["near_cam"] = min(path_dist(self.paths, px, py) for px, py in pts)
        crowd.people[-1]["vis"] = vis
        self.spots += pts
        self.looks.append((x, y, tmpl["name"]))
        REPORT[self.zone] = REPORT.get(self.zone, 0) + 1
        return True

    def walkers(self, n, box, zf, headings, bounds, tries=200):
        rng = self.rng
        x0, y0, x1, y1 = box
        done = 0
        for _ in range(tries):
            if done >= n:
                break
            if self.walker(rng.uniform(x0, x1), rng.uniform(y0, y1), zf, rng.choice(headings) + rng.uniform(-0.06, 0.06),
                           bounds):
                done += 1


# ---------------------------------------------------------------------------------- the zones
RECEPTION_Z, HALL_Z = 1.2, 0.0
LANES = (-11.65, -10.35, -9.05)         # between the belt lines of entrance.queue_west (x -12.3, -11.0, -9.7, -8.4)
LANE_Y = (-56.6, -47.4)


def queue(P):
    """the belt snake: the exit lane (east, nearest the walk) full, the middle one full, the first two-thirds full;
    loose spacing, some side by side, some turned to talk to the one behind"""
    P.zone = "queue"
    rng = P.rng
    fill = {LANES[2]: 1.0, LANES[1]: 1.0, LANES[0]: 0.65}
    for li, lx in enumerate(LANES):
        north = li != 1                                 # the lanes alternate direction
        y = LANE_Y[1] if north else LANE_Y[0]
        stop = LANE_Y[0] + (LANE_Y[1] - LANE_Y[0]) * (1 - fill[lx]) if north else LANE_Y[1]
        s = -1 if north else 1
        while (y > stop) if north else (y < stop):
            fwd = math.pi if north else 0.0                     # facing along the lane towards its exit (yaw 0 faces -y)
            abreast = rng.random() < 0.18
            xs = (lx - 0.33, lx + 0.33) if abreast else (lx + rng.uniform(-0.2, 0.2),)
            for x in xs:
                if P.ok(x, y, RECEPTION_Z, gap=0.65):
                    turn = rng.random()
                    if turn < 0.22:                             # talking to the one behind
                        yaw, role = fwd + math.pi + rng.uniform(-0.6, 0.6), "talk"
                    elif turn < 0.4:
                        yaw, role = fwd + rng.choice((-1, 1)) * rng.uniform(0.6, 1.3), "listen"
                    else:
                        yaw, role = fwd + rng.uniform(-0.35, 0.35), "wait"
                    P.put(role, x, y, RECEPTION_Z, yaw)
            y += s * rng.uniform(0.7, 1.1)


def reception(P):
    """one or two at the two counters nearest the queue's exit, on their open side"""
    P.zone = "reception"
    rng = P.rng
    desks = []
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH" and ob.name.startswith("plan-desk"):
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
            y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
            desks.append((math.hypot((x0 + x1) / 2 - LANES[2], (y0 + y1) / 2 - LANE_Y[1]), (x0, y0, x1, y1)))
    for _, (x0, y0, x1, y1) in sorted(desks)[:2]:
        sides = [((x0 + x1) / 2, y0 - 0.55, (0, 1)), ((x0 + x1) / 2, y1 + 0.55, (0, -1)),
                 (x0 - 0.55, (y0 + y1) / 2, (1, 0)), (x1 + 0.55, (y0 + y1) / 2, (-1, 0))]
        rng.shuffle(sides)
        n = rng.choice((1, 2))
        for cx, cy, (fx, fy) in sides:
            if n == 0:
                break
            if P.ok(cx, cy, RECEPTION_Z):
                P.put(rng.choice(("wait", "talk")), cx, cy, RECEPTION_Z, P.facing(fx, fy) + rng.uniform(-0.2, 0.2))
                n -= 1


def foyer(P):
    """between the queue and the stair, and on the threshold landing: a few groups, a few heading for the hall"""
    P.zone = "foyer"
    P.scatter((-5.6, -58.0, -3.2, -40.0), RECEPTION_Z, groups=2, singles=2)
    P.walkers(2, (-5.2, -58.5, -3.6, -52.0), RECEPTION_Z, (0.0,), (-6.0, -59.5, -3.0, -37.6))
    P.zone = "landing"
    P.scatter((-10.0, -37.2, 8.6, -34.8), RECEPTION_Z, groups=5, singles=3)


def below_steps(P):
    """the open floor between the steps and the booth blocks: dense; and round the fridges"""
    P.zone = "below-steps"
    P.scatter((-10.2, -31.8, 8.9, -25.2), HALL_Z, groups=9, singles=4)
    P.zone = "fridges"
    for fx, fy in ((-4.0, -21.8), (2.82, -21.8)):
        P.scatter((fx - 1.6, fy - 2.4, fx + 1.6, fy - 0.9), HALL_Z, groups=1, singles=1, single_role="idle",
                  face=lambda x, y, fx=fx, fy=fy: P.facing(fx - x, fy - y))


def aisle(P):
    """the middle aisle between the booth blocks (x -6.0 .. 4.7, y -24.7 .. -4.5): people at the booth fronts
    looking in, groups between them and the walk, people walking both ways"""
    import pm_areas.hollywood as H
    P.zone = "booth-fronts"
    rng = P.rng
    ys = H.BLOCK_Y
    for xe, face in ((H.BLOCK_L[2] + 0.75, -1), (H.BLOCK_R[2] - 0.75, 1)):
        for b0, b1 in zip(ys, ys[1:]):
            for _ in range(rng.choice((2, 2, 3, 3))):
                for _ in range(30):
                    x, y = xe + rng.uniform(-0.15, 1.05) * -face, rng.uniform(b0 + 0.6, b1 - 0.6)   # varied: not a row
                    if P.ok(x, y, HALL_Z):
                        P.put(rng.choice(("idle", "listen", "idle")), x, y, HALL_Z,
                              P.facing(face, 0) + rng.uniform(-0.5, 0.5))
                        break
    P.zone = "aisle"
    P.scatter((H.BLOCK_L[2] + 1.0, -24.0, H.BLOCK_R[2] - 1.0, -14.0), HALL_Z, groups=4)
    P.scatter((H.BLOCK_L[2] + 1.0, -14.0, H.BLOCK_R[2] - 1.0, -4.5), HALL_Z, groups=5)   # the north half read empty (16/10 critic)
    bounds = (H.BLOCK_L[2] + 0.4, -31.0, H.BLOCK_R[2] - 0.4, 6.0)
    P.walkers(3, (H.BLOCK_L[2] + 0.6, -26.0, -2.4, -14.0), HALL_Z, (0.0,), bounds)
    P.walkers(3, (0.8, -14.0, H.BLOCK_R[2] - 0.6, -2.0), HALL_Z, (math.pi,), bounds)


def far_hall(P):
    """north of the islands: sparse; people round the high tables by the side walls, a few groups by the far
    islands, a couple walking"""
    P.zone = "far"
    rng = P.rng
    for tx, ty in ((-21.0, 2.0), (-21.2, 6.0), (-21.0, 14.5), (20.8, 13.0), (20.9, 15.6)):
        n = rng.choice((0, 2, 2, 3))
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(n):
            a = a0 + 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
            x, y = tx + 0.75 * math.cos(a), ty + 0.75 * math.sin(a)
            if P.ok(x, y, HALL_Z):
                P.put("talk" if k == 0 else "listen", x, y, HALL_Z, P.facing(tx - x, ty - y))
    P.scatter((-11.0, -3.5, -2.5, 6.0), HALL_Z, groups=4, singles=2)       # 2 + 2 read deserted (16/10 critic)
    P.scatter((2.5, -3.5, 14.0, 6.0), HALL_Z, groups=4, singles=2)
    P.walkers(2, (-9.0, -3.5, -4.0, 4.0), HALL_Z, (math.pi / 2, -math.pi / 2), (-11.5, -4.0, -2.4, 9.0))
    # thinning out, not a closed hall: a few either side of the end view onto the screen and the totem
    P.scatter((-12.0, 6.5, -3.6, 16.5), HALL_Z, groups=2, singles=2)
    P.scatter((10.0, 6.5, 16.0, 16.5), HALL_Z, groups=1, singles=2)
    # between the stairwells, west of the screen's axis: the walks back cross the hall here looking west (it read empty,
    # 17/10); kept south of the hall still's camera (y 9.81) so nobody stands between it and the screen
    # the fly-through's slow ending looks up this stretch at the screen: singles here read the programme on it
    import pm_areas.hall_screen as HS
    P.scatter((-4.2, 3.5, 1.0, 9.3), HALL_Z, groups=2, singles=2,
              face=lambda x, y: P.facing(HS.SCREEN["x"] - x, HS.SCREEN["y"] - y))


def upstairs(P):
    """floor 1: groups along the corridor (by the tables, outside the doors), people walking both ways; the lanes the
    room walks take stay clear (CAM_CLEAR from every walk path)"""
    P.zone = "upstairs"
    zf = 6.2
    P.scatter((-6.3, -45.0, 11.7, -20.0), zf, groups=10, singles=5, tries=1200)      # round the tables, rooms 4-8
    P.scatter((-6.3, -20.0, 11.7, 0.0), zf, groups=7, singles=4, tries=1200)         # the stair tops, rooms 4/9
    P.scatter((-6.3, 0.0, 11.7, 30.0), zf, groups=8, singles=4, tries=1200)          # the north stretch, rooms 2/3/10/11
    P.walkers(8, (-6.0, -44.0, 11.4, 24.0), zf, (0.0, math.pi), (-6.6, -46.5, 12.0, 32.0), tries=600)


def place(crowd, root):
    import pm_areas.venue as V
    sc = bpy.context.scene
    f_was = sc.frame_current
    if V.BACK and "cam-walk" in bpy.data.objects:   # the walk back starts in the auditorium, where the hall side is
        import pm_areas.room_walk as RW          # out of render: measure the venue on its last frame (the hall still)
        sc.frame_set(RW.last_frame(bpy.data.objects["cam-walk"]))   # or every hall spot fails free() (17/10: no hall crowd)
    P = Placer(crowd, root)
    sc.frame_set(f_was)
    import time
    t0 = time.time()
    for zone in (queue, reception, foyer, below_steps, aisle, far_hall, upstairs):
        zone(P)
    print("CROWD placed: " + ", ".join(f"{k} {v}" for k, v in REPORT.items())
          + f"; {P.unseen} spots skipped (never in view)", flush=True)
    print(f"CROWD timing: zones placed in {time.time() - t0:.0f} s", flush=True)
    doubles_in_ending(crowd, sc.frame_end)
    return P


def doubles_in_ending(crowd, f_end):
    """the same avatar twice in the clip's slow last ENDING frames, within 15 m of each other: reported (there the eye
    has time to find them)"""
    seen = [p for p in crowd.people if p.get("avatar") and any(f is not None and f > f_end - ENDING for f in (p.get("vis") or []))]
    pairs = [(a, b) for i, a in enumerate(seen) for b in seen[i + 1:] if a["avatar"] == b["avatar"]
             and (a["at"][0] - b["at"][0]) ** 2 + (a["at"][1] - b["at"][1]) ** 2 < 15 ** 2]
    print(f"CROWD ending: {len(seen)} people in the last {ENDING} frames, {len(pairs)} doubles within 15 m"
          + "".join(f"; {a['avatar']} at ({a['at'][0]:.1f}, {a['at'][1]:.1f}) and ({b['at'][0]:.1f}, {b['at'][1]:.1f})"
                    for a, b in pairs), flush=True)


def _tree(ob):
    out = [ob]
    for c in ob.children:
        out += _tree(c)
    return out


def hide_unseen(crowd):
    """each person renders only in the frames the camera can see them (+ VIS_PAD): out of render otherwise, so
    their skeleton and the accessories' wrap aren't evaluated for frames nobody sees (John, 16/10: "anything the
    camera isn't looking at isn't important")"""
    scene = bpy.context.scene
    f0, f1 = scene.frame_start, scene.frame_end
    shown = total = 0
    for p in crowd.people:
        vis = p.get("vis")
        if vis is None:
            continue
        on = np.zeros(f1 - f0 + 1, bool)
        for f in (f for f in vis if f is not None):
            on[max(0, f - f0 - VIS_PAD - VIS_STEP): min(len(on), f - f0 + VIS_PAD + VIS_STEP + 1)] = True
        shown += int(on.sum())
        total += len(on)
        keys = [(f0, not on[0])] + [(f0 + i, not on[i]) for i in range(1, len(on)) if on[i] != on[i - 1]]
        for ob in _tree(p["rig"]):
            for f, hidden in keys:
                ob.hide_render = hidden
                ob.keyframe_insert("hide_render", frame=f)
    if total:
        print(f"CROWD visibility: people render {100 * shown / total:.0f}% of the frames on average", flush=True)
