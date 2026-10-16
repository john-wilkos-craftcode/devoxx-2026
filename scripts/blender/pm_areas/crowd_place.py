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
HORIZON = 450                   # frames the walkers must stay clear over (the fly-through is ~400)
REPORT = {}


# ---------------------------------------------------------------------------------- the venue as one BVH
def venue_bvh():
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, off = [], [], 0
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
            off += n
        ev.to_mesh_clear()
    V = np.concatenate(verts)
    P = np.concatenate(polys)
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
    segs = []
    for poly in (lap, phone):
        segs += list(zip(poly, poly[1:]))
    return np.array([[a[0], a[1], b[0], b[1]] for a, b in segs])


def path_dist(S, x, y):
    ax, ay, bx, by = S[:, 0], S[:, 1], S[:, 2], S[:, 3]
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-9), 0, 1)
    return float(np.min(np.hypot(ax + t * dx - x, ay + t * dy - y)))


# ---------------------------------------------------------------------------------- placing
class Placer:
    def __init__(self, crowd, root):
        self.crowd, self.rng = crowd, crowd.rng
        self.bvh = venue_bvh()
        self.paths = camera_paths(root)
        self.spots = []                                  # (x, y) of everyone placed, walkers' sweeps sampled
        self.looks = []                                  # (x, y, avatar) for keeping clones apart
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
        """an avatar and clip for a role, avoiding an avatar already standing within CLONE_R"""
        near = {n for (sx, sy, n) in self.looks if (sx - x) ** 2 + (sy - y) ** 2 < CLONE_R ** 2}
        for _ in range(12):
            tmpl, clip = C.pick(self.crowd, role, sex)
            if tmpl["name"] not in near:
                break
        self.looks.append((x, y, tmpl["name"]))
        return tmpl, clip

    def put(self, role, x, y, zf, yaw, sex=None):
        crowd, rng = self.crowd, self.rng
        tmpl, clip = self.pick(role, x, y, sex)
        crowd.person(tmpl, clip, x, y, zf, yaw, offset=rng.randrange(0, 600), speed=rng.uniform(0.9, 1.1),
                     height=rng.uniform(0.96, 1.04), badge=rng.random() < 0.85, role=role,
                     backpack=rng.random() < C.BACKPACK_SHARE)
        self.spots.append((x, y))
        REPORT[self.zone] = REPORT.get(self.zone, 0) + 1

    def face_something(self, x, y):
        """someone on their own faces the nearest person within 3.5 m, else the walkway"""
        best = None
        for sx, sy in self.spots:
            d = (sx - x) ** 2 + (sy - y) ** 2
            if 0.01 < d < 3.5 ** 2 and (best is None or d < best[0]):
                best = (d, sx, sy)
        if best:
            return self.facing(best[1] - x, best[2] - y)
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
        talker = rng.randrange(n)
        for k, (x, y, yaw) in enumerate(spots):
            self.put("talk" if k == talker or (n == 2 and rng.random() < 0.5) else "listen", x, y, zf, yaw)
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
            if self.ok(x, y, zf, gap=0.9):
                yaw = face(x, y) if face else self.face_something(x, y)
                self.put(single_role, x, y, zf, yaw + rng.uniform(-0.3, 0.3))
                s += 1

    def walker(self, x, y, zf, heading, bounds):
        """someone walking along heading (radians, 0 = +y) from (x, y); the whole sweep over HORIZON frames stays
        inside bounds and clear"""
        crowd, rng = self.crowd, self.rng
        tmpl, clip = C.pick(crowd, "walk")
        near = {n for (sx, sy, n) in self.looks if (sx - x) ** 2 + (sy - y) ** 2 < CLONE_R ** 2}
        for _ in range(12):
            if tmpl["name"] not in near:
                break
            tmpl, clip = C.pick(crowd, "walk")
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
        crowd.person(tmpl, clip, x, y, zf, self.facing(dx, dy), offset=rng.randrange(0, 600), speed=speed,
                     height=rng.uniform(0.96, 1.04), walk=((x, y), pts[-1], frames), badge=rng.random() < 0.85,
                     role="walk", backpack=rng.random() < C.BACKPACK_SHARE)
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


def place(crowd, root):
    P = Placer(crowd, root)
    for zone in (queue, reception, foyer, below_steps, aisle, far_hall):
        zone(P)
    print("CROWD placed: " + ", ".join(f"{k} {v}" for k, v in REPORT.items()), flush=True)
    return P
