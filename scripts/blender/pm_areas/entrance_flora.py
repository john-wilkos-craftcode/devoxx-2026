"""Procedural plants for the entrance: potted palms (Kentia-like fronds of narrow leaflets) and trailing hanging
greenery (pothos strands). Each returns one joined mesh object; leaves are single-sided small polygons."""
import math
import random

import pm_lib as L


def _leaf(verts, faces, base, along, side, length, width):
    """a narrow diamond leaf from base along unit vector 'along', widened along 'side'"""
    i = len(verts)
    tip = [base[k] + along[k] * length for k in range(3)]
    mid = [base[k] + along[k] * length * 0.45 for k in range(3)]
    verts += [tuple(base), tuple(mid[k] + side[k] * width for k in range(3)), tuple(tip),
              tuple(mid[k] - side[k] * width for k in range(3))]
    faces.append((i, i + 1, i + 2, i + 3))


def palm(name, x, y, height=1.6, spread=0.9, fronds=11, seed=1, pot=None, pot_h=0.45, pot_r=0.22, material=None, z0=0.0):
    """a palm in a pot standing on the floor at z0: fronds arch out and down from a crown at pot top + 0.15 m"""
    rnd = random.Random(seed)
    verts, faces = [], []
    leaf_mat = material or L.mat("palm-leaf", 0x40602c, 0.55, bump=0.2)
    crown = (x, y, z0 + pot_h + 0.15)
    for f in range(fronds):
        az = 2 * math.pi * f / fronds + rnd.uniform(-0.3, 0.3)
        up = rnd.uniform(0.9, 1.35)                       # initial steepness
        ln = height * rnd.uniform(0.7, 1.0)
        n = 14
        prev = list(crown)
        pts = []
        for k in range(n + 1):
            t = k / n
            r = spread * ln / height * t
            z = crown[2] + ln * (math.sin(up) * t - 0.55 * t * t)
            pts.append((x + r * math.cos(az), y + r * math.sin(az), z))
        for k in range(1, n):
            p, q = pts[k], pts[k + 1]
            d = [q[i] - p[i] for i in range(3)]
            dl = math.sqrt(sum(c * c for c in d)) or 1
            d = [c / dl for c in d]
            side = (-math.sin(az), math.cos(az), 0)
            for s in (-1, 1):
                ll = 0.32 * math.sin(math.pi * (k / n)) + 0.06
                droop = (side[0] * s * 0.8 + d[0] * 0.35, side[1] * s * 0.8 + d[1] * 0.35, -0.45)
                dn = math.sqrt(sum(c * c for c in droop))
                droop = tuple(c / dn for c in droop)
                _leaf(verts, faces, p, droop, d, ll, 0.018)
        # rachis
        for k in range(n):
            p, q = pts[k], pts[k + 1]
            i = len(verts)
            verts += [p, q, (q[0], q[1], q[2] + 0.012), (p[0], p[1], p[2] + 0.012)]
            faces.append((i, i + 1, i + 2, i + 3))
    ob = L.mesh_obj(name, verts, faces, leaf_mat)
    pm = pot or L.mat("pot-black", 0x1a1a1a, 0.5)
    L.cylinder(name + "-pot", x, y, z0, z0 + pot_h, pot_r, pm, r_top=pot_r * 1.1)
    return ob


def hanging(name, x0, y0, x1, y1, z_top, length=0.8, strands=14, seed=3, leaf=0.05, material=None):
    """trailing greenery hanging from a line (x0,y0)-(x1,y1) at z_top: strands of small leaves"""
    rnd = random.Random(seed)
    verts, faces = [], []
    m = material or L.mat("pothos", 0x3f6a2c, 0.5, bump=0.15)
    for s in range(strands):
        t = rnd.random()
        bx, by = x0 + (x1 - x0) * t + rnd.uniform(-0.12, 0.12), y0 + (y1 - y0) * t + rnd.uniform(-0.12, 0.12)
        ln = length * rnd.uniform(0.4, 1.0)
        nleaves = int(ln / 0.035)
        for k in range(nleaves):
            z = z_top - ln * k / nleaves
            ang = rnd.uniform(0, 2 * math.pi)
            sway = 0.04 * math.sin(k * 0.7 + s)
            base = (bx + sway + 0.02 * math.cos(ang), by + 0.02 * math.sin(ang), z)
            along = (math.cos(ang) * 0.75, math.sin(ang) * 0.75, rnd.uniform(-0.6, 0.1))
            al = math.sqrt(sum(c * c for c in along))
            along = tuple(c / al for c in along)
            side = (-along[1], along[0], 0.0)
            sl = math.sqrt(side[0] ** 2 + side[1] ** 2) or 1
            side = (side[0] / sl, side[1] / sl, 0.25)
            _leaf(verts, faces, base, along, side, leaf * rnd.uniform(0.7, 1.3), leaf * 0.45)
    # a dense crown where the strands start
    for k in range(int(strands * 6)):
        t = rnd.random()
        base = (x0 + (x1 - x0) * t + rnd.uniform(-0.2, 0.2), y0 + (y1 - y0) * t + rnd.uniform(-0.2, 0.2),
                z_top - rnd.uniform(0, 0.18))
        ang = rnd.uniform(0, 2 * math.pi)
        along = (math.cos(ang), math.sin(ang), rnd.uniform(-0.5, 0.3))
        side = (-math.sin(ang), math.cos(ang), 0.2)
        _leaf(verts, faces, base, along, side, leaf * 1.3, leaf * 0.6)
    return L.mesh_obj(name, verts, faces, m)


def tree_blob(name, x, y, z0, h, r, color, seed=5, leaves=900):
    """an outdoor tree seen through bright glass: trunk plus a cloud of leaves"""
    rnd = random.Random(seed)
    verts, faces = [], []
    for _ in range(leaves):
        a, b = rnd.uniform(0, 2 * math.pi), rnd.uniform(-1, 1)
        rr = r * rnd.random() ** 0.4
        c = (x + rr * math.sqrt(1 - b * b) * math.cos(a), y + rr * math.sqrt(1 - b * b) * math.sin(a),
             z0 + h - r + rr * b * 0.8)
        along = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))
        al = math.sqrt(sum(q * q for q in along)) or 1
        along = tuple(q / al for q in along)
        side = (-along[1], along[0], 0.3)
        _leaf(verts, faces, c, along, side, 0.16, 0.07)
    ob = L.mesh_obj(name, verts, faces, L.mat(name + "-leaf", color, 0.6))
    L.cylinder(name + "-trunk", x, y, z0, z0 + h - r, 0.08, L.mat("bark", 0x3a3028, 0.9))
    return ob


def garland(name, a, b, material, n=160, seed=9):
    """a thin string of small leaves and warm fairy lights hanging just under the ceiling from a to b"""
    rnd = random.Random(seed)
    verts, faces = [], []
    for k in range(n):
        t = k / (n - 1)
        sag = 0.06 * math.sin(math.pi * t)
        p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
        p[2] -= sag
        along = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.6))
        al = math.sqrt(sum(q * q for q in along)) or 1
        along = tuple(q / al for q in along)
        side = (-along[1], along[0], 0.3)
        _leaf(verts, faces, p, along, side, 0.035, 0.015)
    return L.mesh_obj(name, verts, faces, material)
