"""Build the Kinepolis venue in Blender from site/kino/venue.json, set up the shots, optionally render.

The same rules as the browser renderer (site/kino/kino.js) turn Ghost Light's venue model into
geometry; Blender adds real light: path tracing, soft shadows, bounce light, emissive LEDs.

Run with Blender's Python (Windows Blender, driven from WSL):
  blender.exe -b --python scripts/blender/build_scene.py -- --root C:/path/to/repo --room 8 \
      --save C:/renders/kino.blend [--render hall,seat,walk] [--out C:/renders] [--samples 96] [--preview]
  (--render walk@20+60 renders single frames of the walk, ref:hollywood renders from the camera of a
   reference photo in data/references/cameras.json, both for look-dev)

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
ap.add_argument("--lookdev", action="store_true", help="Cycles at half resolution: look-dev you can trust")
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


def material(name, color, rough=0.85, metal=0.0, emission=None, strength=0.0, sheen=0.0, noise_bump=0.0, speckle=0.0, bevel=0.0, grime=0.0):
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
    if grime:
        # dirt collects where surfaces meet (column foot, wall corners): darken by ambient occlusion
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.35
        ao.only_local = True
        dark = nt.nodes.new("ShaderNodeMapRange")
        dark.inputs["To Min"].default_value, dark.inputs["To Max"].default_value = 1 - grime, 1.0
        nt.links.new(ao.outputs["AO"], dark.inputs["Value"])
        _, a, b, out = mix_multiply(nt)
        a.default_value = srgb(color)
        nt.links.new(dark.outputs["Result"], b)
        nt.links.new(out, bsdf.inputs["Base Color"])
    if bevel:
        # no razor edges: shade every box edge as rounded over a few millimetres
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.inputs["Radius"].default_value = bevel
        nt.links.new(bev.outputs["Normal"], bsdf.inputs["Normal"])
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


TEX = ROOT / "data" / "textures"


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def mix_multiply(nt):
    """A colour Mix node set to multiply; returns (node, A, B, Result) sockets, found by type since the socket
    order changes between Blender versions."""
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type, mx.blend_type = "RGBA", "MULTIPLY"
    mx.inputs["Factor"].default_value = 1.0
    a, b = [i for i in mx.inputs if i.type == "RGBA"][:2]
    out = next(o for o in mx.outputs if o.type == "RGBA")
    return mx, a, b, out


def textured(name, tex, scale, tint=None, rough=None, normal=1.0, sheen=0.0, tiles=None, uv=False):
    """PBR material from a set fetched by scripts/fetch_textures.py, box-projected in object space (the batched
    meshes have no UVs, and every object sits at the origin, so object space is world space in metres).
    tint: replace the texture's colour with this one, keeping its light and dark detail.
    tiles: carpet tiles of this size in metres, laid quarter-turned at random, each with its own mottling,
    shade and sheen.
    uv: map by the mesh's UVs (in metres) instead, for surfaces like curtains where box projection seams."""
    d = TEX / tex
    if not (d / "color.jpg").exists():
        print(f"textures for {name} missing (run scripts/fetch_textures.py); using a flat colour")
        return material(name, tint or 0x888888, rough or 0.9, sheen=sheen)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / scale,) * 3
    pos = coord.outputs["UV" if uv else "Object"]
    if tiles:
        # which tile, a random number per tile, and the position turned a quarter on half of the tiles
        cell = node(nt, "ShaderNodeVectorMath")
        cell.operation = "SCALE"
        cell.inputs["Scale"].default_value = 1 / tiles
        nt.links.new(coord.outputs["Object"], cell.inputs[0])
        flo = nt.nodes.new("ShaderNodeVectorMath")
        flo.operation = "FLOOR"
        nt.links.new(cell.outputs["Vector"], flo.inputs[0])
        rnd = nt.nodes.new("ShaderNodeTexWhiteNoise")
        nt.links.new(flo.outputs["Vector"], rnd.inputs["Vector"])
        sep, comb = nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs[0])
        neg = node(nt, "ShaderNodeMath")
        neg.operation = "MULTIPLY"
        neg.inputs[1].default_value = -1.0
        nt.links.new(sep.outputs["X"], neg.inputs[0])
        nt.links.new(sep.outputs["Y"], comb.inputs["X"])
        nt.links.new(neg.outputs["Value"], comb.inputs["Y"])
        nt.links.new(sep.outputs["Z"], comb.inputs["Z"])
        turn = node(nt, "ShaderNodeMath")
        turn.operation = "GREATER_THAN"
        turn.inputs[1].default_value = 0.5
        nt.links.new(rnd.outputs["Value"], turn.inputs[0])
        pick = nt.nodes.new("ShaderNodeMix")
        pick.data_type = "VECTOR"
        vin = [i for i in pick.inputs if i.type == "VECTOR"]
        nt.links.new(turn.outputs["Value"], next(i for i in pick.inputs if i.type == "VALUE"))
        nt.links.new(coord.outputs["Object"], vin[1])
        nt.links.new(comb.outputs["Vector"], vin[2])
        pos = next(o for o in pick.outputs if o.type == "VECTOR")
    nt.links.new(pos, mapping.inputs["Vector"])

    def image(file, color_space):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(d / file), check_existing=True)
        t.image.colorspace_settings.name = color_space
        if not uv:
            t.projection, t.projection_blend = "BOX", 0.25
        nt.links.new(mapping.outputs["Vector"], t.inputs["Vector"])
        return t
    col = image("color.jpg", "sRGB")
    color_out = col.outputs["Color"]
    if tint is not None:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(color_out, bw.inputs["Color"])
        _, a, b, out = mix_multiply(nt)
        a.default_value = tuple(c * 2 for c in srgb(tint)[:3]) + (1,)   # texture luminance ~0.5
        nt.links.new(bw.outputs["Val"], b)
        color_out = out
    if tiles:
        shift = nt.nodes.new("ShaderNodeVectorMath")                 # each tile samples the mottle elsewhere
        shift.operation = "MULTIPLY_ADD"
        shift.inputs[1].default_value = (37.0, 53.0, 0.0)
        nt.links.new(rnd.outputs["Color"], shift.inputs[0])
        nt.links.new(pos, shift.inputs[2])
        mot = node(nt, "ShaderNodeTexNoise", Scale=11.0, Detail=8.0, Roughness=0.7)
        nt.links.new(shift.outputs["Vector"], mot.inputs["Vector"])
        f1 = node(nt, "ShaderNodeMath")
        f1.operation = "MULTIPLY_ADD"
        f1.inputs[1].default_value, f1.inputs[2].default_value = 2.6, -0.45
        nt.links.new(mot.outputs["Fac"], f1.inputs[0])
        f2 = node(nt, "ShaderNodeMath")
        f2.operation = "MULTIPLY_ADD"
        f2.inputs[1].default_value = 0.4
        nt.links.new(rnd.outputs["Value"], f2.inputs[0])
        nt.links.new(f1.outputs["Value"], f2.inputs[2])
        # small dark specks, like the photos' carpet
        speck = node(nt, "ShaderNodeTexNoise", Scale=38.0, Detail=3.0)
        nt.links.new(shift.outputs["Vector"], speck.inputs["Vector"])
        ramp = node(nt, "ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.56, 0.66
        ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = 1.0, 0.55
        nt.links.new(speck.outputs["Fac"], ramp.inputs["Value"])
        f3 = node(nt, "ShaderNodeMath")
        f3.operation = "MULTIPLY"
        nt.links.new(f2.outputs["Value"], f3.inputs[0])
        nt.links.new(ramp.outputs["Result"], f3.inputs[1])
        _, a, b, out = mix_multiply(nt)
        nt.links.new(color_out, a)
        nt.links.new(f3.outputs["Value"], b)
        color_out = out
    nt.links.new(color_out, bsdf.inputs["Base Color"])
    if rough is None and tiles:
        sheen_shift = node(nt, "ShaderNodeMath")                     # tiles catch the light differently
        sheen_shift.operation = "MULTIPLY_ADD"
        sheen_shift.inputs[1].default_value, sheen_shift.inputs[2].default_value = 0.16, 0.86
        nt.links.new(rnd.outputs["Value"], sheen_shift.inputs[0])
        rmul = node(nt, "ShaderNodeMath")
        rmul.operation = "MULTIPLY"
        nt.links.new(image("rough.jpg", "Non-Color").outputs["Color"], rmul.inputs[0])
        nt.links.new(sheen_shift.outputs["Value"], rmul.inputs[1])
        nt.links.new(rmul.outputs["Value"], bsdf.inputs["Roughness"])
    elif rough is None:
        nt.links.new(image("rough.jpg", "Non-Color").outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    nm = node(nt, "ShaderNodeNormalMap", Strength=normal)
    nt.links.new(image("normal.jpg", "Non-Color").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
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
    "hollywoodFloor": textured("hollywoodFloor", "carpet", 0.6, tint=0xa29b93, normal=1.0, tiles=0.5),
    "hallColumn": material("hallColumn", 0xebeae6, 0.6, bevel=0.012, grime=0.3),
    "hallWall": material("hallWall", 0xe4e2dd, 0.85, bevel=0.01, grime=0.25),
    "raft": material("raft", 0xf1f1ee, 0.9, bevel=0.01),
    "acoustic": material("acoustic", 0x10131c, 1.0, noise_bump=1.0),
    "curtain": textured("curtain", "curtain", 1.4, tint=0x8f8574, normal=0.7, sheen=0.5, uv=True),
    "frostedGlass": material("frostedGlass", 0xdfeee8, 0.2),
    "plinth": material("plinth", 0x8d8d8a, 0.6, bevel=0.005),
    "speaker": material("speaker", 0xe9e9e5, 0.45, bevel=0.01),
    "hexFrame": material("hexFrame", 0xd2d5d8, 0.3, 0.8),         # brushed aluminium: panel rims, mullions
    "extinguisher": material("extinguisher", 0xb3121a, 0.3),
    "exitSign": emissive("exitSign", 0x18c060, 4.0),
    "downlight": emissive("downlight", 0xfff1e0, 25.0),
    "bezel": material("bezel", 0x070708, 0.6),
    "foliage": material("foliage", 0x4a7a3a, 0.55, sheen=0.3),
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
    "cove": emissive("cove", 0x3d6bff, 10.0),
    "panelLight": emissive("panelLight", 0xfff3e6, 8.0),       # the look of the panels; area lights below do the lighting      # about 4000 K, like the photos
    "screen": emissive("screen", 0x2a3350, 4.0),       # the HTML is pinned over this in the browser
    "programme": emissive("programme", 0x16224f, 4.0),  # the hall screen: the programme is pinned over it
    "schedule": emissive("schedule", 0x1c2a6b, 1.5),
    "scheduleCard": emissive("scheduleCard", 0xff7a1a, 2.5),
    "scheduleText": emissive("scheduleText", 0xf4f4f4, 2.0),
}
M["glazing"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.9
# leaves are thin: let a third of the light through, so backlit ivy glows like the real plants
_fnt = M["foliage"].node_tree
_tr = _fnt.nodes.new("ShaderNodeBsdfTranslucent")
_tr.inputs["Color"].default_value = srgb(0x7fb04a)
_mixs = _fnt.nodes.new("ShaderNodeMixShader")
_mixs.inputs["Fac"].default_value = 0.3
_fnt.links.new(_fnt.nodes["Principled BSDF"].outputs["BSDF"], _mixs.inputs[1])
_fnt.links.new(_tr.outputs["BSDF"], _mixs.inputs[2])
_fnt.links.new(_mixs.outputs["Shader"], _fnt.nodes["Material Output"].inputs["Surface"])
M["frostedGlass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
M["frostedGlass"].node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.5


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


def intersect(a, b):
    x0, y0 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x1, y1 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0} if x1 > x0 and y1 > y0 else None


# The Hollywood room has a drop ceiling at HALL_CEIL. Ghost Light stacks the floors closer than the
# real building, so cinema walls and seating from floor 1 would hang into the room: over the room's
# footprint they stop at HALL_CLEAR, just above the drop ceiling.
HALL_CEIL, HALL_CLEAR = 3.0, 3.3
stair_links = [l for l in venue["links"] if l["id"] in ("stair-west", "stair-east")]
stairwells = [{"x": l["bounds"]["x"] - 0.3, "y": l["bounds"]["y"], "w": l["bounds"]["w"] + 0.6, "h": 15.5} for l in stair_links]


def box_clear_of_hall(key, b, bottom, top):
    over = intersect(b, hall)
    if not over or bottom >= HALL_CLEAR:
        B.box(key, b, bottom, top)
        return
    for cell in subtract_rects(b, [over]):
        B.box(key, cell, bottom, top)
    B.box(key, over, max(bottom, HALL_CLEAR), top)


hall_pad = {**hall, "x": hall["x"] - 0.5, "y": hall["y"] - 0.5, "w": hall["w"] + 1, "h": hall["h"] + 1}
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
    in_hall = o["floor"] == 0 and inside(hall_pad, b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
    if o["floor"] == 0 and not in_hall:
        for a in auditoriums:
            if intersect(b, a["bounds"]):
                top = min(top, FH - a.get("rake", 0) - 0.35)
    key = "column" if column else "wall" if tall else (o.get("material") if o.get("material") in M else "concrete")
    if in_hall and tall:
        if any(intersect(b, sw) for sw in stairwells):
            # the stairwells are boxed in teal frosted glass up to the drop ceiling
            B.box("frostedGlass", b, bottom, HALL_CEIL)
            B.box("hallWall", b, HALL_CEIL, top)
            continue
        key, top = ("hallColumn" if column else "hallWall"), HALL_CEIL + 0.25     # white, up to the drop ceiling
    if o["floor"] == 1 and tall:
        box_clear_of_hall(key, b, bottom, top)
        continue
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
        if rake:
            box_clear_of_hall("rake", sl, max(datum + L["base"] - 0.3, top - 0.6), top)
        else:
            B.box("stair", sl, datum + L["base"] - 0.3, top)
        if not rake:
            edge = 0 if L["ascending"] else going - 0.05
            st = {"x": sl["x"] + edge, "y": b["y"], "w": 0.05, "h": b["h"]} if along_x else \
                 {"x": b["x"], "y": sl["y"] + edge, "w": b["w"], "h": 0.05}
            B.box("nosing", st, top - 0.004, top + 0.006)


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


def cylinder(key, cx, cy, z0, z1, r, segs=16):
    ring = [(cx + r * math.cos(2 * math.pi * k / segs), cy + r * math.sin(2 * math.pi * k / segs)) for k in range(segs)]
    B.mesh(key, [(x, y, z) for z in (z0, z1) for x, y in ring],
           [tuple(reversed(range(segs))), tuple(range(segs, 2 * segs)), *[(k, (k + 1) % segs, segs + (k + 1) % segs, segs + k) for k in range(segs)]])


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
        box_clear_of_hall("audWall", wb, lo, hi)
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
# The exhibition floor downstairs, after the photos in data/references/ (area "hollywood"). A white drop
# ceiling at HALL_CEIL over the whole room with hexagonal LED panels and downlights; at the entrance end
# a raised coffer lit blue from a hidden cove, and before it a higher ceiling with track spots and black
# acoustic panels. White columns with speakers, mottled tile carpet, beige curtains on the far (north)
# wall, and on that wall the programme on a 16:10 screen shaped like a laptop's.
SX = 5.9                                        # on the axis between the column lines x = 2.3 and 8.78
NORTH = hall["y"] + hall["h"] - 0.15            # inner face of the north wall
NEAR_Z = 4.3                                     # ceiling over the entrance end
entrance = {"x": hall["x"], "y": hall["y"], "w": hall["w"], "h": 11.0}
coffer = {"x": SX - 4.6, "y": entrance["y"] + entrance["h"], "w": 9.2, "h": 11.0}
inner = {"x": coffer["x"] + 0.7, "y": coffer["y"] + 0.7, "w": coffer["w"] - 1.4, "h": coffer["h"] - 1.4}
STEP_Z, INNER_Z, COVE = HALL_CEIL + 0.25, HALL_CEIL + 0.6, 0.25
for cell in subtract_rects(hall, [entrance, coffer] + stairwells):
    B.box("raft", cell, HALL_CEIL, HALL_CEIL + 0.25)
for cell in subtract_rects(coffer, [inner]):                      # the coffer's first step
    B.box("raft", cell, STEP_Z, STEP_Z + 0.1)
outer = {"x": inner["x"] - COVE, "y": inner["y"] - COVE, "w": inner["w"] + 2 * COVE, "h": inner["h"] + 2 * COVE}
for wb in ({**outer, "h": 0.05}, {**outer, "y": outer["y"] + outer["h"] - 0.05, "h": 0.05},
           {**outer, "w": 0.05}, {**outer, "x": outer["x"] + outer["w"] - 0.05, "w": 0.05}):
    B.box("raft", wb, STEP_Z + 0.1, INNER_Z)
B.box("raft", outer, INNER_Z, INNER_Z + 0.05)
for wb in ({"x": inner["x"], "y": inner["y"] - 0.17, "w": inner["w"], "h": 0.04},
           {"x": inner["x"], "y": inner["y"] + inner["h"] + 0.13, "w": inner["w"], "h": 0.04},
           {"x": inner["x"] - 0.17, "y": inner["y"], "w": 0.04, "h": inner["h"]},
           {"x": inner["x"] + inner["w"] + 0.13, "y": inner["y"], "w": 0.04, "h": inner["h"]}):
    B.box("cove", wb, STEP_Z + 0.1, STEP_Z + 0.12)
# entrance end: higher ceiling, the bulkhead down to the drop ceiling, black acoustic panels at the sides
B.box("raft", {k: entrance[k] for k in "xywh"}, NEAR_Z, NEAR_Z + 0.1)
B.box("raft", {"x": hall["x"], "y": entrance["y"] + entrance["h"] - 0.05, "w": hall["w"], "h": 0.05}, HALL_CEIL + 0.25, NEAR_Z)
for (x0, x1) in ((hall["x"], coffer["x"] - 0.6), (coffer["x"] + coffer["w"] + 0.6, hall["x"] + hall["w"])):
    B.box("acoustic", {"x": x0, "y": entrance["y"], "w": x1 - x0, "h": entrance["h"] - 0.3}, NEAR_Z - 0.35, NEAR_Z)
spots = []
for sy in (entrance["y"] + 2.5, entrance["y"] + 5.0):
    for k in range(-3, 4):
        sx = SX + k * 1.6
        B.box("tableFrame", {"x": sx - 0.02, "y": sy - 0.5, "w": 0.04, "h": 1.0}, NEAR_Z - 0.04, NEAR_Z)   # track
        cylinder("tableFrame", sx, sy, NEAR_Z - 0.32, NEAR_Z - 0.04, 0.055)
        spots.append((sx, sy, NEAR_Z - 0.3))


def hex_panel(cx, cy, z, length=0.9, width=0.34, depth=0.05):
    """A surface-mounted LED panel: an elongated hexagon in plan, white rim, glowing underside."""
    half, cut = length / 2, width / 2
    ring = [(-half, 0), (-half + cut, -cut), (half - cut, -cut), (half, 0), (half - cut, cut), (-half + cut, cut)]
    top = [(cx + x, cy + y, z) for x, y in ring]
    bot = [(cx + x, cy + y, z - depth) for x, y in ring]
    B.mesh("hexFrame", top + bot, [tuple(range(6)), *[(i, (i + 1) % 6, 6 + (i + 1) % 6, 6 + i) for i in range(6)]])
    glow = [(cx + x * 0.94, cy + y * 0.86, z - depth - 0.002) for x, y in ring]
    B.mesh("panelLight", glow, [tuple(reversed(range(6)))])


# hexagon panels on a grid between the columns, downlights between them
lights, downlights = [], []
for gx in [SX + 3.24 * k for k in range(-9, 8)]:
    for gy in [NORTH - 2.2 - 3.2 * k for k in range(0, 16)]:
        if not (hall["x"] + 1 < gx < hall["x"] + hall["w"] - 1 and gy > entrance["y"] + entrance["h"] + 0.5):
            continue
        if inside(coffer, gx, gy) or any(inside({**sw, "x": sw["x"] - 0.8, "w": sw["w"] + 1.6}, gx, gy) for sw in stairwells):
            continue
        hex_panel(gx, gy, HALL_CEIL)
        lights.append((gx, gy, HALL_CEIL))
        B.mesh("downlight", [(gx + 1.62 + 0.08 * math.cos(a), gy + 0.08 * math.sin(a), HALL_CEIL - 0.003)
                             for a in [2 * math.pi * i / 12 for i in range(12)]], [tuple(reversed(range(12)))])
        downlights.append((gx + 1.62, gy))
for (gx, gy) in [(inner["x"] + 1.2 + 2.2 * i, inner["y"] + 1.5 + 2.5 * j) for i in range(3) for j in range(4)]:
    hex_panel(gx, gy, INNER_Z)
    lights.append((gx, gy, INNER_Z))

# columns: a grey plinth, and a white speaker high up on the face towards the entrance
for o in venue["obstacles"]:
    b = o["bounds"]
    if o["floor"] == 0 and o["height"] >= 3 and b["w"] < 1.2 and b["h"] < 1.2 and inside(hall, b["x"] + b["w"] / 2, b["y"] + b["h"] / 2):
        B.box("plinth", {"x": b["x"] - 0.015, "y": b["y"] - 0.015, "w": b["w"] + 0.03, "h": b["h"] + 0.03}, 0, 0.1)
        B.box("speaker", {"x": b["x"] + b["w"] / 2 - 0.13, "y": b["y"] - 0.2, "w": 0.26, "h": 0.2}, 2.42, 2.78)
        B.box("tableFrame", {"x": b["x"] + b["w"] / 2 - 0.03, "y": b["y"] - 0.05, "w": 0.06, "h": 0.05}, 2.55, 2.65)

# fire extinguishers on every third column, exit signs over the side walls, smoke detectors on the ceiling
cols = [o["bounds"] for o in venue["obstacles"] if o["floor"] == 0 and o["height"] >= 3 and o["bounds"]["w"] < 1.2
        and o["bounds"]["h"] < 1.2 and inside(hall, o["bounds"]["x"] + o["bounds"]["w"] / 2, o["bounds"]["y"] + o["bounds"]["h"] / 2)]
for i, b in enumerate(cols):
    if i % 3 == 1:
        ex, ey = b["x"] + b["w"] + 0.1, b["y"] - 0.12
        cylinder("extinguisher", ex, ey, 0.6, 1.08, 0.075)          # hung on a bracket, as in the photo
        cylinder("tableFrame", ex, ey, 1.08, 1.15, 0.025)
        B.box("tableFrame", {"x": ex - 0.04, "y": ey + 0.04, "w": 0.08, "h": 0.06}, 0.95, 1.15)
for (sx_, sy_) in ((hall["x"] + 0.05, -10.0), (hall["x"] + 0.05, 8.0), (hall["x"] + hall["w"] - 0.2, -12.0)):
    B.box("exitSign", {"x": sx_, "y": sy_ - 0.2, "w": 0.15, "h": 0.4}, HALL_CEIL - 0.42, HALL_CEIL - 0.2)
for (gx, gy, _) in lights[::3]:
    cylinder("speaker", gx + 0.9, gy + 1.1, HALL_CEIL - 0.04, HALL_CEIL, 0.06)

# the stairwells' glass: white mullions every 1.25 m, and glass across the stair's high (south) end
for l in stair_links:
    b = l["bounds"]
    B.box("frostedGlass", {"x": b["x"] - 0.3, "y": b["y"] - 0.3, "w": b["w"] + 0.6, "h": 0.3}, 0, HALL_CEIL)
    for fx in (b["x"] - 0.33, b["x"] + b["w"] + 0.3):
        y = b["y"] - 0.3
        while y < b["y"] + 12.9:
            B.box("hexFrame", {"x": fx, "y": y, "w": 0.03, "h": 0.05}, 0, HALL_CEIL)
            y += 1.25
        B.box("plinth", {"x": fx - 0.01, "y": b["y"] - 0.3, "w": 0.05, "h": 13.2}, 0, 0.12)
    for fx in [b["x"] - 0.3 + 1.25 * k for k in range(4)]:
        B.box("hexFrame", {"x": fx, "y": b["y"] - 0.33, "w": 0.05, "h": 0.03}, 0, HALL_CEIL)

# trusses along the side walls, a box truss with its chords and a zigzag of diagonals
for tx in (hall["x"] + 0.9, hall["x"] + hall["w"] - 0.9):
    y0, y1, z = entrance["y"] + entrance["h"] + 1, NORTH - 2, HALL_CEIL - 0.45
    for (dx, dz) in ((-0.15, 0), (0.15, 0), (-0.15, 0.3), (0.15, 0.3)):
        B.box("steel", {"x": tx + dx - 0.02, "y": y0, "w": 0.04, "h": y1 - y0}, z + dz - 0.02, z + dz + 0.02)
    y, k = y0, 0
    while y < y1 - 0.4:
        for dx in (-0.15, 0.15):
            za, zb = (z, z + 0.3) if k % 2 == 0 else (z + 0.3, z)
            B.mesh("steel", [(tx + dx - 0.012, y, za), (tx + dx + 0.012, y, za), (tx + dx + 0.012, y + 0.4, zb), (tx + dx - 0.012, y + 0.4, zb)], [(0, 1, 2, 3)])
        y, k = y + 0.4, k + 1

# trailing greenery: along the coffer, and clumps here and there on the ceiling (never over the screen)
rng = random.Random(7)
clumps = [(gx, y) for gx in (coffer["x"] - 0.12, coffer["x"] + coffer["w"] + 0.12) for y in (coffer["y"] + 1.5, coffer["y"] + 5.5, coffer["y"] + 9.5)]
while len(clumps) < 22:
    gx, gy = rng.uniform(hall["x"] + 3, hall["x"] + hall["w"] - 3), rng.uniform(entrance["y"] + 8, NORTH - 1.5)
    if abs(gx - SX) < 3.5 and gy > NORTH - 7 or any(inside({**sw, "x": sw["x"] - 1, "w": sw["w"] + 2}, gx, gy) for sw in stairwells):
        continue
    if all(abs(gx - lx) > 0.9 or abs(gy - ly) > 0.6 for lx, ly, _ in lights):
        clumps.append((gx, gy))
for (gx, gy) in clumps:
    for _ in range(40):                                   # strands of ivy, leaves every few centimetres
        x, y, z = gx + rng.uniform(-0.4, 0.4), gy + rng.uniform(-0.4, 0.4), HALL_CEIL - 0.01
        for _ in range(int(rng.uniform(0.1, 0.8) ** 1.5 / 0.03) + 2):
            x, y, z = x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.02, 0.02), z - 0.03
            u = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 0.4))).normalized()
            v = u.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
            c, a_, b_ = Vector((x, y, z)), 0.055 * rng.uniform(0.7, 1.2), 0.035 * rng.uniform(0.7, 1.2)
            B.mesh("foliage", [c - u * a_, c - v * b_, c + u * a_, c + v * b_], [(0, 1, 2, 3)])


def curtain(name, x0, x1, y, z1, pleat=0.3, amp=0.09, face=-1):
    """A pleated curtain along x at depth y, from just above the floor to z1: irregular folds (two frequencies plus
    a per-fold depth), the hem breaking a little outward on the floor, UVs in metres for the fabric texture."""
    rng_c = random.Random(name)
    folds = [rng_c.uniform(0.6, 1.3) for _ in range(256)]
    xs = [x0 + i * 0.025 for i in range(int((x1 - x0) / 0.025) + 1)]
    zs = [0.0, 0.04, 0.12, 0.5, 1.2, 2.0, z1]
    def depth(x, z):
        k = (x - x0) / pleat
        d = amp * math.sin(2 * math.pi * k) * folds[int(k) % 256] + 0.3 * amp * math.sin(2 * math.pi * k * 0.23 + 1.7)
        return d * (1 + 0.5 * max(0.0, 0.12 - z) / 0.12) + (0.03 if z < 0.05 else 0.0)
    verts, uvs = [], []
    run, prev = 0.0, None
    for x in xs:
        p = (x, y + face * (amp * 1.6 + depth(x, 1.0)))
        run += 0 if prev is None else math.dist(p, prev)
        prev = p
        for z in zs:
            verts.append((x, y + face * (amp * 1.6 + depth(x, z)), z))
            uvs.append((run, z))
    n = len(zs)
    faces = [(i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1) for i in range(len(xs) - 1) for j in range(n - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(M["curtain"])
    scene.collection.objects.link(ob)


curtain("curtain-north", hall["x"] + 0.2, hall["x"] + hall["w"] - 6.9, NORTH, HALL_CEIL + 0.05)
# divider curtains drawn back against the columns away from the middle aisle
for i, o in enumerate(venue["obstacles"]):
    b = o["bounds"]
    cxo, cyo = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    if o["floor"] == 0 and o["height"] >= 3 and b["w"] < 1.2 and b["h"] < 1.2 and inside(hall, cxo, cyo) and abs(cxo - SX) > 4:
        side = 1 if cxo < SX else -1
        x0 = b["x"] + b["w"] + 0.02 if side > 0 else b["x"] - 0.5
        curtain(f"curtain-col-{i}", x0, x0 + 0.48, cyo, HALL_CEIL, pleat=0.12, amp=0.07)

# the programme screen: 16:10 like a laptop panel, thin bezel with a deeper chin, in front of the curtains
SCREEN = {"x": SX, "y": NORTH - 0.32, "z": 1.7, "w": 3.6, "h": 2.25}
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
scene.world = world
# a little haze in the auditoriums only (the stage spots throw visible beams there, as in the photos);
# the Hollywood room and the corridors are clear
haze = bpy.data.materials.new("haze")
haze.use_nodes = True
hnt = haze.node_tree
hnt.nodes.remove(hnt.nodes["Principled BSDF"])
vol = hnt.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = 0.012
vol.inputs["Anisotropy"].default_value = 0.55
hnt.links.new(vol.outputs["Volume"], hnt.nodes["Material Output"].inputs["Volume"])
hz = Batch()
for r in auditoriums:
    hz.box("haze", {k: r["bounds"][k] + d for k, d in (("x", 0.35), ("y", 0.2), ("w", -0.7), ("h", -0.4))},
           FH - r.get("rake", 0) - 0.4, FH + CLEAR - 0.05)
M["haze"] = haze
hz.finish()


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
# the Hollywood room: an area light under each hexagon panel, a narrow spot in each downlight (they throw the
# pools of light on the carpet), warm track spots at the entrance end
for (lx, ly, lz) in lights:
    ob = area(f"panel-{lx:.1f}-{ly:.1f}", (lx, ly, lz - 0.06), 0.3, 55, (1.0, 0.94, 0.86))
    ob.data.shape, ob.data.size, ob.data.size_y = "RECTANGLE", 0.8, 0.3
for (lx, ly) in downlights:
    spot = bpy.data.lights.new(f"down-{lx:.1f}-{ly:.1f}", "SPOT")
    spot.energy, spot.spot_size, spot.spot_blend, spot.color = 45, math.radians(38), 0.35, (1.0, 0.9, 0.78)
    spot.shadow_soft_size = 0.04
    so = bpy.data.objects.new(spot.name, spot)
    so.location = (lx, ly, HALL_CEIL - 0.01)
    scene.collection.objects.link(so)
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
scene.render.resolution_x, scene.render.resolution_y = (960, 540) if (args.preview or args.lookdev) else (1920, 1080)
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
scene.view_settings.exposure = -0.9
try:
    scene.view_settings.look = "Medium High Contrast"
except TypeError as e:
    print("look:", e)


def phone_post():
    """Post like a phone photo: soft bloom around the lights, a hint of colour fringing towards the corners and
    a little vignetting. No lens distortion, so the overlay corners in shots.json stay exact."""
    ng = bpy.data.node_groups.new("post", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl, out = ng.nodes.new("CompositorNodeRLayers"), ng.nodes.new("NodeGroupOutput")
    glare = ng.nodes.new("CompositorNodeGlare")
    for k, v in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", 1.2), ("Strength", 0.35), ("Size", 0.6)):
        try:
            glare.inputs[k].default_value = v
        except (KeyError, TypeError, ValueError) as e:
            print(f"post: glare {k}: {e}")
    lens = ng.nodes.new("CompositorNodeLensdist")
    lens.inputs["Distortion"].default_value, lens.inputs["Dispersion"].default_value = 0.0, 0.004
    mask = ng.nodes.new("CompositorNodeEllipseMask")
    mask.inputs["Size"].default_value = (1.15, 1.15)
    blur = ng.nodes.new("CompositorNodeBlur")
    blur.inputs["Size"].default_value = (250, 250)
    vig = ng.nodes.new("ShaderNodeMix")
    vig.data_type, vig.blend_type = "RGBA", "MULTIPLY"
    vig.inputs["Factor"].default_value = 0.3
    a, b = [i for i in vig.inputs if i.type == "RGBA"][:2]
    links = ng.links
    links.new(rl.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], lens.inputs["Image"])
    links.new(mask.outputs["Mask"], blur.inputs["Image"])
    links.new(lens.outputs["Image"], a)
    links.new(blur.outputs["Image"], b)
    links.new(next(o for o in vig.outputs if o.type == "RGBA"), out.inputs["Image"])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True


if not args.preview:
    phone_post()
scene.render.image_settings.file_format = "PNG"

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=args.save)

REF_CAMS = json.loads((ROOT / "data" / "references" / "cameras.json").read_text())


def render_reference(name):
    """Render from a camera placed where a reference photo was taken, for side-by-side calibration."""
    rc = REF_CAMS[name]
    data = bpy.data.cameras.new(f"cam-ref-{name}")
    ob = bpy.data.objects.new(f"cam-ref-{name}", data)
    scene.collection.objects.link(ob)
    ob.location, ob.rotation_euler = rc["loc"], aim(rc["loc"], rc["look"])
    data.sensor_fit, data.angle_x = "HORIZONTAL", math.radians(rc["fov_h"])
    hidden = [o for o in scene.objects if o.name in rc.get("hide", [])]
    for o in hidden:
        o.hide_render = True
    scene.camera = ob
    scene.render.filepath = str(OUT / f"ref-{name}.png")
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    scene.camera = cam


for what in [w for w in args.render.split(",") if w]:
    if what.startswith("ref:"):
        render_reference(what[4:])
    elif what == "hall":
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
