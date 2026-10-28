"""The laptop on your lap in the cinema seat (site/, laptops and desktops): a Dell Precision 5570, rendered alone
on a transparent background from the eyes of whoever sits there, so the page can lay it over the room like a
first-person game draws the hands, and place it for each window size without ever covering the recording.

Run with Blender's Python (Windows Blender, driven from WSL, like build_scene.py):
  blender.exe -b --python scripts/blender/build_laptop.py -- --root C:/path/to/repo --out C:/renders/laptop \
      [--samples 256] [--frames 14] [--only open,closed,anim] [--preview]

One camera for every lid angle: it looks square on at the open display (so the HTML pinned onto it stays a plain
2D rectangle, sharp), from about half a metre, down about 25 degrees, and its frame is the union of everything the lid
sweeps through between closed and open, down to the front edge of the base. So every picture is the same size and
lines up: the page only moves it up or down.
Writes laptop-open.png, laptop-closed.png, anim/f_00.png... (closed to open) and laptop.json:
  w, h            the frame, px
  screen          the open display's corners in px (tl, tr, bl, br)
  open_top        the top of the open lid, px; open_cut: where the view's bottom edge cuts it when open
  closed_top      the top of the closed lid (its far edge), px; closed_bottom: the front edge of the base
  frames, angles  the opening animation

Dimensions and materials from data/laptop/REFERENCE.md (Dell's manual and review photos). Metres, +x right, +y away
from you, +z up; the base's rear edge (the hinge) on y = 0.
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

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--anim-samples", type=int, default=64)
ap.add_argument("--frames", type=int, default=14)
ap.add_argument("--width", type=int, default=2000)
ap.add_argument("--anim-width", type=int, default=900)
ap.add_argument("--only", default="open,closed,anim")
ap.add_argument("--preview", action="store_true", help="EEVEE, quick look")
ap.add_argument("--save")
ap.add_argument("--cpu", action="store_true", help="Cycles on the CPU (look-dev while the GPU renders something else)")
args = ap.parse_args(argv)
ROOT, OUT = Path(args.root), Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

# ------------------------------------------------------------------------------------------- dimensions
W, D = 0.3444, 0.2301          # footprint
TB, TL = 0.0135, 0.0048        # base and lid thickness (18.3 mm closed)
R = 0.0055                     # plan corner radius
DISP_W, DISP_H = 0.33638, 0.21024
BEZ_TOP = 0.0058               # camera bezel; the sides are (W - DISP_W) / 2 ~ 4 mm
OPEN = 115.0                   # lid angle when open: its display faces your eyes, looking down ~25 degrees
PIVOT = Vector((0, -0.0045, TB))


def srgb(h, a=1.0):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin((h >> 16) & 255), lin((h >> 8) & 255), lin(h & 255), a)


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def principled(name, color, rough, metal=0.0, coat=0.0, coat_rough=0.05, aniso=0.0, emission=None, strength=0.0, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    b.inputs["Anisotropic"].default_value = aniso
    b.inputs["Sheen Weight"].default_value = sheen
    if emission is not None:
        b.inputs["Emission Color"].default_value = srgb(emission)
        b.inputs["Emission Strength"].default_value = strength
    return m


def bump(m, tex, strength, distance=0.0002):
    nt = m.node_tree
    bp = node(nt, "ShaderNodeBump", Strength=strength, Distance=distance)
    nt.links.new(tex, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])


def obj_coords(nt, scale):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"]


# "Titan Gray" anodised aluminium: satin, a faint grain; the diamond-cut chamfers bright
M = {}
M["alu"] = principled("alu", 0x55565A, 0.32, metal=1.0, aniso=0.4)    # Titan Gray in a dark room: it shows what's in front
nt = M["alu"].node_tree
noise = node(nt, "ShaderNodeTexNoise", Scale=9000.0, Detail=2.0)
nt.links.new(obj_coords(nt, 1.0), noise.inputs["Vector"])
bump(M["alu"], noise.outputs["Fac"], 0.04)
M["chamfer"] = principled("chamfer", 0xD2D2D2, 0.12, metal=1.0)
M["hinge"] = principled("hinge", 0x3A3B3E, 0.4, metal=1.0)
# the deck: black woven carbon fibre under a soft-touch coat, a 2 mm weave you only see in the sheen
M["carbon"] = principled("carbon", 0x2E2E30, 0.6, sheen=0.08)
nt = M["carbon"].node_tree
chk = node(nt, "ShaderNodeTexChecker", Scale=1.0)
chk.inputs["Color1"].default_value = srgb(0x232325)
chk.inputs["Color2"].default_value = srgb(0x343437)
nt.links.new(obj_coords(nt, 1000.0), chk.inputs["Vector"])
nt.links.new(chk.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
wave = node(nt, "ShaderNodeTexWave", Scale=1.0, Distortion=0.0)
nt.links.new(obj_coords(nt, 1000.0), wave.inputs["Vector"])
bump(M["carbon"], wave.outputs["Fac"], 0.3)
# speaker grilles: the deck perforated in a fine grid of holes
M["grille"] = principled("grille", 0x232325, 0.6)
nt = M["grille"].node_tree
vor = node(nt, "ShaderNodeTexVoronoi", Scale=1.0)
nt.links.new(obj_coords(nt, 800.0), vor.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.32, 0.36
ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = srgb(0x050505), srgb(0x2A2A2C)
nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
bump(M["grille"], ramp.outputs["Color"], 0.3)
M["key"] = principled("key", 0x121214, 0.5)
M["legend"] = principled("legend", 0xDADADF, 0.6, emission=0xE8ECFF, strength=0.0)   # backlit at night
M["pad"] = principled("pad", 0x202022, 0.3, coat=0.3, coat_rough=0.15)
M["bezel"] = principled("bezel", 0x0A0A0C, 0.3, coat=0.8, coat_rough=0.05)
M["display"] = principled("display", 0x000000, 0.5, emission=0x1A2140, strength=0.0)   # pure black under the notes (the page adds the glass)
M["camera"] = principled("camera", 0x0A0A12, 0.05, coat=1.0)
M["logo"] = principled("logo", 0xF2F2F4, 0.05, metal=1.0)          # mirror-polished: it catches the screen
M["led"] = principled("led", 0xFFFFFF, 0.3, emission=0xFFFFFF, strength=0.0)


# ------------------------------------------------------------------------------------------- geometry helpers
def rounded_outline(w, d, r, y0, segs=8):
    """A rounded rectangle, x centred, y from y0 - d to y0, counter-clockwise from above."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, y0 - d + r, -90), (w / 2 - r, y0 - r, 0), (-w / 2 + r, y0 - r, 90), (-w / 2 + r, y0 - d + r, 180)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(name, outline, z0, z1, mats, chamfer=0.0007, parent=None):
    """An extruded outline with chamfered rims; mats: (top, bottom, side, chamfer)."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z0)) for x, y in outline]
    bottom = bm.faces.new(vs[::-1])
    top_edges = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    up = [g for g in top_edges["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=up)
    bm.normal_update()
    rims = [e for e in bm.edges if len(e.link_faces) == 2 and abs(e.link_faces[0].normal.dot(e.link_faces[1].normal)) < 0.5]
    if chamfer:
        bmesh.ops.bevel(bm, geom=rims, offset=chamfer, segments=2, profile=0.5, affect="EDGES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)                  # outward, whichever way the outline ran
    bm.normal_update()
    for f in bm.faces:
        nz = f.normal.z
        f.material_index = 0 if nz > 0.97 else 1 if nz < -0.97 else 2 if abs(nz) < 0.2 else 3
        f.smooth = abs(nz) < 0.97
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def plate(name, x0, x1, y0, y1, z, mat, parent=None, r=0.0, thick=0.0002):
    out = rounded_outline(x1 - x0, y1 - y0, r, y1, segs=4) if r else [(x0 - (x0 + x1) / 2, y0), (x1 - (x0 + x1) / 2, y0), (x1 - (x0 + x1) / 2, y1), (x0 - (x0 + x1) / 2, y1)]
    ob = slab(name, [(x + (x0 + x1) / 2, y) for x, y in out], z, z + thick, [mat, mat, mat, mat], chamfer=0, parent=parent)
    return ob


# ------------------------------------------------------------------------------------------- the base
base = slab("base", rounded_outline(W, D, R, 0.0), 0.0, TB, [M["carbon"], M["alu"], M["alu"], M["chamfer"]])
# keyboard: 19.05 x 18.05 mm pitch, a half-height function row, block ~265 mm wide, 22 mm from the hinge
U, V = 0.01905, 0.01805
ROWS = [
    [("esc", 1.0)] + [(f"F{i}", 1.0) for i in range(1, 13)] + [("", 1.0)],                       # half height; last: power
    [("`", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("backspace", 1.0)],
    [("tab", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1), ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 0.5)],
    [("caps", 1.75), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1), ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("enter", 1.25)],
    [("shift", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1), ("M", 1), (",", 1), (".", 1), ("/", 1), ("shift", 1.75)],
    [("ctrl", 1), ("fn", 1), ("", 1), ("alt", 1), ("", 5.0), ("alt", 1), ("ctrl", 1), ("<", 1), ("^", 1), (">", 1)],
]
KB_W = 0.265
kb_top = -0.020                                                   # the function row's top edge, y
key_me = None
legend_specs = []
bm = bmesh.new()
y = kb_top
for r_i, row in enumerate(ROWS):
    units = sum(wu for _, wu in row)
    s = KB_W / (units * U)                                        # each row stretched to the block's width
    h = (V * 0.5 if r_i == 0 else V)
    x = -KB_W / 2
    for label, wu in row:
        kw = wu * U * s
        gap = 0.0032
        cx, cy = x + kw / 2, y - h / 2
        if r_i == 5 and label in ("^",):                          # up/down share a key's height
            for dy, lab in ((h / 4, "^"), (-h / 4, "v")):
                ret = bmesh.ops.create_cube(bm, size=1.0)
                bmesh.ops.scale(bm, vec=(kw - gap, h / 2 - gap * 0.6, 0.0011), verts=ret["verts"])
                bmesh.ops.translate(bm, vec=(cx, cy + dy, TB + 0.0006), verts=ret["verts"])
                legend_specs.append((lab, cx, cy + dy, 0.0024))
        else:
            ret = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(kw - gap, h - gap, 0.0011), verts=ret["verts"])
            bmesh.ops.translate(bm, vec=(cx, cy, TB + 0.0006), verts=ret["verts"])
            if label:
                small = len(label) > 1
                legend_specs.append((label, cx - (kw / 2 - 0.0035 if small and r_i else 0), cy - (0 if r_i == 0 or not small else h / 4), 0.0022 if small else 0.0034))
        x += kw
    y -= h
kb_bottom = y
bm.normal_update()
bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.0004, segments=2, profile=0.5, affect="EDGES")
key_me = bpy.data.meshes.new("keys")
bm.to_mesh(key_me)
bm.free()
key_me.materials.append(M["key"])
for p in key_me.polygons:
    p.use_smooth = True
keys = bpy.data.objects.new("keys", key_me)
scene.collection.objects.link(keys)
for label, lx, ly, size in legend_specs:
    cu = bpy.data.curves.new(f"legend-{label}", "FONT")
    cu.body = {"<": "\u2190", ">": "\u2192", "^": "\u2191", "v": "\u2193"}.get(label, label)
    cu.size = size
    cu.align_x, cu.align_y = ("LEFT" if len(label) > 1 else "CENTER"), "CENTER"
    ob = bpy.data.objects.new(f"legend-{label}", cu)
    ob.location = (lx, ly, TB + 0.0006 + 0.00056)
    ob.data.materials.append(M["legend"])
    scene.collection.objects.link(ob)
# the power button (blank, top right) carries the fingerprint reader: a faint ring
# touchpad and grilles
pad_y1 = kb_bottom - 0.010
plate("touchpad", -0.15090 / 2, 0.15090 / 2, pad_y1 - 0.090, pad_y1, TB, M["pad"], r=0.004)
for sx in (-1, 1):
    gx = sx * (KB_W / 2 + 0.0045 + 0.0055)
    plate(f"grille-{sx}", gx - 0.0055, gx + 0.0055, kb_bottom, kb_top, TB, M["grille"], r=0.002, thick=0.00005)
# the battery LED on the front edge
plate("led", -0.003, 0.003, -D - 0.00005, -D + 0.0001, TB * 0.45, M["led"], thick=0.0008)
hinge = bpy.data.objects.new("hinge", bpy.data.meshes.new("hinge"))
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0042, radius2=0.0042, depth=0.29)
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
bmesh.ops.translate(bm, vec=(0, PIVOT.y + 0.0004, TB + 0.0003), verts=bm.verts)
bm.to_mesh(hinge.data)
bm.free()
hinge.data.materials.append(M["hinge"])
for p in hinge.data.polygons:
    p.use_smooth = True
scene.collection.objects.link(hinge)

# ------------------------------------------------------------------------------------------- the lid
pivot = bpy.data.objects.new("lid-pivot", None)
scene.collection.objects.link(pivot)
pivot.location = PIVOT
z0 = TB + 0.0004                                                  # closed: a hair above the keys' tops
outline = [(x, y - PIVOT.y) for x, y in rounded_outline(W, D, R, 0.0)]
# the lid in the pivot's frame, closed: its outer face (+z) up, its display face (-z) down onto the keys
lid = slab("lid", outline, z0 - PIVOT.z, z0 - PIVOT.z + TL, [M["alu"], M["bezel"], M["alu"], M["chamfer"]], parent=pivot)
front_y = -D - PIVOT.y                                            # the lid's free edge (its top, when open)
disp_y0 = front_y + BEZ_TOP
plate("display", -DISP_W / 2, DISP_W / 2, disp_y0, disp_y0 + DISP_H, z0 - PIVOT.z - 0.00005, M["display"], parent=pivot, thick=0.00004)
cam_dot = plate("webcam", -0.0012, 0.0012, front_y + 0.0018, front_y + 0.0042, z0 - PIVOT.z - 0.00006, M["camera"], parent=pivot, r=0.0011, thick=0.00003)
for d in (-1, 1):
    plate(f"ir-{d}", d * 0.006 - 0.0006, d * 0.006 + 0.0006, front_y + 0.0024, front_y + 0.0036, z0 - PIVOT.z - 0.00006, M["camera"], parent=pivot, r=0.0005, thick=0.00003)
for ob in [o for o in scene.objects if o.name.startswith(("display", "webcam", "ir-"))]:
    for f in ob.data.polygons:                                    # these face down (the display side)
        f.flip()
top_z = z0 - PIVOT.z + TL


# the Dell logo, centred, upright for people behind you when it's open (so upside down to you when it's closed)
def logo():
    ring = bpy.data.objects.new("logo-ring", bpy.data.meshes.new("logo-ring"))
    bm = bmesh.new()
    rr, rw, segs = 0.0150, 0.0011, 96
    outer = [bm.verts.new((rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs), 0)) for i in range(segs)]
    inner = [bm.verts.new(((rr - rw) * math.cos(2 * math.pi * i / segs), (rr - rw) * math.sin(2 * math.pi * i / segs), 0)) for i in range(segs)]
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
    bm.to_mesh(ring.data)
    bm.free()
    ring.data.materials.append(M["logo"])
    cy = front_y + D / 2
    ring.location = (0, cy, top_z + 0.00005)
    ring.parent = pivot
    scene.collection.objects.link(ring)
    cu = bpy.data.curves.new("logo-text", "FONT")
    cu.body = "DELL"
    cu.size = 0.0098
    cu.space_character = 0.85
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    if font.exists():
        cu.font = bpy.data.fonts.load(str(font))
    tx = bpy.data.objects.new("logo-text", cu)
    tx.data.materials.append(M["logo"])
    # its up is the lid's free edge (-y when closed): turned half round
    tx.location = (0, cy, top_z + 0.00003)
    tx.rotation_euler = (0, 0, math.pi)
    tx.parent = pivot
    scene.collection.objects.link(tx)


logo()


# the sticker: die-cut vinyl with a gloss laminate, ~0.15 mm proud, on the lower right of the lid as you see it closed,
# readable to you; its edge catches the light and throws a hairline shadow
def sticker():
    tex = ROOT / "data" / "laptop" / "sticker.png"
    hgt = ROOT / "data" / "laptop" / "sticker-height.png"
    img = bpy.data.images.load(str(tex))
    h_img = bpy.data.images.load(str(hgt))
    h_img.colorspace_settings.name = "Non-Color"
    sh = 0.074
    sw = sh * img.size[0] / img.size[1]
    me = bpy.data.meshes.new("sticker")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=(sw, sh, 1), verts=bm.verts)
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / sw + 0.5, lp.vert.co.y / sh + 0.5)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("sticker")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Cubic"
    th = nt.nodes.new("ShaderNodeTexImage")
    th.image = h_img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Coat Weight"].default_value = 1.0                    # the gloss laminate, glossier than the lid
    b.inputs["Coat Roughness"].default_value = 0.05
    bump(m, th.outputs["Color"], 0.6, distance=0.00015)
    m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    me.materials.append(m)
    ob = bpy.data.objects.new("sticker", me)
    ob.parent = pivot
    ob.location = (0.086, front_y + 0.176, top_z + 0.00015)         # near the hinge: in view when you look up at the film too
    ob.rotation_euler = (0, 0, math.radians(-9))                   # up = +y when closed: away from you, so you read it
    scene.collection.objects.link(ob)


sticker()


def set_lid(angle_deg):
    pivot.rotation_euler = (-math.radians(angle_deg), 0, 0)
    bpy.context.view_layer.update()


# ------------------------------------------------------------------------------------------- light: a dark cinema
world = bpy.data.worlds.new("cinema")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = srgb(0x06070C)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12


def area(name, loc, size, power, color, target, shape="RECTANGLE"):
    lt = bpy.data.lights.new(name, "AREA")
    lt.shape = shape
    lt.size, lt.size_y = size
    lt.energy = power
    lt.color = color
    ob = bpy.data.objects.new(name, lt)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)
    return ob


# the projected screen far ahead and up (19 x 7 m, ~15 m away): the key light, and the long reflection on the lid
area("cinema-screen", (0, 15.0, 4.2), (19.0, 7.2), 8000.0, (0.55, 0.58, 0.72), (0, 0, 0))   # the projected light: bluish, not saturated
# house lights: two warm spots high on either side, for glints on the chamfers; a faint fill from the aisle
for sx in (-1, 1):
    sp = bpy.data.lights.new(f"spot-{sx}", "SPOT")
    sp.energy, sp.spot_size, sp.color, sp.shadow_soft_size = 12.0, math.radians(30), (1.0, 0.9, 0.78), 0.15   # house lights: dim, warm
    ob = bpy.data.objects.new(f"spot-{sx}", sp)
    ob.location = (sx * 2.2, 2.5, 3.2)
    ob.rotation_euler = (Vector((0, -0.05, 0)) - ob.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)

# the room's own glow: the screen's light thrown back by the ceiling and the walls, a big soft source overhead and in
# front, which is what a satin metal lid in a dark cinema mostly reflects (without it the lid reads black)
area("ceiling-glow", (0, 7.5, 3.0), (8.0, 3.5), 45.0, (0.55, 0.62, 1.0), (0, 0.4, 0))
area("behind", (0, -3.0, 2.6), (4.0, 2.0), 25.0, (0.6, 0.66, 1.0), (0, 0, 0.3))
# (the lap under it is the page's: a soft darkness round its lower half, site/cinema.css .lap::before; modelled thighs
# read as pillars beyond the lid)
# whoever is sitting there: a dark body just behind the camera, so the glass reflects a shape, not the void
body = slab("you", rounded_outline(0.5, 0.35, 0.15, -0.38), 0.0, 0.75, [principled("you", 0x0B0C10, 0.8)] * 4, chamfer=0)
body.visible_camera = False

# ------------------------------------------------------------------------------------------- the camera
set_lid(OPEN)
disp = bpy.data.objects["display"]
quad_local = [Vector((-DISP_W / 2, disp_y0 + DISP_H, 0)), Vector((DISP_W / 2, disp_y0 + DISP_H, 0)),
              Vector((-DISP_W / 2, disp_y0, 0)), Vector((DISP_W / 2, disp_y0, 0))]
mw = pivot.matrix_world
zd = z0 - PIVOT.z - 0.0001
# closed coords: y grows from the free edge (disp_y0) toward the hinge, so the free edge is the top when open
corners_local = {"tl": Vector((-DISP_W / 2, disp_y0, zd)), "tr": Vector((DISP_W / 2, disp_y0, zd)),
                 "bl": Vector((-DISP_W / 2, disp_y0 + DISP_H, zd)), "br": Vector((DISP_W / 2, disp_y0 + DISP_H, zd))}
corners = {k: mw @ v for k, v in corners_local.items()}
centre = sum(corners.values(), Vector()) / 4
normal = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
EYE = 0.56
cam_data = bpy.data.cameras.new("eye")
cam_data.sensor_fit = "HORIZONTAL"
cam_data.sensor_width = 36.0
cam = bpy.data.objects.new("eye", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = centre + normal * EYE
cam.rotation_euler = (-normal).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()
print("camera pitch (deg below level):", round(math.degrees(math.asin(-(-normal).z)), 1) if False else round(math.degrees(math.asin(normal.z)), 1))

# frame: everything the lid sweeps through, and the base down to its front edge
cm = cam.matrix_world.inverted()


def image_plane(p):
    c = cm @ p
    return (c.x / -c.z, c.y / -c.z)


pts = []
lid_corners = [Vector((x, y, z)) for x in (-W / 2, W / 2) for y in (front_y, -PIVOT.y) for z in (z0 - PIVOT.z, top_z)]
for a in range(0, int(OPEN) + 1, 5):
    set_lid(a)
    pts += [image_plane(pivot.matrix_world @ v) for v in lid_corners]
set_lid(OPEN)
pts += [image_plane(Vector((x, y, z))) for x in (-W / 2, W / 2) for y in (-D, 0.0) for z in (0.0, TB)]
us, vs = [p[0] for p in pts], [p[1] for p in pts]
mx, my = 0.015, 0.012
u0, u1, v0, v1 = min(us) - mx, max(us) + mx, min(vs) - my, max(vs) + my
half = max(abs(u0), abs(u1))                                      # keep the display centred left to right
u0, u1 = -half, half
wt, ht = u1 - u0, v1 - v0
cam_data.lens = 36.0 / wt
big = max(wt, ht)
cam_data.shift_x = 0.0
cam_data.shift_y = (v0 + v1) / 2 / big
WPX = args.width
HPX = round(WPX * ht / wt)
scene.render.resolution_x, scene.render.resolution_y = WPX, HPX
scene.render.resolution_percentage = 100
bpy.context.view_layer.update()


def px(p, w=WPX, h=HPX):
    v = world_to_camera_view(scene, cam, p)
    return [round(v.x * w, 2), round((1 - v.y) * h, 2)]


set_lid(OPEN)
mw = pivot.matrix_world
info = {"w": WPX, "h": HPX, "open_angle": OPEN,
        "screen": [px(mw @ corners_local[k]) for k in ("tl", "tr", "bl", "br")]}
info["open_top"] = min(px(mw @ Vector((x, front_y, z)))[1] for x in (-W / 2, W / 2) for z in (z0 - PIVOT.z, top_z))
hinge_y = px(Vector((0, PIVOT.y, TB)))[1]
disp_h_px = info["screen"][2][1] - info["screen"][0][1]
info["open_cut"] = round(min(HPX, hinge_y + 0.32 * disp_h_px), 1)       # the view's bottom edge, open: a few rows of keys
set_lid(0)
mw = pivot.matrix_world
info["closed_top"] = min(px(mw @ Vector((x, -PIVOT.y, top_z)))[1] for x in (-W / 2, W / 2))
_lid = [px(mw @ Vector((x, y, top_z))) for x in (-W / 2, W / 2) for y in (front_y, -PIVOT.y)]
info["closed_box"] = [min(p[0] for p in _lid), min(p[1] for p in _lid), max(p[0] for p in _lid), max(p[1] for p in _lid)]   # the closed lid
info["closed_bottom"] = round(max(px(Vector((x, -D, 0.0)))[1] for x in (-W / 2, W / 2)) + 6, 1)
# closed, the view's bottom edge cuts the lid like it cuts the base when open: just past the sticker's front edge
_st = bpy.data.objects["sticker"]
_sw, _sh = _st.dimensions.x, _st.dimensions.y
_cs = [px(_st.matrix_world @ Vector((x * _sw / 2 / _st.scale.x, y * _sh / 2 / _st.scale.y, 0))) for x in (-1, 1) for y in (-1, 1)]
info["sticker_box"] = [round(min(p[0] for p in _cs), 1), round(min(p[1] for p in _cs), 1), round(max(p[0] for p in _cs), 1), round(max(p[1] for p in _cs), 1)]
info["closed_cut"] = round(min(info["closed_bottom"], max(p[1] for p in _cs) + 0.06 * (info["closed_bottom"] - info["closed_top"])), 1)
print("laptop frame", WPX, "x", HPX, json.dumps(info))

# ------------------------------------------------------------------------------------------- render
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
    scene.cycles.device = "CPU" if args.cpu else "GPU"
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 8
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "Medium High Contrast"):     # renamed in Blender 5
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        continue
scene.view_settings.exposure = -0.6
# a real lens at half a metre: the far edge of the deck a touch soft
cam_data.dof.use_dof = True
cam_data.dof.focus_distance = EYE
cam_data.dof.aperture_fstop = 5.6

screen_glow = area("screen-glow", centre + normal * 0.004, (DISP_W, DISP_H), 0.0, (0.75, 0.8, 1.0), centre + normal * 0.004 + Vector((0, -0.25, -0.3)))
screen_glow.rotation_euler = (-normal).to_track_quat("Z", "Y").to_euler()                       # emits along the display's normal
screen_glow.data.spread = math.radians(140)

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=args.save)
only = set(args.only.split(","))


def shoot(angle, path, samples, width, spill):
    set_lid(angle)
    M["display"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0
    M["legend"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.6 if spill else 0.0   # backlight on with the screen
    screen_glow.data.energy = spill * 1.6                          # watts: a dark-mode screen's glow on the keys
    if not args.preview:
        scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = width, round(width * HPX / WPX)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


if "open" in only:
    shoot(OPEN, OUT / "laptop-open.png", args.samples, WPX, 0.8)   # the screen's own light on the keys (it's on)
if "closed" in only:
    shoot(0, OUT / "laptop-closed.png", args.samples, WPX, 0.0)
if "anim" in only:
    (OUT / "anim").mkdir(exist_ok=True)
    n = args.frames
    angles = [OPEN * (0.5 - 0.5 * math.cos(math.pi * i / (n - 1))) for i in range(n)]   # eased: it starts and settles slowly
    for i, a in enumerate(angles):
        shoot(a, OUT / "anim" / f"f_{i:02d}.png", args.anim_samples, args.anim_width, 0.0)
    info["frames"], info["angles"] = n, [round(a, 1) for a in angles]
(OUT / "laptop.json").write_text(json.dumps(info, indent=1))
print("done")
