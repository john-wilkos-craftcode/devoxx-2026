"""Build the Kinepolis venue in Blender from site/kino/venue.json, set up the shots, optionally render.

The same rules as the browser renderer (site/kino/kino.js) turn Ghost Light's venue model into
geometry; Blender adds real light: path tracing, soft shadows, bounce light, emissive LEDs.

Run with Blender's Python (Windows Blender, driven from WSL):
  blender.exe -b --python scripts/blender/build_scene.py -- --root C:/path/to/repo --room 8 \
      --save C:/renders/kino.blend [--render hall,seat,walk] [--out C:/renders] [--samples 96] [--preview]

Shots (per --room):
  hall      the exhibition hall, facing the LED wall that carries the programme (a still)
  walk-<n>  hall -> side stair -> corridor -> door -> aisle -> seat (an animation, also played back
            in reverse for the way out)
  seat-<n>  the seat that frames room n's cinema screen (a still)
Writes shots.json next to the renders: camera data per shot and, for the stills, where the LED wall
and the cinema screen land on screen, so the browser can pin the HTML onto them.

Venue coordinates are metres, +x east, +y north, +z up: Blender's own convention, so no conversion.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

FH, CLEAR, RAKE_DEPTH = 6.2, 5.4, 4.6
FPS = 30

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--room", type=int, default=8)
ap.add_argument("--save")
ap.add_argument("--render", default="")
ap.add_argument("--out")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--preview", action="store_true", help="EEVEE, low resolution: fast look-dev")
args = ap.parse_args(argv)
ROOT = Path(args.root)
venue = json.loads((ROOT / "site" / "kino" / "venue.json").read_text())["venue"]
OUT = Path(args.out) if args.out else ROOT / "build" / "renders"

# ---------------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"


def srgb(h):
    """0xRRGGBB (sRGB) -> linear RGBA."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin((h >> 16) & 255), lin((h >> 8) & 255), lin(h & 255), 1.0)


MATS = {}


def material(name, color, rough=0.85, metal=0.0, emission=None, strength=0.0, sheen=0.0, noise_bump=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = srgb(emission)
        bsdf.inputs["Emission Strength"].default_value = strength
    if noise_bump:
        # carpet / fabric: fine noise in the normals so large surfaces don't read as plastic
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 180.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = noise_bump
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    MATS[name] = m
    return m


def emissive(name, color, strength):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = srgb(color)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    MATS[name] = m
    return m


# Kinepolis Antwerp, from the reference photos: charcoal walls, navy carpet, pale vaults,
# blue-grey seats, red portals, orange numeral panels, blue LED light.
M = {
    "wall": material("wall", 0x34373f, 0.92),
    "audWall": material("audWall", 0x0f1014, 0.95),
    "column": material("column", 0x24262c, 0.9),
    "concrete": material("concrete", 0x34363d, 0.9),
    "rake": material("rake", 0x1a1c25, 0.98, noise_bump=0.15),
    "stair": material("stair", 0x2f3f86, 1.0, noise_bump=0.25),
    "nosing": material("nosing", 0x5d6694, 0.8),
    "carpet": material("carpet", 0x161c2e, 1.0, noise_bump=0.3),
    "hallFloor": material("hallFloor", 0x2a2c33, 1.0, noise_bump=0.3),
    "audFloor": material("audFloor", 0x111218, 1.0, noise_bump=0.2),
    "ceiling": material("ceiling", 0x121318, 1.0),
    "vault": material("vault", 0xcdc8bf, 0.9),
    "seat": material("seat", 0x2c3650, 0.95, sheen=0.6, noise_bump=0.2),
    "seatFrame": material("seatFrame", 0x15161b, 0.5, 0.4),
    "steel": material("steel", 0xb8bcc4, 0.3, 0.9),
    "portal": material("portal", 0xc61d3b, 0.55, emission=0xc61d3b, strength=0.15),
    "door": material("door", 0x1a1416, 0.5),
    "numeral": material("numeral", 0xf0641e, 0.7),
    "white": material("white", 0xf4f4f4, 0.6),
    "sign": material("sign", 0xf4f4f4, 0.5, emission=0xf4f4f4, strength=0.6),
    "signAccent": material("signAccent", 0xff6a1a, 0.5, emission=0xff6a1a, strength=2.0),
    "signPlate": material("signPlate", 0x101014, 0.6),
    "desk": material("desk", 0x0d0d10, 0.5),
    "booth": material("booth", 0x2f3138, 0.8),
    "chair": material("chair", 0x22242c, 0.8),
    "glazing": material("glazing", 0x8fb4d8, 0.05, 0.0),
    "paving": material("paving", 0x2c2d31, 0.95),
    "funnel": material("funnel", 0xf3f4f8, 0.7),
    "led": emissive("led", 0x3f74ff, 12.0),
    "ledWhite": emissive("ledWhite", 0xdfe7ff, 8.0),
    "screen": emissive("screen", 0x2a3350, 4.0),       # the HTML is pinned over this in the browser
    "ledWall": emissive("ledWall", 0x16224f, 4.0),
    "glassDoors": emissive("glassDoors", 0x2c58ff, 3.0),
    "redFunnel": material("redFunnel", 0x8f1026, 0.7, emission=0xb0132f, strength=0.8),
    "schedule": emissive("schedule", 0x1c2a6b, 1.5),
}
M["glazing"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.9


# ---------------------------------------------------------------------------------- mesh building
class Batch:
    """Boxes and meshes collected per material, joined into one object each at the end."""

    def __init__(self):
        self.bms = {}

    def bm(self, key):
        if key not in self.bms:
            self.bms[key] = bmesh.new()
        return self.bms[key]

    def box(self, key, b, bottom, top):
        if not (top - bottom > 0.005 and b["w"] > 0 and b["h"] > 0):
            return
        m = Matrix.Translation((b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, (bottom + top) / 2)) @ \
            Matrix.Diagonal((b["w"], b["h"], top - bottom, 1))
        bmesh.ops.create_cube(self.bm(key), size=1.0, matrix=m)

    def mesh(self, key, verts, faces, matrix=Matrix.Identity(4)):
        bm = self.bm(key)
        vs = [bm.verts.new(matrix @ Vector(v)) for v in verts]
        for f in faces:
            bm.faces.new([vs[i] for i in f])

    def finish(self):
        for key, bm in self.bms.items():
            me = bpy.data.meshes.new(key)
            bm.to_mesh(me)
            bm.free()
            ob = bpy.data.objects.new(key, me)
            ob.data.materials.append(M.get(key, M["concrete"]))
            scene.collection.objects.link(ob)


B = Batch()
rooms = venue["rooms"]
auditoriums = [r for r in rooms if r["kind"] == "auditorium" and r["floor"] == 1]
corridor = next(r for r in rooms if r["id"] == "corridor")["bounds"]


def inside(b, x, y):
    return b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]


def ground_at(floor, x, y):
    best, area = None, float("inf")
    for r in rooms:
        if r["floor"] == floor and inside(r["bounds"], x, y) and r["bounds"]["w"] * r["bounds"]["h"] < area:
            best, area = r, r["bounds"]["w"] * r["bounds"]["h"]
    return (best or {}).get("elevation", 0) or 0


def plate_under(p):
    b = p["bounds"]
    return 0 if p.get("linkId") else ground_at(p["floor"], b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)


# walls and columns, full height; floor-0 walls stop under the floor-1 seating rakes
for o in venue["obstacles"]:
    if o.get("hidden"):
        continue
    datum = o["floor"] * FH
    tall = o["height"] >= 3 and not o.get("linkId")
    b = o["bounds"]
    column = tall and b["w"] < 1.2 and b["h"] < 1.2
    under = datum + plate_under(o)
    bottom = datum - RAKE_DEPTH if (tall and o["floor"] == 1) else under + o.get("base", 0)
    top = datum + CLEAR if tall else under + o["height"]
    if o["floor"] == 0:
        for a in auditoriums:
            ab = a["bounds"]
            if b["x"] < ab["x"] + ab["w"] and b["x"] + b["w"] > ab["x"] and b["y"] < ab["y"] + ab["h"] and b["y"] + b["h"] > ab["y"]:
                top = min(top, FH - a.get("rake", 0) - 0.35)
    key = "column" if column else "wall" if tall else (o.get("material") if o.get("material") in M else "concrete")
    B.box(key, b, bottom, top)

STAIRS = {"grand-stair", "stair-west", "stair-east", "hall-steps", "bof-1-steps", "bof-2-steps"}
for d in venue["decor"]:
    mat = d.get("material")
    if mat in ("floorBelow", "seat", "seatBack"):
        continue
    if d.get("wordmark") and d["wordmark"] != "devoxx":
        continue   # Ghost Light stores DEVOXX and JAVAPOLIS in the same spot; draw only DEVOXX
    under = d["floor"] * FH + plate_under(d)
    key = mat or ("stair" if d.get("linkId") in STAIRS else "rake" if d.get("linkId") else "concrete")
    if mat == "structure":
        key = "rake"
    if key == "screen":
        continue   # screens are built below as clean emissive planes
    B.box(key if key in M else "concrete", d["bounds"], under + d.get("base", 0), under + d["height"])

# stair treads and seating terraces from the links (Ghost Light keeps them as rise/riser/direction)
for L in venue["links"]:
    if not L.get("riser"):
        continue
    datum, b = L["from"] * FH, L["bounds"]
    n = round(L["rise"] / L["riser"])
    along_x = L["axis"] == "x"
    going = (b["w"] if along_x else b["h"]) / n
    rake = L["id"].startswith("rake-")
    for i in range(n):
        top = datum + L["base"] + ((i + 1) if L["ascending"] else (n - i)) * L["riser"]
        sl = {"x": b["x"] + i * going, "y": b["y"], "w": going, "h": b["h"]} if along_x else \
             {"x": b["x"], "y": b["y"] + i * going, "w": b["w"], "h": going}
        B.box("rake" if rake else "stair", sl, datum + L["base"] - 0.3, top)
        if not rake:
            edge = 0 if L["ascending"] else going - 0.05
            st = {"x": sl["x"] + edge, "y": b["y"], "w": 0.05, "h": b["h"]} if along_x else \
                 {"x": b["x"], "y": sl["y"] + edge, "w": b["w"], "h": 0.05}
            B.box("nosing", st, top - 0.004, top + 0.006)


def subtract_rects(b, holes):
    xs = sorted({b["x"], b["x"] + b["w"], *[v for h in holes for v in (h["x"], h["x"] + h["w"]) if b["x"] < v < b["x"] + b["w"]]})
    ys = sorted({b["y"], b["y"] + b["h"], *[v for h in holes for v in (h["y"], h["y"] + h["h"]) if b["y"] < v < b["y"] + b["h"]]})
    out = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not any(h["x"] < mx < h["x"] + h["w"] and h["y"] < my < h["y"] + h["h"] for h in holes):
                out.append({"x": xs[i], "y": ys[j], "w": xs[i + 1] - xs[i], "h": ys[j + 1] - ys[j]})
    return out


FLOOR_KEY = {"corridor": "carpet", "foyer": "carpet", "landing": "carpet", "hall": "hallFloor",
             "auditorium": "audFloor", "stage": "audFloor", "outside": "paving"}
for r in rooms:
    z = r["floor"] * FH + (r.get("elevation") or 0)
    key = "hallFloor" if (r["kind"] == "foyer" and r["floor"] == 0) else FLOOR_KEY.get(r["kind"], "concrete")
    for cell in subtract_rects(r["bounds"], r.get("voids", [])):
        B.box(key, cell, z - 0.25, z)            # a slab, so it is also the ceiling of the floor below
for e in venue["extents"]:
    B.box("ceiling", e, FH + CLEAR, FH + CLEAR + 0.2)

# ---------------------------------------------------------------------------------- corridor dressing
cx, cy = corridor["x"] + corridor["w"] / 2, corridor["y"] + corridor["h"] / 2


def cove(side, R=1.3, segs=16):
    """A quarter-cylinder vault springing from the corridor wall head up to the ceiling."""
    wall_x = corridor["x"] if side < 0 else corridor["x"] + corridor["w"]
    cxx, cz = wall_x - side * R, FH + CLEAR - R
    y0, y1 = corridor["y"], corridor["y"] + corridor["h"]
    verts, faces = [], []
    for k in range(segs + 1):
        a = k / segs * math.pi / 2
        x, z = cxx + side * R * math.cos(a), cz + R * math.sin(a)
        verts += [(x, y0, z), (x, y1, z)]
    for k in range(segs):
        faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    B.mesh("vault", verts, faces)
    B.box("led", {"x": wall_x - side * (R + 0.05) - 0.03, "y": y0, "w": 0.06, "h": y1 - y0}, FH + CLEAR - 0.07, FH + CLEAR - 0.01)


cove(-1)
cove(1)


def lathe(key, profile, center, segs=48, phi0=0.0, phi=2 * math.pi, scale=(1, 1, 1)):
    verts, faces = [], []
    for k in range(segs + 1):
        a = phi0 + phi * k / segs
        for (r, z) in profile:
            verts.append((center[0] + r * math.cos(a) * scale[0], center[1] + r * math.sin(a) * scale[1], center[2] + z * scale[2]))
    n = len(profile)
    for k in range(segs):
        for i in range(n - 1):
            a, b = k * n + i, (k + 1) * n + i
            faces.append((a, b, b + 1, a + 1))
    B.mesh(key, verts, faces)


grand = next(l for l in venue["links"] if l["id"] == "grand-stair")["bounds"]
funnel_profile = [(0.12 + 2.8 * (t / 24) ** 2.6, (t / 24) * 3.0) for t in range(25)]
for fx in (grand["x"] + grand["w"] * 0.17, grand["x"] + grand["w"] * 0.5, grand["x"] + grand["w"] * 0.83):
    lathe("funnel", funnel_profile, (fx, grand["y"] + grand["h"] + 1.8, FH + CLEAR - 3.0))

# ---------------------------------------------------------------------------------- rooms: doors, screens
FONT = bpy.data.fonts.load(str(ROOT / "scripts" / "blender" / "fonts" / "BigShouldersDisplay.ttf"))


def text_object(body, size, loc, rot, mat, extrude=0.01, offset=0.02):
    cu = bpy.data.curves.new(f"txt-{body}", "FONT")
    cu.body, cu.font, cu.size, cu.extrude, cu.offset = body, FONT, size, extrude, offset
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    ob = bpy.data.objects.new(f"txt-{body}", cu)
    ob.location, ob.rotation_euler = loc, rot
    ob.data.materials.append(mat)
    scene.collection.objects.link(ob)
    return ob


doors = {}
screens = {}
for r in auditoriums:
    n = int("".join(c for c in r["label"] if c.isdigit()))
    b = r["bounds"]
    west = b["x"] < corridor["x"]
    wall_x = b["x"] + b["w"] if west else b["x"]
    face = 1 if west else -1                     # +1: the door faces east, into the corridor
    margin = (r.get("doorMargin") or 1.2) + 1.25
    yc = b["y"] + margin if r.get("doorSide") == "low" else b["y"] + b["h"] - margin
    along = 1 if r.get("doorSide") == "low" else -1
    # enclosure, floor to ceiling, door gap left open
    lo, hi, t = FH - RAKE_DEPTH, FH + CLEAR, 0.3
    corr_x = b["x"] + b["w"] - t if west else b["x"]
    far_x = b["x"] if west else b["x"] + b["w"] - t
    for wb in ({"x": b["x"], "y": b["y"] - t / 2, "w": b["w"], "h": t}, {"x": b["x"], "y": b["y"] + b["h"] - t / 2, "w": b["w"], "h": t},
               {"x": far_x, "y": b["y"], "w": t, "h": b["h"]}, {"x": corr_x, "y": b["y"], "w": t, "h": yc - 1.15 - b["y"]},
               {"x": corr_x, "y": yc + 1.15, "w": t, "h": b["y"] + b["h"] - yc - 1.15}):
        B.box("audWall", wb, lo, hi)
    B.box("audWall", {"x": corr_x, "y": yc - 1.15, "w": t, "h": 2.3}, FH + 2.7, hi)
    # portal frame (head + two jambs) standing proud of the wall
    px = wall_x + face * 0.16
    for (dy, w, z0, z1) in ((0, 3.1, 2.7, 3.5), (-1.35, 0.4, 0, 2.7), (1.35, 0.4, 0, 2.7)):
        B.box("portal", {"x": min(px, px + face * 0.55), "y": yc + dy - w / 2, "w": 0.55, "h": w}, FH + z0, FH + z1)
    B.box("led", {"x": px + face * 0.53, "y": yc - 1.55, "w": 0.05, "h": 3.1}, FH + 3.53, FH + 3.58)
    # door leaves on hinges, animated open for the room we walk to
    leaves = []
    for side in (-1, 1):
        hinge = bpy.data.objects.new(f"hinge-{n}-{side}", None)
        hinge.location = (px + face * 0.56, yc + side * 1.15, FH)
        scene.collection.objects.link(hinge)
        me = bpy.data.meshes.new(f"leaf-{n}-{side}")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -side * 0.575, 1.35)) @ Matrix.Diagonal((0.08, 1.15, 2.7, 1)))
        bm.to_mesh(me)
        bm.free()
        leaf = bpy.data.objects.new(f"leaf-{n}-{side}", me)
        leaf.data.materials.append(M["door"])
        leaf.parent = hinge
        scene.collection.objects.link(leaf)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.34, minor_radius=0.025, location=(face * 0.06, -side * 0.73, 1.25),
                                         rotation=(0, math.pi / 2, 0))
        ring = bpy.context.active_object
        ring.data.materials.append(M["steel"])
        ring.parent = hinge
        leaves.append((hinge, side))
    # numeral panel with the big white room number
    side_y = -along
    panel_y = yc + side_y * 2.75
    B.box("numeral", {"x": wall_x + (0.0 if west else -0.06), "y": panel_y - 0.95, "w": 0.06, "h": 1.9}, FH + 0.33, FH + 3.38)
    text_object(str(n), 2.6, (wall_x + face * 0.07, panel_y, FH + 1.85), (math.pi / 2, 0, math.pi / 2 if west else -math.pi / 2), M["white"], 0.02, 0.03)
    # schedule screen on a stand (its programme is drawn in HTML in the browser)
    sy = yc - side_y * 2.4
    sx = wall_x + face * 1.2
    B.box("steel", {"x": sx - 0.02, "y": sy - 0.02, "w": 0.04, "h": 0.04}, FH, FH + 1.2)
    B.box("schedule", {"x": sx - 0.02, "y": sy - 0.33, "w": 0.04, "h": 0.66}, FH + 1.2, FH + 2.3)
    doors[n] = {"room": r, "wall_x": wall_x, "yc": yc, "face": face, "leaves": leaves, "west": west}

    # the cinema screen: a clean emissive plane on the screen wall
    sd = next((d for d in venue["decor"] if d.get("material") == "screen" and d.get("room") == r["id"]), None)
    if sd:
        sb = sd["bounds"]
        z0 = FH + plate_under(sd) + sd.get("base", 0)
        z1 = FH + plate_under(sd) + sd["height"]
        w = sb["h"]
        h = min(z1 - z0, w * 776 / 2048)
        x = sb["x"] + sb["w"] + 0.02 if west else sb["x"] - 0.02
        zc = (z0 + z1) / 2
        corners = [(x, sb["y"], zc - h / 2), (x, sb["y"] + w, zc - h / 2), (x, sb["y"] + w, zc + h / 2), (x, sb["y"], zc + h / 2)]
        B.mesh("screen", corners, [(0, 1, 2, 3)])
        screens[n] = {"corners": corners, "x": x, "y": sb["y"] + w / 2, "z": zc, "w": w, "h": h, "west": west}

# ---------------------------------------------------------------------------------- seats
seat_me = bpy.data.meshes.new("seat-model")
bm = bmesh.new()
for (sx, sy, sz, x, y, z, rz) in ((0.46, 0.5, 0.09, 0, 0, -0.045, 0), (0.09, 0.5, 0.72, -0.25, 0, 0.3, 0.12)):
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(-rz, 4, "Y") @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.025, segments=2, affect="EDGES")
bm.to_mesh(seat_me)
bm.free()
frame_me = bpy.data.meshes.new("seat-frame")
bm = bmesh.new()
for (sx, sy, sz, x, y, z) in ((0.46, 0.06, 0.05, 0, 0.27, 0.2), (0.06, 0.06, 0.62, -0.05, 0.27, -0.12), (0.2, 0.4, 0.06, -0.08, 0, -0.3)):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x, y, z)) @ Matrix.Diagonal((sx, sy, sz, 1)))
bm.to_mesh(frame_me)
bm.free()
seats_bm, frames_bm = bmesh.new(), bmesh.new()
pans = [d for d in venue["decor"] if d.get("material") == "seat"]
for d in pans:
    b = d["bounds"]
    room = next((r for r in auditoriums if inside(r["bounds"], b["x"], b["y"])), None)
    faces_west = room is None or room["bounds"]["x"] < corridor["x"]
    mat = Matrix.Translation((b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, d["floor"] * FH + plate_under(d) + d["height"])) @ \
        Matrix.Rotation(math.pi if faces_west else 0, 4, "Z")
    for src, dst in ((seat_me, seats_bm), (frame_me, frames_bm)):
        tmp = src.copy()
        tmp.transform(mat)
        dst.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
for name, bm_, mat in (("seats", seats_bm, M["seat"]), ("seat-frames", frames_bm, M["seatFrame"])):
    me = bpy.data.meshes.new(name)
    bm_.to_mesh(me)
    bm_.free()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    scene.collection.objects.link(ob)

# ---------------------------------------------------------------------------------- the exhibition hall
WALL = {"x": 5.9, "y": 18.0, "z": 4.05, "w": 7.2, "h": 4.05}
wall_corners = [(WALL["x"] - WALL["w"] / 2, WALL["y"] - 0.06, WALL["z"] - WALL["h"] / 2), (WALL["x"] + WALL["w"] / 2, WALL["y"] - 0.06, WALL["z"] - WALL["h"] / 2),
                (WALL["x"] + WALL["w"] / 2, WALL["y"] - 0.06, WALL["z"] + WALL["h"] / 2), (WALL["x"] - WALL["w"] / 2, WALL["y"] - 0.06, WALL["z"] + WALL["h"] / 2)]
B.mesh("ledWall", wall_corners, [(0, 1, 2, 3)])
B.box("desk", {"x": WALL["x"] - WALL["w"] / 2 - 0.15, "y": WALL["y"] - 0.02, "w": WALL["w"] + 0.3, "h": 0.2}, WALL["z"] - WALL["h"] / 2 - 0.15, WALL["z"] + WALL["h"] / 2 + 0.15)
for sxn in (-1, 1):
    B.box("column", {"x": WALL["x"] + sxn * (WALL["w"] / 2 + 1.0) - 0.55, "y": WALL["y"] - 1.15, "w": 1.1, "h": 1.1}, 0, FH)
lathe("redFunnel", [(0.25 + 3.3 * (t / 16) ** 2.2, (t / 16) * 1.9) for t in range(17)],
      (WALL["x"], WALL["y"] - 0.2, WALL["z"] - WALL["h"] / 2 - 1.9), segs=40, phi0=math.pi, phi=math.pi, scale=(1, 0.22, 1))
B.mesh("glassDoors", [(WALL["x"] - 2.3, WALL["y"] - 0.1, 0.05), (WALL["x"] + 2.3, WALL["y"] - 0.1, 0.05), (WALL["x"] + 2.3, WALL["y"] - 0.1, 1.55), (WALL["x"] - 2.3, WALL["y"] - 0.1, 1.55)], [(0, 1, 2, 3)])
for sxn in (-1, 1):
    bx = WALL["x"] + sxn * 7.2
    B.box("ledWhite", {"x": bx + sxn * 0.4 - 0.04, "y": WALL["y"] - 18, "w": 0.08, "h": 18}, 5.72, 5.78)
    y = WALL["y"] - 2
    while y > WALL["y"] - 17:
        B.box("seatFrame", {"x": bx - 0.12, "y": y - 0.12, "w": 0.24, "h": 0.24}, 5.4, 5.7)
        spot = bpy.data.lights.new(f"track-{sxn}-{y:.1f}", "SPOT")
        spot.energy, spot.spot_size, spot.spot_blend, spot.color = 900, math.radians(38), 0.6, (1.0, 0.93, 0.82)
        so = bpy.data.objects.new(spot.name, spot)
        so.location = (bx, y, 5.38)
        so.rotation_euler = (0, -sxn * 0.5, 0)
        scene.collection.objects.link(so)
        y -= 3.2
    for row in range(4):
        for i in range(6):
            B.box("chair", {"x": WALL["x"] + sxn * (8.6 - row * 0.65) - 0.25, "y": WALL["y"] - 9 + i * 0.62 - 0.25, "w": 0.5, "h": 0.5}, 0, 0.9)
    gx = WALL["x"] + sxn * 10.5
    for (dy, w, z0, z1) in ((0, 3.2, 2.75, 3.25), (-1.4, 0.4, 0, 2.75), (1.4, 0.4, 0, 2.75)):
        B.box("portal", {"x": gx - 0.3, "y": WALL["y"] - 5 + dy - w / 2, "w": 0.6, "h": w}, z0, z1)

B.finish()

# ---------------------------------------------------------------------------------- lights
world = bpy.data.worlds.new("night")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = srgb(0x07060c)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
# a little haze in the air: spots and LEDs throw visible beams, as in the venue photos
vol = world.node_tree.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = 0.012
vol.inputs["Anisotropy"].default_value = 0.55
world.node_tree.links.new(vol.outputs["Volume"], world.node_tree.nodes["World Output"].inputs["Volume"])
scene.world = world


def area(name, loc, size, power, color=(1, 1, 1), rot=(0, 0, 0)):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.size, li.color = power, size, color
    ob = bpy.data.objects.new(name, li)
    ob.location, ob.rotation_euler = loc, rot
    scene.collection.objects.link(ob)
    return ob


def point(name, loc, power, color=(1, 1, 1), radius=0.2):
    li = bpy.data.lights.new(name, "POINT")
    li.energy, li.color, li.shadow_soft_size = power, color, radius
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    scene.collection.objects.link(ob)


y = -44
while y <= 62:
    area(f"corridor-{y}", (cx, y, FH + CLEAR - 0.05), 1.2, 900, (0.9, 0.92, 1.0))
    y += 12
for fx in (grand["x"] + grand["w"] * 0.17, grand["x"] + grand["w"] * 0.5, grand["x"] + grand["w"] * 0.83):
    point(f"funnel-{fx:.1f}", (fx, grand["y"] + grand["h"] + 1.8, FH + 0.6), 1500, (0.35, 0.5, 1.0), 0.4)
for sid in ("stair-west", "stair-east"):
    sb = next(l for l in venue["links"] if l["id"] == sid)["bounds"]
    point(f"{sid}-low", (sb["x"] + sb["w"] / 2, sb["y"] + sb["h"] * 0.7, 2.6), 500, (0.8, 0.85, 1.0))
    point(f"{sid}-high", (sb["x"] + sb["w"] / 2, sb["y"] + sb["h"] * 0.25, FH - 0.6), 500, (0.8, 0.85, 1.0))
area("ledwall-spill", (WALL["x"], WALL["y"] - 1.0, WALL["z"]), 4.0, 2500, (0.45, 0.55, 1.0), rot=(math.pi / 2, 0, 0))
point("portal-glow-w", (WALL["x"] - 9.8, WALL["y"] - 5, 2.2), 500, (1.0, 0.25, 0.35))
point("portal-glow-e", (WALL["x"] + 9.8, WALL["y"] - 5, 2.2), 500, (1.0, 0.25, 0.35))
# the auditorium we walk to: dim house lights, the screen's own spill does the rest
_room = doors[args.room]["room"]["bounds"] if args.room in doors else None
if _room:
    _west = _room["x"] < corridor["x"]
    _mx = _room["x"] + _room["w"] * 0.55
    area("house-1", (_mx, _room["y"] + _room["h"] * 0.3, FH + CLEAR - 0.1), 2.0, 700, (0.85, 0.88, 1.0))
    area("house-2", (_mx, _room["y"] + _room["h"] * 0.7, FH + CLEAR - 0.1), 2.0, 700, (0.85, 0.88, 1.0))

# ---------------------------------------------------------------------------------- shots
cam_data = bpy.data.cameras.new("cam")
cam_data.sensor_fit = "VERTICAL"     # fov values below are vertical, as in the browser version
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = (960, 540) if args.preview else (1920, 1080)
scene.render.fps = FPS
ASPECT = 16 / 9


def fit_distance(w, h, fov_deg, fill):
    t = math.tan(math.radians(fov_deg) / 2)
    return max(h / 2 / t, w / 2 / (t * ASPECT)) / fill


def aim(loc, target):
    d = Vector(target) - Vector(loc)
    return d.to_track_quat("-Z", "Y").to_euler()


def set_cam(loc, target, fov):
    cam.location = loc
    cam.rotation_euler = aim(loc, target)
    cam_data.sensor_fit = "VERTICAL"
    cam_data.angle_y = math.radians(fov)


def hall_pose():
    d = fit_distance(WALL["w"], WALL["h"], 50, 0.5)
    return (WALL["x"], WALL["y"] - d, WALL["z"]), (WALL["x"], WALL["y"], WALL["z"]), 50


def seat_for(n, fov=52):
    door, scr = doors[n], screens[n]
    b = door["room"]["bounds"]
    seats = [d for d in pans if d["floor"] == 1 and inside(b, d["bounds"]["x"], d["bounds"]["y"])]
    want = fit_distance(scr["w"], scr["h"], fov, 0.92)
    best = min(seats, key=lambda s: abs(abs(s["bounds"]["x"] + s["bounds"]["w"] / 2 - scr["x"]) - want) +
               abs(s["bounds"]["y"] + s["bounds"]["h"] / 2 - scr["y"]) * 0.6)
    seat = (best["bounds"]["x"] + best["bounds"]["w"] / 2, best["bounds"]["y"] + best["bounds"]["h"] / 2, FH + best["height"] + 0.8)
    return seat, (scr["x"], seat[1], scr["z"]), fov, seats


def catmull_rom(pts, samples):
    """Centripetal Catmull-Rom through pts, resampled to `samples` points evenly spaced along the curve."""
    P = [Vector(p) for p in pts]
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + (p1 - p0).length ** 0.5 + 1e-6
        t2 = t1 + (p2 - p1).length ** 0.5 + 1e-6
        t3 = t2 + (p3 - p2).length ** 0.5 + 1e-6
        for k in range(40):
            t = t1 + (t2 - t1) * k / 40
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            dense.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    dense.append(P[-2])
    cum = [0.0]
    for i in range(1, len(dense)):
        cum.append(cum[-1] + (dense[i] - dense[i - 1]).length)
    out, j = [], 0
    for s in range(samples):
        target = cum[-1] * s / (samples - 1)
        while j < len(cum) - 2 and cum[j + 1] < target:
            j += 1
        f = (target - cum[j]) / max(1e-9, cum[j + 1] - cum[j])
        out.append(dense[j].lerp(dense[j + 1], f))
    return out, cum[-1]


def walk(n):
    """Keyframe the camera from the hall to its seat in room n, and swing that room's doors open."""
    door, scr = doors[n], screens[n]
    seat, look_end, fov_end, seats = seat_for(n)
    west, face = door["west"], door["face"]
    stair = next(l for l in venue["links"] if l["id"] == ("stair-west" if west else "stair-east"))["bounds"]
    sx = stair["x"] + stair["w"] / 2
    rake = next(l for l in venue["links"] if l["id"] == f"rake-{n}")
    steps = round(rake["rise"] / rake["riser"])
    going = rake["bounds"]["w"] / steps

    def tread(x):
        i = min(steps - 1, max(0, int((x - rake["bounds"]["x"]) // going)))
        return FH + rake["base"] + ((i + 1) if rake["ascending"] else (steps - i)) * rake["riser"]

    b = door["room"]["bounds"]
    ys = [s["bounds"]["y"] for s in seats]
    y0, y1 = min(ys), max(s["bounds"]["y"] + s["bounds"]["h"] for s in seats)
    aisle_y = (b["y"] + y0) / 2 if door["room"].get("doorSide") == "low" else (y1 + b["y"] + b["h"]) / 2
    high_x = rake["bounds"]["x"] + rake["bounds"]["w"] if west else rake["bounds"]["x"]
    lp, _, _ = hall_pose()
    wx, yc = door["wall_x"], door["yc"]
    pts = [lp, ((lp[0] + sx) / 2, stair["y"] + stair["h"] + 2.2, 1.7), (sx, stair["y"] + stair["h"] - 0.4, 1.75),
           (sx, stair["y"] + 0.6, FH + 1.65), ((sx + cx) / 2, stair["y"] - 2.5, FH + 1.7),
           (wx + face * 3.2, yc, FH + 1.7), (wx - face * 1.2, yc, FH + 1.65), ((high_x + wx) / 2, aisle_y, FH + 1.65),
           ((high_x + seat[0]) / 2, aisle_y, tread((high_x + seat[0]) / 2) + 1.65), (seat[0], aisle_y, tread(seat[0]) + 1.6),
           (seat[0], (aisle_y + seat[1]) / 2, seat[2] + 0.15), seat]
    length_guess = sum((Vector(pts[i + 1]) - Vector(pts[i])).length for i in range(len(pts) - 1))
    seconds = min(5.0, 2.8 + length_guess / 45)
    frames = int(seconds * FPS)
    path, length = catmull_rom(pts, frames * 4)

    def ease(x):
        return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

    look = Vector(path[min(len(path) - 1, 40)])
    for f in range(frames + 1):
        t = f / frames
        u = ease(t)
        idx = min(len(path) - 1, int(u * (len(path) - 1)))
        pos = path[idx]
        ahead = path[min(len(path) - 1, idx + len(path) // 8)].copy()
        ahead.z = pos.z + (ahead.z - pos.z) * 0.25                      # keep the horizon level
        blend = 0 if t < 0.55 else (1 if t > 1 else (lambda s: s * s * (3 - 2 * s))((t - 0.55) / 0.45))
        target = ahead.lerp(Vector(look_end), blend)
        look = look.lerp(target, 1 - math.exp(-1 / FPS / 0.22)) if f < frames else target
        cam.location = pos
        cam.rotation_euler = aim(pos, look)
        cam_data.angle_y = math.radians(50 + (fov_end - 50) * u)
        cam.keyframe_insert("location", frame=f + 1)
        cam.keyframe_insert("rotation_euler", frame=f + 1)
        cam_data.keyframe_insert("lens", frame=f + 1)
    # doors open as you reach them (around 55% of the walk) and stay open
    for hinge, side in door["leaves"]:
        hinge.rotation_euler = (0, 0, 0)
        hinge.keyframe_insert("rotation_euler", frame=int(frames * 0.42))
        hinge.rotation_euler = (0, 0, -side * face * 1.45)
        hinge.keyframe_insert("rotation_euler", frame=int(frames * 0.56))
    return frames


def screen_quad(corners, camera):
    """Where a world-space quad lands on the rendered image: [x, y] per corner, 0..1 from the top left."""
    out = []
    for c in corners:
        v = world_to_camera_view(scene, camera, Vector(c))
        out.append([round(v.x, 5), round(1 - v.y, 5)])
    return out


OUT.mkdir(parents=True, exist_ok=True)
shots = {}
n = args.room
# the hall gets its own camera, so rendering it never disturbs the walk's keyframes
hall_data = bpy.data.cameras.new("cam-hall")
hall_cam = bpy.data.objects.new("cam-hall", hall_data)
scene.collection.objects.link(hall_cam)
pos, look, fov = hall_pose()
hall_cam.location, hall_cam.rotation_euler = pos, aim(pos, look)
hall_data.sensor_fit, hall_data.angle_y = "VERTICAL", math.radians(fov)
bpy.context.view_layer.update()       # matrix_world is stale until the depsgraph runs
shots["hall"] = {"kind": "still", "overlay": {"ledWall": screen_quad(wall_corners, hall_cam)}}
frames = walk(n)
shots[f"walk-{n}"] = {"kind": "clip", "frames": frames, "fps": FPS}
seat, look_end, fov_end, _ = seat_for(n)
scene.frame_set(frames + 1)
shots[f"seat-{n}"] = {"kind": "still", "frame": frames + 1, "overlay": {"screen": screen_quad(screens[n]["corners"], cam)}}
(OUT / "shots.json").write_text(json.dumps(shots, indent=1))

# ---------------------------------------------------------------------------------- render settings
if args.preview:
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
else:
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.type == backend for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == backend
                break
        except TypeError:
            continue
    scene.cycles.device = "GPU"
    scene.cycles.samples = args.samples
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.4
scene.view_settings.view_transform = "AgX" if "AgX" in [v.name for v in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=args.save)

for what in [w for w in args.render.split(",") if w]:
    if what == "hall":
        scene.camera = hall_cam
        scene.render.filepath = str(OUT / "hall.png")
        bpy.ops.render.render(write_still=True)
        scene.camera = cam
    elif what == "seat":
        scene.frame_set(frames + 1)
        scene.render.filepath = str(OUT / f"seat-{n}.png")
        bpy.ops.render.render(write_still=True)
    elif what == "walk":
        scene.frame_start, scene.frame_end = 1, frames + 1
        scene.render.filepath = str(OUT / f"walk-{n}" / "f_")
        bpy.ops.render.render(animation=True)
print("done", json.dumps({k: v.get("frames") for k, v in shots.items()}))
