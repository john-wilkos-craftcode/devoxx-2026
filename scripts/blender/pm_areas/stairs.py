"""The two side stairs from the hall up to floor 1, in venue coordinates (data/venue/venue.json's links stair-west and
stair-east: x -7.15..-4.85 and 10.25..12.55, 2.3 m wide, one straight flight from the hall at y 9.88 rising south to
floor 1 at y -1.32; 34 risers of 0.18 m over 11.2 m).

In the hall they stand in the teal frosted glass boxes hollywood.py builds (up to the structural ceiling, 5.45 m);
this module adds what's inside and above: the treads with light nosings, solid stringers (no see-through underside),
the shaft through the 0.75 m slab, and on floor 1 a balustrade round each opening (the corridor side and the north
end; the south end is where the flight arrives). Balustrade from the Street View detail views (2020, upstairs north
of the stairs): dark posts leaning out, glass infill, a dark handrail.
"""
import json
import math
from pathlib import Path

import pm_lib as L

FH = 6.2
TOP = 5.45                       # hall structural ceiling (hollywood.TOP); the slab runs from here to floor 1
RAIL_H = 1.1
POST_STEP = 1.25


def links(root):
    v = json.loads((Path(root) / "data" / "venue" / "venue.json").read_text())["venue"]
    return [ln for ln in v["links"] if ln["id"] in ("stair-west", "stair-east")]


def flight(name, ln, M):
    b = ln["bounds"]
    x0, x1, y0, y1 = b["x"], b["x"] + b["w"], b["y"], b["y"] + b["h"]
    n = round(ln["rise"] / ln["riser"])
    going = (y1 - y0) / n
    for i in range(n):                       # tread i: its top at the floor-1 end is FH, the hall end 0.18
        ya, yb = y0 + i * going, y0 + (i + 1) * going
        top = ln["base"] + (n - i) * ln["riser"]
        L.box(f"{name}-step{i:02d}", x0 + 0.05, ya, max(0.0, top - 0.35), x1 - 0.05, yb, top, M["tread"])
        L.box(f"{name}-nose{i:02d}", x0 + 0.08, ya, top, x1 - 0.08, ya + 0.04, top + 0.004, M["nosing"])
    # stringers: solid triangles closing each side of the flight down to the hall floor
    for xs in (x0, x1 - 0.05):
        v = [(xs, y0, FH), (xs, y1, 0.0), (xs, y0, 0.0), (xs + 0.05, y0, FH), (xs + 0.05, y1, 0.0), (xs + 0.05, y0, 0.0)]
        L.mesh_obj(f"{name}-stringer", v, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], M["stringer"])
    # the shaft through the slab, on the glass box's lines (hollywood cuts the hall ceilings there): dark slab edges
    # between the hall ceiling and floor 1, closing the gap between the box and the floor-1 opening
    gx0, gx1, gy0, gy1 = x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.32
    L.box(f"{name}-shaft-n", gx0, gy1 - 0.05, TOP, gx1, gy1, FH, M["slab"])
    L.box(f"{name}-shaft-s", gx0, gy0, TOP, gx1, gy0 + 0.05, FH, M["slab"])
    for xs in (gx0, gx1 - 0.05):
        L.box(f"{name}-shaft-side", xs, gy0, TOP, xs + 0.05, gy1, FH, M["slab"])
    L.box(f"{name}-lip-n", gx0, y1, FH - 0.1, gx1, gy1, FH, M["slab"])           # floor-1 edge round the opening
    L.box(f"{name}-lip-s", gx0, gy0, FH - 0.1, gx1, y0, FH, M["slab"])
    for xa, xb in ((gx0, x0), (x1, gx1)):
        L.box(f"{name}-lip-side", xa, y0, FH - 0.1, xb, y1, FH, M["slab"])
    return x0, x1, y0, y1


def balustrade(name, a, b, M, out):
    """posts every POST_STEP leaning towards `out` (unit, away from the opening), glass between, handrail on top"""
    ax, ay = a
    bx, by = b
    ln = math.hypot(bx - ax, by - ay)
    n = max(1, round(ln / POST_STEP))
    ux, uy = (bx - ax) / ln, (by - ay) / ln
    ox, oy = out
    for k in range(n + 1):
        px, py = ax + ux * ln * k / n, ay + uy * ln * k / n
        L.tube(f"{name}-post{k}", (px, py, FH), (px + ox * 0.12, py + oy * 0.12, FH + RAIL_H), 0.025, M["rail"], segs=8)
    L.tube(f"{name}-handrail", (ax + ox * 0.12, ay + oy * 0.12, FH + RAIL_H), (bx + ox * 0.12, by + oy * 0.12, FH + RAIL_H),
           0.03, M["rail"], segs=12)
    v = [(ax, ay, FH + 0.1), (bx, by, FH + 0.1), (bx + ox * 0.1, by + oy * 0.1, FH + RAIL_H - 0.08),
         (ax + ox * 0.1, ay + oy * 0.1, FH + RAIL_H - 0.08)]
    L.mesh_obj(f"{name}-glass", v, [(0, 1, 2, 3)], M["glass"])


GAP_Y = (11.58, 13.38)            # the openings in both long sides of each stairwell's glass box (plan walls)
BOX_SIDES = {"stair-west": ((-7.45, -7.15), (-4.85, -4.55)), "stair-east": ((9.95, 10.25), (12.55, 12.85))}
DOOR_H = 2.4


def double_doors(name, xa, xb, M, open_out=0):
    """white double doors in a glass box's side opening (xa..xb is the wall's thickness), a frosted panel above them to
    the ceiling; open_out = +1/-1 swings both leaves 90 deg out towards +x/-x (the side the walk comes from)"""
    y0, y1 = GAP_Y
    xm = (xa + xb) / 2
    w = (y1 - y0) / 2
    L.box(f"{name}-transom", xa, y0, DOOR_H + 0.08, xb, y1, TOP, M["frosted"])
    L.box(f"{name}-head", xa - 0.01, y0, DOOR_H, xb + 0.01, y1, DOOR_H + 0.08, M["door_frame"])
    for k, (h0, sgn) in enumerate(((y0, 1), (y1, -1))):           # hinge at each end, leaves meet in the middle
        if open_out:                                            # swung out flat against nothing: perpendicular to the wall
            xs, xe = sorted((xm, xm + open_out * w))
            L.box(f"{name}-leaf{k}", xs, h0 + sgn * 0.02 - 0.025, 0.01, xe, h0 + sgn * 0.02 + 0.025, DOOR_H - 0.01, M["door"])
        else:
            ys, ye = sorted((h0, h0 + sgn * (w - 0.005)))
            L.box(f"{name}-leaf{k}", xm - 0.025, ys, 0.01, xm + 0.025, ye, DOOR_H - 0.01, M["door"])
            yb = h0 + sgn * (w - 0.18)                          # a steel push bar on each face
            for f in (-1, 1):
                L.box(f"{name}-bar{k}{f}", xm + f * 0.03, min(yb, yb - sgn * 0.6), 1.0, xm + f * 0.05, max(yb, yb - sgn * 0.6), 1.05,
                      M["bar"])


def build(root, unified=True):
    M = {
        "tread": L.mat("stair-tread-dark", 0x2b2d33, 0.8, bump=0.2, bump_scale=200),
        "nosing": L.mat("stair-nosing", 0xb9bcc2, 0.4, metal=0.6),
        "stringer": L.mat("stair-stringer", 0x1c1e24, 0.7),
        "slab": L.mat("stair-slab-edge", 0x121318, 0.9),
        "rail": L.mat("stair-rail", 0x1a1a1c, 0.4, metal=0.6),
        "glass": L.mat("stair-rail-glass", 0xdfe8ee, 0.05, alpha=0.18),
        "door": L.mat("stair-door-white", 0xf2f2ee, 0.45),
        "door_frame": L.mat("stair-door-frame", 0xdcdcd8, 0.5),
        "bar": L.mat("stair-door-bar", 0xb9bcc2, 0.25, metal=1.0),
        "frosted": L.mat("frosted-glass", 0x8fb5b0, 0.35, transmission=0.6),
    }
    import pm_areas.venue as V
    walk_side = None if not V.ROOM else ("stair-west" if V.ROOM in (3, 4, 5, 6) else "stair-east")
    for sid, ((oa, ob), (ia, ib)) in BOX_SIDES.items():
        # the hall-facing side (towards the middle of the hall) is the way in; only the room walk's own opens
        inner = (ia, ib) if sid == "stair-west" else (oa, ob)
        outer = (oa, ob) if sid == "stair-west" else (ia, ib)
        out_dir = 1 if sid == "stair-west" else -1
        double_doors(f"{sid}-door-in", *inner, M, open_out=out_dir if sid == walk_side else 0)
        double_doors(f"{sid}-door-out", *outer, M)
    for ln in links(root):
        name = ln["id"]
        x0, x1, y0, y1 = flight(name, ln, M)
        west = x0 < 0
        inner, wall = (x1, x0) if west else (x0, x1)      # the opening's corridor side, and its side on the room wall
        balustrade(f"{name}-rail-side", (inner, y0), (inner, y1), M, out=(1.0 if west else -1.0, 0.0))
        balustrade(f"{name}-rail-end", (inner, y1), (wall, y1), M, out=(0.0, 1.0))
    print("STAIRS built", flush=True)
