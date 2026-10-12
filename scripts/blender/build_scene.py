"""Build the Kinepolis venue in Blender from site/kino/venue.json, set up the shots, optionally render.

The same rules as the browser renderer (site/kino/kino.js) turn Ghost Light's venue model into
geometry; Blender adds real light: path tracing, soft shadows, bounce light, emissive LEDs.

Run with Blender's Python (Windows Blender, driven from WSL):
  blender.exe -b --python scripts/blender/build_scene.py -- --root C:/path/to/repo --room 8 \
      --save C:/renders/kino.blend [--render hall,seat,walk] [--out C:/renders] [--samples 96] [--preview]
  (--render walk@20+60 renders single frames of the walk, for look-dev)

Shots (per --room):
  hall      the Hollywood room (the exhibition floor downstairs), facing the screen on the curtained
            far wall that carries the programme (a still)
  walk-<n>  hall -> side stair -> corridor -> door -> aisle -> seat (an animation, also played back
            in reverse for the way out)
  seat-<n>  the seat that frames room n's cinema screen (a still)
Writes shots.json next to the renders: camera data per shot and, for the stills, where the programme
screen and the cinema screen land on screen, so the browser can pin the HTML onto them.

Venue coordinates are metres, +x east, +y north, +z up: Blender's own convention, so no conversion.
"""
import argparse
import json
import math
import random
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


def material(name, color, rough=0.85, metal=0.0, emission=None, strength=0.0, sheen=0.0, noise_bump=0.0, speckle=0.0):
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
    if speckle:
        # mottled carpet: blotchy noise between a darker and a lighter shade of the base colour
        coord = nt.nodes.new("ShaderNodeTexCoord")
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 7.0          # object space, so the mottling is about 15 cm whatever the mesh size
        tex.inputs["Detail"].default_value = 4.0
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        lo, hi = ramp.color_ramp.elements
        lo.position, hi.position = 0.35, 0.65
        base = srgb(color)
        lo.color = tuple(c * (1 - speckle) for c in base[:3]) + (1,)
        hi.color = tuple(min(1.0, c * (1 + speckle)) for c in base[:3]) + (1,)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
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


# Kinepolis Antwerp, from the reference photos (data/references/): charcoal walls, navy carpet, pale
# vaults, blue-grey seats, red portals, orange numeral panels, blue LED light. Downstairs, the Hollywood
# room is the opposite: white columns and ceilings, grey carpet, beige curtains, black acoustic ceiling.
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
    "hollywoodFloor": material("hollywoodFloor", 0x7f7a74, 1.0, noise_bump=0.3, speckle=0.14),
    "hallColumn": material("hallColumn", 0xecebe7, 0.75),
    "hallWall": material("hallWall", 0xe4e2dd, 0.85),
    "raft": material("raft", 0xf1f1ee, 0.9),
    "acoustic": material("acoustic", 0x131418, 1.0, noise_bump=0.8),
    "curtain": material("curtain", 0xb8ac9a, 0.95, sheen=0.5),
    "bezel": material("bezel", 0x070708, 0.6),
    "foliage": material("foliage", 0x2c4a1c, 0.6, sheen=0.3),
    "tableFrame": material("tableFrame", 0x111114, 0.4, 0.6),
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
    "glazing": material("glazing", 0x8fb4d8, 0.05, 0.0),
    "paving": material("paving", 0x2c2d31, 0.95),
    "funnel": material("funnel", 0xf3f4f8, 0.7),
    "led": emissive("led", 0x3f74ff, 12.0),
    "cove": emissive("cove", 0x3d6bff, 60.0),
    "panelLight": emissive("panelLight", 0xf2f5ff, 6.0),
    "screen": emissive("screen", 0x2a3350, 4.0),       # the HTML is pinned over this in the browser
    "programme": emissive("programme", 0x16224f, 4.0),  # the hall screen: the programme is pinned over it
    "schedule": emissive("schedule", 0x1c2a6b, 1.5),
    "scheduleCard": emissive("scheduleCard", 0xff7a1a, 2.5),
    "scheduleText": emissive("scheduleText", 0xf4f4f4, 2.0),
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
hall = next(r for r in rooms if r["id"] == "hall")["bounds"]


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
    if o.get("linkId") and o["floor"] == 1 and o["height"] <= 0:
        continue   # floor-1 colliders hanging down a stairwell (one is a 6 m sheet across each side stair's foot)
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
    if o["floor"] == 0 and tall and inside({**hall, "x": hall["x"] - 0.5, "y": hall["y"] - 0.5, "w": hall["w"] + 1, "h": hall["h"] + 1},
                                           b["x"] + b["w"] / 2, b["y"] + b["h"] / 2):
        key = "hallColumn" if column else "hallWall"      # the Hollywood room is white
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


FLOOR_KEY = {"corridor": "carpet", "foyer": "carpet", "landing": "carpet", "hall": "hollywoodFloor",
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

# ---------------------------------------------------------------------------------- the Hollywood room
# The exhibition floor downstairs (data/references/, area "hollywood"). A white drop ceiling, the raft,
# runs down the middle with a raised coffer lit blue from a hidden cove; around it the black acoustic
# ceiling with ducts and track spots. White columns, grey carpet, beige curtains on the far (north)
# wall, and on that wall the programme on a 16:10 screen shaped like a laptop's.
SX = 5.9                                        # on the axis between the column lines x = 2.3 and 8.78
NORTH = hall["y"] + hall["h"] - 0.15            # inner face of the north wall
RAFT_Z, COFFER_Z, BLACK_Z = 3.3, 3.85, 4.6
stair_links = [l for l in venue["links"] if l["id"] in ("stair-west", "stair-east")]
stairwells = [{"x": l["bounds"]["x"] - 0.3, "y": l["bounds"]["y"], "w": l["bounds"]["w"] + 0.6, "h": 15.5} for l in stair_links]
raft = {"x": SX - 4.6, "y": hall["y"], "w": 9.2, "h": NORTH - hall["y"]}
coffer = {"x": SX - 2.8, "y": hall["y"] + 6, "w": 5.6, "h": NORTH - 2.15 - hall["y"] - 6}
COVE = 0.25                                      # width of the hidden ledge the LED strip sits on
for cell in subtract_rects(raft, [coffer] + stairwells):
    B.box("raft", cell, RAFT_Z, RAFT_Z + 0.25)
outer = {"x": coffer["x"] - COVE, "y": coffer["y"] - COVE, "w": coffer["w"] + 2 * COVE, "h": coffer["h"] + 2 * COVE}
for wb in ({**outer, "h": 0.05}, {**outer, "y": outer["y"] + outer["h"] - 0.05, "h": 0.05},
           {**outer, "w": 0.05}, {**outer, "x": outer["x"] + outer["w"] - 0.05, "w": 0.05}):
    B.box("raft", wb, RAFT_Z + 0.25, COFFER_Z)
B.box("raft", outer, COFFER_Z, COFFER_Z + 0.05)
for wb in ({"x": coffer["x"], "y": coffer["y"] - 0.17, "w": coffer["w"], "h": 0.04},
           {"x": coffer["x"], "y": coffer["y"] + coffer["h"] + 0.13, "w": coffer["w"], "h": 0.04},
           {"x": coffer["x"] - 0.17, "y": coffer["y"], "w": 0.04, "h": coffer["h"]},
           {"x": coffer["x"] + coffer["w"] + 0.13, "y": coffer["y"], "w": 0.04, "h": coffer["h"]}):
    B.box("cove", wb, RAFT_Z + 0.25, RAFT_Z + 0.27)
for cell in subtract_rects(hall, stairwells):
    B.box("acoustic", cell, BLACK_Z, BLACK_Z + 0.1)
B.box("acoustic", {"x": hall["x"], "y": NORTH - 0.04, "w": hall["w"], "h": 0.04}, RAFT_Z, BLACK_Z)

# recessed square panels: two rows in the coffer, one row each side of it, two above the screen
panels = []
y = coffer["y"] + 1.6
while y < coffer["y"] + coffer["h"] - 0.5:
    panels += [(SX - 1.5, y, COFFER_Z), (SX + 1.5, y, COFFER_Z), (raft["x"] + 0.8, y, RAFT_Z), (raft["x"] + raft["w"] - 0.8, y, RAFT_Z)]
    y += 3.2
panels += [(SX - 3.6, NORTH - 1.1, RAFT_Z), (SX + 3.6, NORTH - 1.1, RAFT_Z)]
panels = [p for p in panels if not any(inside(sw, p[0], p[1]) for sw in stairwells)]
for (px, py, pz) in panels:
    B.box("panelLight", {"x": px - 0.3, "y": py - 0.3, "w": 0.6, "h": 0.6}, pz - 0.012, pz - 0.002)


def tube(key, x, z, y0, y1, r, segs=16):
    """A round duct along y."""
    verts = [(x + r * math.cos(2 * math.pi * k / segs), yy, z + r * math.sin(2 * math.pi * k / segs)) for yy in (y0, y1) for k in range(segs)]
    B.mesh(key, verts, [(k, (k + 1) % segs, segs + (k + 1) % segs, segs + k) for k in range(segs)])


# the black ceiling either side of the raft: a duct and a line of track spots
spots = []
for side in (-1, 1):
    edge = raft["x"] if side < 0 else raft["x"] + raft["w"]
    tube("steel", edge + side * 1.9, BLACK_Z - 0.45, hall["y"] + 0.3, NORTH - 0.3, 0.28)
    y = hall["y"] + 2
    while y < NORTH - 1:
        dx = edge + side * 0.8
        if not any(inside(sw, dx, y) for sw in stairwells):
            B.box("tableFrame", {"x": dx - 0.07, "y": y - 0.07, "w": 0.14, "h": 0.14}, BLACK_Z - 0.3, BLACK_Z)
            spots.append((dx, y, BLACK_Z - 0.32))
        y += 3.2

# trailing greenery hanging from the raft along both long edges of the coffer, and at its far corners
rng = random.Random(7)
clumps = [(gx, y) for gx in (coffer["x"] - 0.12, coffer["x"] + coffer["w"] + 0.12)
          for y in [coffer["y"] + 1.0 + 3.2 * k for k in range(int((coffer["h"] - 1.6) / 3.2) + 1)]]
clumps += [(coffer["x"] + 0.5, coffer["y"] + coffer["h"] + 0.12), (coffer["x"] + coffer["w"] - 0.5, coffer["y"] + coffer["h"] + 0.12)]
for (gx, gy) in clumps:
    for _ in range(40):                                   # strands of ivy, leaves every few centimetres
        x, y, z = gx + rng.uniform(-0.4, 0.4), gy + rng.uniform(-0.4, 0.4), RAFT_Z - 0.01
        for _ in range(int(rng.uniform(0.1, 0.8) ** 1.5 / 0.03) + 2):
            x, y, z = x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.02, 0.02), z - 0.03
            u = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 0.4))).normalized()
            v = u.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
            c, a_, b_ = Vector((x, y, z)), 0.055 * rng.uniform(0.7, 1.2), 0.035 * rng.uniform(0.7, 1.2)
            B.mesh("foliage", [c - u * a_, c - v * b_, c + u * a_, c + v * b_], [(0, 1, 2, 3)])

# beige curtains along the north wall: a pleated sheet, smooth shaded
xs = [hall["x"] + 0.2 + i * 0.05 for i in range(int((hall["w"] - 6.9) / 0.05))]
cverts = [(x, NORTH - 0.09 + 0.05 * math.sin(2 * math.pi * x / 0.32), z) for x in xs for z in (0.02, RAFT_Z + 0.05)]
cme = bpy.data.meshes.new("curtain")
cme.from_pydata(cverts, [], [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(len(xs) - 1)])
cme.shade_smooth()
cob = bpy.data.objects.new("curtain", cme)
cob.data.materials.append(M["curtain"])
scene.collection.objects.link(cob)

# the programme screen: 16:10 like a laptop panel, thin bezel with a deeper chin, in front of the curtains
SCREEN = {"x": SX, "y": NORTH - 0.32, "z": 1.85, "w": 3.84, "h": 2.4}
BEZEL, CHIN = 0.07, 0.18
B.box("bezel", {"x": SX - SCREEN["w"] / 2 - BEZEL, "y": SCREEN["y"] - 0.05, "w": SCREEN["w"] + 2 * BEZEL, "h": 0.1},
      SCREEN["z"] - SCREEN["h"] / 2 - CHIN, SCREEN["z"] + SCREEN["h"] / 2 + BEZEL)
sy_ = SCREEN["y"] - 0.055
screen_corners = [(SX - SCREEN["w"] / 2, sy_, SCREEN["z"] - SCREEN["h"] / 2), (SX + SCREEN["w"] / 2, sy_, SCREEN["z"] - SCREEN["h"] / 2),
                (SX + SCREEN["w"] / 2, sy_, SCREEN["z"] + SCREEN["h"] / 2), (SX - SCREEN["w"] / 2, sy_, SCREEN["z"] + SCREEN["h"] / 2)]
B.mesh("programme", screen_corners, [(0, 1, 2, 3)])


def schedule_board(face_x, face, yc, w=1.7, h=0.96, z0=1.35):
    """A wall screen with the next timeslot as orange cards, on the wall plane x = face_x facing +x (face=1) or -x."""
    def slab(key, y0, y1, za, zb, depth):
        x0 = face_x + face * depth
        B.box(key, {"x": min(face_x, x0), "y": y0, "w": abs(x0 - face_x), "h": y1 - y0}, za, zb)
    slab("bezel", yc - w / 2 - 0.04, yc + w / 2 + 0.04, z0 - 0.04, z0 + h + 0.04, 0.06)
    slab("schedule", yc - w / 2, yc + w / 2, z0, z0 + h, 0.065)
    slab("scheduleText", yc - w / 2 + 0.08, yc - w / 2 + 0.7, z0 + h - 0.13, z0 + h - 0.08, 0.07)
    cw, ch = (w - 0.16 - 0.08) / 3, (h - 0.26 - 0.06) / 2
    for row in range(2):
        for col in range(3):
            ya = yc - w / 2 + 0.08 + col * (cw + 0.04)
            za = z0 + 0.08 + (1 - row) * (ch + 0.06)
            slab("scheduleCard", ya, ya + cw, za, za + ch, 0.07)
            for k, frac in enumerate((0.8, 0.55)):
                slab("scheduleText", ya + 0.04, ya + 0.04 + (cw - 0.08) * frac, za + ch - 0.1 - k * 0.08, za + ch - 0.07 - k * 0.08, 0.075)


# the real screens hung on the near wall of each stairwell: the side facing the middle of the room
for l in stair_links:
    b = l["bounds"]
    west = b["x"] + b["w"] / 2 < SX
    schedule_board(b["x"] + b["w"] + 0.3 if west else b["x"] - 0.3, 1 if west else -1, b["y"] + b["h"] - 3.0)

# black wire-frame high tables, as on the floor during the event
for (tx, ty) in ((SX - 4.9, NORTH - 3.0), (SX + 3.4, NORTH - 7.8), (SX - 4.9, NORTH - 7.5), (SX - 2.0, NORTH - 10.5)):
    for (lx, ly) in ((-0.3, -0.3), (0.27, -0.3), (-0.3, 0.27), (0.27, 0.27)):
        B.box("tableFrame", {"x": tx + lx, "y": ty + ly, "w": 0.03, "h": 0.03}, 0, 1.08)
    B.box("tableFrame", {"x": tx - 0.3, "y": ty - 0.3, "w": 0.6, "h": 0.6}, 1.08, 1.11)

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
    point(f"{sid}-foot", (sb["x"] + sb["w"] / 2, sb["y"] + sb["h"] + 2.0, 3.0), 300, (0.85, 0.88, 1.0))
    point(f"{sid}-low", (sb["x"] + sb["w"] / 2, sb["y"] + sb["h"] * 0.7, 2.6), 500, (0.8, 0.85, 1.0))
    point(f"{sid}-high", (sb["x"] + sb["w"] / 2, sb["y"] + sb["h"] * 0.25, FH - 0.6), 500, (0.8, 0.85, 1.0))
# the Hollywood room: an area light behind every ceiling panel, warm track spots in the black ceiling
for (px, py, pz) in panels:
    area(f"panel-{px:.1f}-{py:.1f}", (px, py, pz - 0.02), 0.6, 100, (0.97, 0.98, 1.0))
for (tx, ty, tz) in spots:
    spot = bpy.data.lights.new(f"track-{tx:.1f}-{ty:.1f}", "SPOT")
    spot.energy, spot.spot_size, spot.spot_blend, spot.color = 350, math.radians(40), 0.5, (1.0, 0.92, 0.8)
    so = bpy.data.objects.new(spot.name, spot)
    so.location, so.rotation_euler = (tx, ty, tz), (0.35, 0, 0)
    scene.collection.objects.link(so)
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
    """Eye height, square on to the programme screen, the screen filling a bit under half the frame."""
    d = fit_distance(SCREEN["w"] + 2 * BEZEL, SCREEN["h"] + BEZEL + CHIN, 50, 0.45)
    return (SCREEN["x"], SCREEN["y"] - d, 1.7), (SCREEN["x"], SCREEN["y"], SCREEN["z"]), 50


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
    lp, _, hall_fov = hall_pose()
    wx, yc = door["wall_x"], door["yc"]
    # into the stairwell through the side opening at its foot (between the wall end and the stub)
    gap_y, in_x = stair["y"] + stair["h"] + 2.55, stair["x"] - 0.3 if sx > lp[0] else stair["x"] + stair["w"] + 0.3
    pts = [lp, (in_x + (-1.6 if sx > lp[0] else 1.6), gap_y, 1.7), (sx, gap_y - 0.25, 1.7), (sx, stair["y"] + stair["h"] - 0.4, 1.75),
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
        cam_data.angle_y = math.radians(hall_fov + (fov_end - hall_fov) * u)
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
shots["hall"] = {"kind": "still", "overlay": {"programme": screen_quad(screen_corners, hall_cam)}}
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
    elif what.startswith("walk@"):
        for fr in what[5:].split("+"):
            scene.frame_set(int(fr))
            scene.render.filepath = str(OUT / f"walk-{n}-f{int(fr):03d}.png")
            bpy.ops.render.render(write_still=True)
    elif what == "walk":
        scene.frame_start, scene.frame_end = 1, frames + 1
        scene.render.filepath = str(OUT / f"walk-{n}" / "f_")
        bpy.ops.render.render(animation=True)
print("done", json.dumps({k: v.get("frames") for k, v in shots.items()}))
