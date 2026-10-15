"""Outside: the Kinepolis facade on its street, matched to the Street View shots kinepolis_outside_1/2/3.

Frames: the geometry is written in a local photo frame (metres at photo scale: the facade's cladding face is the
plane y = 0, the street at y < 0, x along the facade to the right as seen from the street, x = 0 near the west
edge of the first entrance bay, z up from the road) and the whole area is then placed in the venue frame of
data/venue/venue.json (VS, VA, VY, VZ below): the facade on the reception's south wall (y -60.55, facing south),
the forecourt at its plan elevation 1.2. The three Street View cameras were bundle-adjusted together (one shared
focal length) and are stored in venue coordinates.

Layout read off orthophotos of the facade rectified from the photos (scripts/photomatch, build/photomatch/outside):
three entrance bays 5.1 m wide under the sign, a stepped band of curtain-wall glazing above that follows the stair
inside, ground-floor window bands either side, granite-grey cladding panels on a 3.03 m module, the stair and its
grey landing block at the east end. In front: a 5.3 m strip of red concrete pavers, a service lane, the row of grey
bollards on its white edge line, the road with a dashed centre line, a verge with a row of young maples, a footpath
and a car park, and Decathlon across the way.
"""
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import pm_lib as L

EXPOSURE = 0.6
UNIFIED = False         # build(root, unified=True): part of the one venue model (see build)
ROOT = None

# the facade layout was read at a scale 1.3 % smaller than the final camera solve: S puts it right
S = 1.013


def sx(x):
    return -0.26 + (x + 0.26) * S


PARAPET = 13.7 * S      # top of the cladding
GLAZE_TOP = 10.95 * S   # top of the stepped upper glazing
SIGN_BOTTOM = 5.29      # top of the entrance bays = bottom of the sign band
DOOR_TOP = 2.32 * S     # head of the ground-floor doors and windows
FACADE_X = (-60.0, sx(45.4))
BAYS = [(-0.26, 4.95), (5.89, 11.03), (11.96, 17.09)]
# upper glazing: (x0, x1, bottom z), all up to GLAZE_TOP
UPPER = [(-20.0, -6.72, 5.25), (-6.72, -3.69, 6.0), (-3.69, -0.67, 6.7), (-0.67, 2.36, 7.4), (2.36, 5.38, 8.15),
         (5.38, 8.40, 8.15), (8.40, 11.43, 8.15), (11.43, 14.46, 8.15), (14.46, 17.48, 7.45), (17.48, 20.5, 6.6),
         (20.5, 23.53, 5.9), (23.53, 26.1, 5.2), (26.1, 29.1, 4.4), (29.1, 32.1, 3.6), (32.1, 35.0, 2.9),
         (35.0, 37.9, 2.9), (37.9, 40.8, 2.9), (40.8, 42.6, 4.6)]
# ground-floor window bands (x0, x1), z 0 .. DOOR_TOP
GROUND = [(-9.9, -7.0), (-6.25, -1.0), (17.7, 22.9), (23.6, 28.9), (29.8, 32.2), (-20.0, -10.6)]
STAIR_DOOR = (40.8, 43.0, 1.75, 4.6)
TRANSOMS = [9.65, 8.15, 7.4, 6.65, 5.9, 5.2, 4.4, 3.6]
# Into the venue frame (data/venue/venue.json, the frame build_scene.py uses): the photo frame scaled by VS and
# moved so the entrance's west edge meets the grand stair's west edge (x -2.4: the three entrance bays face the grand
# stair) and the facade's east end the back-of-house east wall (x 42.25); the facade's face on the reception's
# south wall (outer face y -60.55); the forecourt at its plan elevation 1.2.
# The plan's back-of-house wall east of x 22.7 stands 0.4 m further south; the photos show a flush facade there, so
# the model follows the photos (JOG = 0 keeps the step switchable).
VS, VA, VY, VZ = 0.9654, -2.149, -60.55, 1.2
XJ, JOG = (22.7 - VA) / VS, 0.0         # the plan's 0.4 m step east of x 22.7 isn't in the photos: flush
UPPER = [(sx(a), sx(b), z * S) for a, b, z in UPPER]
GROUND = [(sx(a), sx(b)) for a, b in GROUND]


def split_at_jog(spans):
    out = []
    for sp in spans:
        if sp[0] < XJ < sp[1]:
            out += [(sp[0], XJ) + tuple(sp[2:]), (XJ, sp[1]) + tuple(sp[2:])]
        else:
            out.append(sp)
    return out


UPPER = split_at_jog(UPPER)
GROUND = split_at_jog(GROUND)
STAIR_DOOR = (sx(STAIR_DOOR[0]), sx(STAIR_DOOR[1]), STAIR_DOOR[2] * S, STAIR_DOOR[3] * S)
TRANSOMS = [z * S for z in TRANSOMS]


def mats():
    M = {}
    M["clad"] = granite("clad", 0xcbcac5, 3.025, 0.92, x0=-0.67, z0=DOOR_TOP)
    M["pier"] = L.mat("pier", 0xdedfdc, 0.55)
    M["frame"] = L.mat("frame", 0xf1f1ee, 0.35)
    M["glass_up"] = L.mat("glass_up", 0xb4bec8, 0.02, metal=0.92)
    M["glass_dn"] = L.mat("glass_dn", 0x6b747c, 0.03, metal=0.75)
    M["frosted"] = L.mat("frosted", 0xa9adae, 0.35, metal=0.1)
    M["glass_door"] = L.mat("glass_door", 0x5d666e, 0.03, metal=0.7)
    M["interior"] = L.mat("interior", 0x2b2d2e, 0.9)
    M["blue"] = L.mat("blue", 0x1f43e0, 0.35, coat=0.3)
    M["star"] = L.mat("star", 0xb9b0ab, 0.5)
    M["star_dark"] = L.mat("star_dark", 0x8f8580, 0.6)
    M["pavers"] = pavers()
    M["asphalt"] = asphalt("asphalt", 0x636260)
    M["asphalt_road"] = asphalt("asphalt_road", 0x666563)
    M["line"] = L.mat("line", 0xe9e9e4, 0.6)
    M["gutter"] = L.mat("gutter", 0x6f6865, 0.85)
    M["kerb"] = L.mat("kerb", 0xa9a8a2, 0.8)
    M["grass"] = L.mat("grass", 0x55602f, 0.95, bump=0.3, bump_scale=60)
    M["foot"] = L.mat("foot", 0xb3a69c, 0.85)
    M["bollard"] = L.mat("bollard", 0x6c7075, 0.45, metal=0.3)
    M["bollard_cap"] = L.mat("bollard_cap", 0x9a9fa3, 0.35, metal=0.5)
    M["black"] = L.mat("black", 0x1b1c1e, 0.45)
    M["bin_grey"] = L.mat("bin_grey", 0x8e8f8c, 0.8)
    M["pole"] = L.mat("pole", 0xf0f0ee, 0.35)
    M["banner"] = L.mat("banner", 0xf2f2f2, 0.7)
    M["lamp"] = L.mat("lamp", 0x7a7468, 0.4, metal=0.6)
    M["concrete"] = L.mat("concrete", 0x8c8d8c, 0.85)
    M["stair"] = L.mat("stair", 0x9b9c9b, 0.8)
    M["rail"] = L.mat("rail", 0xd8d8d6, 0.4, metal=0.6)
    M["dec_grey"] = L.mat("dec_grey", 0x9da1a5, 0.7)
    M["dec_dark"] = L.mat("dec_dark", 0x5d6166, 0.7)
    M["dec_win"] = L.mat("dec_win", 0x37414c, 0.1, metal=0.5)
    M["white_sign"] = L.mat("white_sign", 0xf4f4f4, 0.4)
    M["hedge"] = L.mat("hedge", 0x47602c, 0.95, bump=0.5, bump_scale=25)
    M["handle"] = L.mat("handle", 0x8a6a45, 0.5)
    return M


def granite(name, color, bw, rh, x0=0.0, z0=0.0):
    """speckled grey stone panels with dark joints on a bw x rh grid, mapped on the facade plane (x, z)"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.8
    co = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for src, dst, off in (("X", "X", -x0), ("Z", "Y", -z0)):
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.inputs[1].default_value = off
        nt.links.new(sep.outputs[src], add.inputs[0])
        nt.links.new(add.outputs[0], comb.inputs[dst])
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Mortar Smooth"].default_value = 0.2
    brick.inputs["Brick Width"].default_value = bw
    brick.inputs["Row Height"].default_value = rh
    brick.inputs["Color1"].default_value = L.srgb(color)
    brick.inputs["Color2"].default_value = L.srgb(color - 0x050505)
    brick.inputs["Mortar"].default_value = L.srgb(0x7c7b77)
    brick.inputs["Bias"].default_value = 0.0
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    # speckle
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 400.0
    noise.inputs["Detail"].default_value = 2.0
    nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.35, 0.7
    ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = 0.82, 1.08
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
    # weathering: streaks down from the top, patchy
    streak = nt.nodes.new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value = 1.5
    sc = nt.nodes.new("ShaderNodeMapping")
    sc.inputs["Scale"].default_value = (3.0, 1.0, 0.15)
    nt.links.new(co.outputs["Object"], sc.inputs["Vector"])
    nt.links.new(sc.outputs["Vector"], streak.inputs["Vector"])
    sr = nt.nodes.new("ShaderNodeMapRange")
    sr.inputs["To Min"].default_value, sr.inputs["To Max"].default_value = 0.92, 1.04
    nt.links.new(streak.outputs["Fac"], sr.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(brick.outputs["Color"], mul.inputs[6])
    nt.links.new(ramp.outputs[0], mul.inputs[7])
    mul2 = nt.nodes.new("ShaderNodeMix")
    mul2.data_type = "RGBA"
    mul2.blend_type = "MULTIPLY"
    mul2.inputs["Factor"].default_value = 1.0
    nt.links.new(mul.outputs[2], mul2.inputs[6])
    nt.links.new(sr.outputs[0], mul2.inputs[7])
    nt.links.new(mul2.outputs[2], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], inv.inputs[1])
    nt.links.new(inv.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = L.srgb(color)
    L.MATS[name] = m
    return m


def pavers():
    """red-brown concrete pavers 0.2 x 0.1 in a running bond, a shade per paver"""
    m = bpy.data.materials.new("pavers")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    co = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.5
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = 0.2
    brick.inputs["Row Height"].default_value = 0.1
    brick.inputs["Mortar Size"].default_value = 0.004
    brick.inputs["Color1"].default_value = L.srgb(0x8e7a72)
    brick.inputs["Color2"].default_value = L.srgb(0x84716a)
    brick.inputs["Mortar"].default_value = L.srgb(0x76675f)
    brick.inputs["Bias"].default_value = 0.0
    nt.links.new(co.outputs["Object"], brick.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.6
    nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.85, 1.1
    nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(brick.outputs["Color"], mix.inputs[6])
    nt.links.new(mr.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    m.diffuse_color = L.srgb(0xa38279)
    L.MATS["pavers"] = m
    return m


def asphalt(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.9
    co = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.25
    n1.inputs["Detail"].default_value = 4
    nt.links.new(co.outputs["Object"], n1.inputs["Vector"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 300
    nt.links.new(co.outputs["Object"], n2.inputs["Vector"])
    a = nt.nodes.new("ShaderNodeMapRange")
    a.inputs["To Min"].default_value, a.inputs["To Max"].default_value = 0.85, 1.12
    nt.links.new(n1.outputs["Fac"], a.inputs["Value"])
    c = nt.nodes.new("ShaderNodeMapRange")
    c.inputs["To Min"].default_value, c.inputs["To Max"].default_value = 0.8, 1.15
    nt.links.new(n2.outputs["Fac"], c.inputs["Value"])
    mm = nt.nodes.new("ShaderNodeMath")
    mm.operation = "MULTIPLY"
    nt.links.new(a.outputs[0], mm.inputs[0])
    nt.links.new(c.outputs[0], mm.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[6].default_value = L.srgb(color)
    # patches and repairs: blotches of darker and lighter resurfacing
    pn = nt.nodes.new("ShaderNodeTexNoise")
    pn.inputs["Scale"].default_value = 0.12
    pn.inputs["Detail"].default_value = 1.0
    nt.links.new(co.outputs["Object"], pn.inputs["Vector"])
    pr = nt.nodes.new("ShaderNodeMapRange")
    pr.inputs["From Min"].default_value, pr.inputs["From Max"].default_value = 0.56, 0.6
    pr.inputs["To Min"].default_value, pr.inputs["To Max"].default_value = 1.0, 0.8
    nt.links.new(pn.outputs["Fac"], pr.inputs["Value"])
    ln = nt.nodes.new("ShaderNodeTexNoise")
    ln.inputs["Scale"].default_value = 0.07
    ln.inputs["Detail"].default_value = 1.0
    ln.noise_dimensions = "4D"
    ln.inputs["W"].default_value = 3.0
    nt.links.new(co.outputs["Object"], ln.inputs["Vector"])
    lr = nt.nodes.new("ShaderNodeMapRange")
    lr.inputs["From Min"].default_value, lr.inputs["From Max"].default_value = 0.6, 0.63
    lr.inputs["To Min"].default_value, lr.inputs["To Max"].default_value = 1.0, 1.15
    nt.links.new(ln.outputs["Fac"], lr.inputs["Value"])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(mm.outputs[0], m2.inputs[0])
    nt.links.new(pr.outputs[0], m2.inputs[1])
    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(lr.outputs[0], m3.inputs[1])
    nt.links.new(m3.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = L.srgb(color)
    L.MATS[name] = m
    return m


# ---------------------------------------------------------------------------------- facade
def openings():
    ops = [(x0, x1, zb, GLAZE_TOP) for x0, x1, zb in UPPER]
    ops += [(x0, x1, 0.0, SIGN_BOTTOM) for x0, x1 in BAYS]
    ops += [(x0, x1, 0.0, DOOR_TOP) for x0, x1 in GROUND]
    ops.append(STAIR_DOOR)
    return ops


def cladding(M):
    """the facade face at y = 0 as rectangles around the openings (a sweep over the x breakpoints)"""
    ops = openings()
    xs = sorted({FACADE_X[0], FACADE_X[1]} | {v for o in ops for v in o[:2] if FACADE_X[0] < v < FACADE_X[1]})
    verts, faces = [], []
    for xa, xb in zip(xs, xs[1:]):
        xm = (xa + xb) / 2
        holes = sorted((o[2], o[3]) for o in ops if o[0] <= xm <= o[1])
        z = 0.0
        spans = []
        for h0, h1 in holes:
            if h0 > z:
                spans.append((z, h0))
            z = max(z, h1)
        if z < PARAPET:
            spans.append((z, PARAPET))
        for za, zb in spans:
            i = len(verts)
            verts += [(xa, 0, za), (xb, 0, za), (xb, 0, zb), (xa, 0, zb)]
            faces.append((i, i + 1, i + 2, i + 3))
    ob = L.mesh_obj("facade-clad", verts, faces, M["clad"])
    # opening reveals (the cladding is 0.25 m thick round each opening)
    rv, rf = [], []
    d = 0.25
    for x0, x1, z0, z1 in ops:
        for a, b in (((x0, z0), (x0, z1)), ((x1, z1), (x1, z0)), ((x0, z1), (x1, z1)), ((x1, z0), (x0, z0))):
            if a[1] == 0 and b[1] == 0:
                continue
            i = len(rv)
            rv += [(a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], d, b[1]), (a[0], d, a[1])]
            rf.append((i, i + 1, i + 2, i + 3))
    L.mesh_obj("facade-reveals", rv, rf, M["clad"])
    # the building behind: roof, ends, a dark interior box behind the glass
    if not UNIFIED:                                       # a stand-in for the building behind the skin
        L.box("building", FACADE_X[0], 2.6, -0.2, FACADE_X[1], 70, PARAPET - 0.02, M["concrete"])
    L.box("coping", FACADE_X[0], -0.06, PARAPET, XJ, 0.3, PARAPET + 0.08, M["rail"])
    L.box("coping-east", XJ, -0.06, PARAPET, FACADE_X[1] + 0.06, 0.3, PARAPET + 0.08, M["rail"])
    # east end wall continues back as cladding
    L.box("east-end", FACADE_X[1], 0, 0, FACADE_X[1] + 0.05, 1.0 if UNIFIED else 70, PARAPET, M["clad"])
    return ob


def glass_bay(M, x0, x1, z0, z1, mat, cols, rows, depth=0.18, frame=0.07, name="glass"):
    """a glazed opening: pane set back by depth, a frame round it, mullions and transoms"""
    L.quad(f"{name}-pane", [(x0, depth, z0), (x1, depth, z0), (x1, depth, z1), (x0, depth, z1)], mat)
    t = 0.12
    f = M["frame"]
    parts = [L.box(f"{name}-fl", x0, depth - t / 2, z0, x0 + frame, depth + t / 2, z1, f),
             L.box(f"{name}-fr", x1 - frame, depth - t / 2, z0, x1, depth + t / 2, z1, f),
             L.box(f"{name}-fb", x0, depth - t / 2, z0, x1, depth + t / 2, z0 + frame, f),
             L.box(f"{name}-ft", x0, depth - t / 2, z1 - frame, x1, depth + t / 2, z1, f)]
    for c in cols:
        parts.append(L.box(f"{name}-m", c - frame / 2, depth - t / 2, z0, c + frame / 2, depth + t / 2, z1, f))
    for r in rows:
        parts.append(L.box(f"{name}-t", x0, depth - t / 2, r - frame / 2, x1, depth + t / 2, r + frame / 2, f))
    return parts


# The ground floor is a wall of glass doors. The walk comes in through the second pair west of the grand stair:
# leaves 0 and 1 of the ground-floor run GROUND[1] (venue x -8.26 .. -5.69), swung in 90 degrees; every other door
# is shut.
OPEN = {("gw1", 0), ("gw1", 1)}
# The walk crosses the bollard row obliquely at about venue x -13.1: the two bollards either side stand apart to
# leave it a 4.8 m passage (local x of bollards k = -6 and -5; the rest keep the photos' 2.565 m rhythm).
BOLLARD_MOVED = {-6: -14.19, -5: -9.168}


def door_leaf(M, lo, hi, mat, name, handle_x):
    """one glass door leaf between x lo and hi in its own frame (y = 0 at its middle): stiles and rails 8 cm, mid
    rails, a pull handle on each face"""
    glass_bay(M, lo, hi, 0.0, DOOR_TOP, mat, [], [0.78, 1.55], depth=0.0, frame=0.08, name=name)
    for side in (-1, 1):
        L.box(f"{name}-handle", handle_x - 0.02, side * 0.06, 0.55, handle_x + 0.02, side * 0.12, 1.85, M["handle"])


def door_run(M, x0, x1, n, mat, depth, tag):
    """n glass door leaves side by side from x0 to x1, hung in pairs (handles at the meeting stiles); leaves listed
    in OPEN stand open, swung 90 degrees into the building on their outer hinges"""
    leaf = (x1 - x0) / n
    opened = []
    for j in range(n):
        a, b = x0 + j * leaf, x0 + (j + 1) * leaf
        west = j % 2 == 0                                 # the pair's west leaf hinges west, the east leaf east
        hx = b - 0.12 if west and j < n - 1 else a + 0.12
        if (tag, j) not in OPEN:
            before = set(bpy.data.objects)
            door_leaf(M, a, b, mat, f"{tag}-leaf{j}", hx)
            for o in set(bpy.data.objects) - before:
                o.location.y += depth
            continue
        opened.append((a, b))
        hinge = a if west else b
        before = set(bpy.data.objects)
        door_leaf(M, a - hinge, b - hinge, mat, f"{tag}-open{j}", hx - hinge)
        empty = bpy.data.objects.new(f"{tag}-hinge{j}", None)
        bpy.context.scene.collection.objects.link(empty)
        empty.location = (hinge, depth, 0.0)
        empty.rotation_euler = (0, 0, math.pi / 2 if west else -math.pi / 2)   # into the building (+y)
        for o in set(bpy.data.objects) - before - {empty}:
            o.parent = empty
    if opened:
        # fixed jambs and head round the opening, a flush threshold plate (pavers and reception floor both at 1.2)
        a, b = min(o[0] for o in opened), max(o[1] for o in opened)
        for xa, xb in ((a - 0.05, a + 0.01), (b - 0.01, b + 0.05)):
            L.box(f"{tag}-jamb", xa, depth - 0.08, 0.0, xb, depth + 0.08, DOOR_TOP, M["frame"])
        L.box(f"{tag}-head", a - 0.05, depth - 0.08, DOOR_TOP - 0.06, b + 0.05, depth + 0.08, DOOR_TOP, M["frame"])
        L.box(f"{tag}-threshold", a, -0.05, -0.05, b, 0.3, 0.0, M["rail"])
        print(f"OPEN DOORWAY {tag}: venue x {VA + VS * a:.3f} .. {VA + VS * b:.3f}, centre {VA + VS * (a + b) / 2:.3f}")


def facade(M):
    cladding(M)
    # interior: dark rooms behind all glass
    if not UNIFIED:
        L.box("interior-back", FACADE_X[0], 2.5, 0, FACADE_X[1], 2.6, PARAPET, M["interior"])
    # upper stepped glazing
    for i, (x0, x1, zb) in enumerate(UPPER):
        rows = [r for r in TRANSOMS if zb + 0.1 < r < GLAZE_TOP - 0.1]
        glass_bay(M, x0, x1, zb, GLAZE_TOP, M["glass_up"], [], rows, name=f"up{i}")
    # entrance bays: doors below DOOR_TOP, curtain wall above, piers between
    for i, (x0, x1) in enumerate(BAYS):
        xm = (x0 + x1) / 2
        glass_bay(M, x0, x1, DOOR_TOP, SIGN_BOTTOM, M["glass_dn"], [xm], [3.3, 4.27], depth=0.12, name=f"bay{i}")
        door_run(M, x0, x1, 4, M["glass_door"], 0.12, f"bay{i}")
    for xa, xb in ((BAYS[0][1], BAYS[1][0]), (BAYS[1][1], BAYS[2][0])):
        L.box("pier", xa, -0.04, 0, xb, 0.25, SIGN_BOTTOM, M["pier"])
    # the ground floor either side: glass doors too, about 1.25 m leaves in pairs (frosted west of the entrance)
    for i, (x0, x1) in enumerate(GROUND):
        n = max(1, round((x1 - x0) / 1.25))
        g = M["frosted"] if x1 < 0 else M["glass_door"]
        door_run(M, x0, x1, n, g, 0.1, f"gw{i}")
    # white plinth piers between the ground-floor openings
    for xa, xb in ((-10.6, -9.9), (-7.0, -6.25), (-1.0, -0.26), (16.87, 17.7), (22.9, 23.6), (28.9, 29.8)):
        L.box("plinth", xa, -0.03, 0, xb, 0.25, DOOR_TOP, M["pier"])
    x0, x1, z0, z1 = STAIR_DOOR
    glass_bay(M, x0, x1, z0, z1, M["glass_door"], [(x0 + x1) / 2], [z0 + 0.8, z0 + 1.6, z0 + 2.3], depth=0.1,
              name="stairdoor")
    # vent grille
    g = L.cylinder("vent", -2.25, 0.0, 0, 0.05, 0.3, M["frame"], segs=32)
    g.rotation_euler = (math.pi / 2, 0, 0)
    g.location = (0, 0, 4.6)
    # wall floodlights below the parapet
    for x in (0.9, 15.4, 35.5):
        L.box("lamp-arm", x - 0.04, -0.6, 13.2, x + 0.04, 0.0, 13.28, M["lamp"])
        L.box("lamp-head", x - 0.22, -0.75, 13.05, x + 0.22, -0.45, 13.35, M["lamp"])
    sign(M)


def sign(M):
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    for body, xa, xb, h in (("KINEPOLIS", -0.25, 6.38, 0.95), ("EVENT", 7.13, 11.25, 0.83), ("CENTER", 11.75, 16.75, 0.83)):
        t = L.text(f"sign-{body}", body, 1.0, (0, -0.08, 0), (math.pi / 2, 0, 0), M["blue"], extrude=0.07,
                   font=font, align="LEFT")
        t.data.shear = 0.12
        bpy.context.view_layer.update()
        dx, dy = t.dimensions.x, t.dimensions.y
        t.scale = ((xb - xa) / dx, h / dy, 1.0)
        t.location = (xa, -0.08, 5.52)
    # the star: five points, extruded, one point up, a little proud of the wall
    R, r = 1.27, 0.52
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5 - math.radians(6)
        rad = R if k % 2 == 0 else r
        pts.append((0.75 + rad * math.cos(a), 7.55 + rad * math.sin(a)))
    verts = [(x, -0.12, z) for x, z in pts] + [(x, -0.4, z) for x, z in pts]
    n = len(pts)
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    s = L.mesh_obj("star", verts, faces, M["star"])
    mod = s.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = 0.03, 2


# ---------------------------------------------------------------------------------- street
def ground(M):
    L.box("pavers", -70, -5.3, -0.05, 60, 0, 0.0, M["pavers"])
    L.box("gutter", -70, -5.6, -0.05, 60, -5.3, 0.002, M["gutter"])
    L.box("lane", -70, -11.6, -0.06, 60, -5.6, 0.0, M["asphalt"])
    L.box("edge-line", -70, -11.95, 0.0, 60, -11.72, 0.004, M["line"])
    # the far side of the road runs off at a slight angle (it closes on the facade by 4 cm a metre eastward)
    skew("road", -70, 140, -11.72, KERB0, -0.06, 0.0, M["asphalt_road"], fixed_a=True)
    for k in range(-25, 50):
        x = 0.45 + 2.9 * k
        skew("dash", x - 0.5, x + 0.5, DASH0 + 0.075, DASH0 - 0.075, 0, 0.004, M["line"])
    # the box cross on the road near camera 1
    for a in (1, -1):
        L.extrude_section("cross", [(-0.1, 0), (0.1, 0), (0.1, 0.004), (-0.1, 0.004)],
                          (-0.84, -16.18 - a * 1.0, 0.0), (1.16, -16.18 + a * 1.0, 0.0), M["line"])
    skew("kerb", -70, 140, KERB0, KERB0 - 0.15, 0, 0.12, M["kerb"])
    skew("verge", -70, 140, KERB0 - 0.15, KERB0 - 3.0, -0.05, 0.08, M["grass"])
    skew("footpath", -70, 140, KERB0 - 3.0, KERB0 - 5.2, -0.05, 0.07, M["foot"])
    skew("park-verge", -70, 140, KERB0 - 5.2, KERB0 - 7.0, -0.05, 0.08, M["grass"])
    skew("parking", -70, 140, KERB0 - 7.0, KERB0 - 60, -0.06, 0.0, M["asphalt"])
    for k in range(-20, 40):
        x = 3.0 + 2.5 * k
        skew("stall", x - 0.06, x + 0.06, KERB0 - 7.5, KERB0 - 12.0, 0, 0.004, M["line"])
    skew("hedge", -40, 60, KERB0 - 6.9, KERB0 - 7.7, 0, 1.0, M["hedge"])
    for x0, x1, y0, y1, h in ((60, 98, -12, -10, 0.8), (70, 95, -8.5, -7.5, 0.7)):
        L.box("hedge", x0, y0, 0, x1, y1, h, M["hedge"], bevel=0.15)
    L.box("east-pavers", 45.4, -5.3, -0.05, 60, 30, 0.0, M["pavers"])
    L.box("far-road", 60, -19.5, -0.06, 140, 30, 0.0, M["asphalt_road"])


KERB0, DASH0, SKEW = -22.85, -16.82, 0.04       # far-side kerb and centre line at x = 0, and how they run


def skew(name, x0, x1, ya, yb, z0, z1, mat, fixed_a=False):
    """a box between x0 and x1 whose y edges ya/yb (given at x = 0) drift by SKEW per metre of x"""
    def y(v, x, fixed):
        return v if fixed else v + SKEW * x
    pts = [(x0, y(ya, x0, fixed_a)), (x1, y(ya, x1, fixed_a)), (x1, y(yb, x1, False)), (x0, y(yb, x0, False))]
    if pts[0][1] < pts[3][1]:
        pts = pts[::-1]
    return L.prism(name, pts[::-1] if L_area(pts) < 0 else pts, z0, z1, mat)


def L_area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))


def street_furniture(M):
    # grey anti-ram bollards along the lane's edge line, 1.2 m, every 2.5 m
    proto = None
    for k in range(-8, 27):
        x = BOLLARD_MOVED.get(k, 2.45 + 2.565 * k)
        L.cylinder(f"bollard{k}", x, -11.4, 0, 1.15, 0.105, M["bollard"], segs=20)
        L.cylinder(f"bollard-cap{k}", x, -11.4, 1.15, 1.2, 0.105, M["bollard_cap"], segs=20, r_top=0.085)
    # banner poles: white masts with an arm, two spots and a banner
    for name, x, y in (("poleL", -0.57, -4.08), ("poleR", 16.95, -4.3)):
        L.cylinder(f"{name}", x, y, 0, 8.33, 0.085, M["pole"], segs=20)
        L.box(f"{name}-plate", x - 0.3, y - 0.3, 0, x + 0.3, y + 0.3, 0.04, M["pole"])
        banner(M, name, x, y)
    # black bins at the piers, a grey concrete bin, small cast-iron bollards by the wall
    # (photo 3 has the concrete bin at x -2.2 and a black bin at -1.0, in front of the walk's open doorway: both moved
    # east onto the white plinth by the entrance so the approach stays clear)
    for x in (-0.25, 5.3, 11.36):
        L.box("bin", x - 0.2, -0.75, 0, x + 0.2, -0.38, 0.95, M["black"], bevel=0.04)
        L.box("bin-top", x - 0.21, -0.76, 0.95, x + 0.21, -0.37, 1.0, M["black"], bevel=0.02)
    L.box("bin-concrete", -0.95, -0.75, 0, -0.5, -0.3, 0.75, M["bin_grey"], bevel=0.02)
    for x in (-6.6, 1.6, 4.4, 20.4):                      # the first one moved 2.3 m west, off the walk's doorway
        L.cylinder("cast-bollard", x, -0.9, 0, 0.75, 0.07, M["black"], segs=16)
        L.sphere("cast-bollard-top", (x, -0.9, 0.82), 0.09, M["black"])


def banner(M, name, x, y):
    """a vertical banner hung beside the mast, turned to face down the street"""
    ux, uy = 0.0, -1.0                       # hangs out toward the street; its faces look east and west
    w, z0, z1 = 0.85, 3.75, 8.2
    ax, ay = x + 0.12 * ux, y + 0.12 * uy
    bx, by = ax + w * ux, ay + w * uy
    L.box(f"{name}-banner", min(ax, bx) - 0.004, min(ay, by), z0, max(ax, bx) + 0.004, max(ay, by), z1, M["banner"])
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    cy = (ay + by) / 2
    for side in (1, -1):                      # the print on both faces, reading bottom to top
        m3 = Matrix(((0.0, 0.0, 1.0), (0.0, -side * 1.0, 0.0), (side * 1.0, 0.0, 0.0))).transposed()
        t = L.text(f"{name}-print{side}", "KINEPOLIS", 0.36, (x + side * 0.012, cy, 4.15), (0, 0, 0), M["blue"],
                   extrude=0.0, font=font, align="LEFT")
        t.rotation_euler = m3.to_euler()
        bpy.context.view_layer.update()
        t.scale = (3.0 / t.dimensions.x, 0.36 / t.dimensions.y, 1)
        t.location = (x + side * 0.012, cy + side * 0.18, 4.15)
        L.box(f"{name}-logo{side}", x + side * 0.006 - 0.004, cy - 0.3, 7.35, x + side * 0.006 + 0.004, cy + 0.3, 7.95, M["blue"])
        star = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            rad = 0.2 if k % 2 == 0 else 0.08
            star.append((cy + rad * math.cos(a), 7.65 + rad * math.sin(a)))
        L.mesh_obj(f"{name}-logostar{side}", [(x + side * 0.012, yy, zz) for yy, zz in star], [tuple(range(10))], M["banner"])
    L.tube(f"{name}-arm", (x, y, 8.3), (bx, by, 8.3), 0.03, M["pole"])
    for s in (-1, 1):
        L.box(f"{name}-spot", x + s * 0.5 * uy - 0.08, y - s * 0.5 * ux - 0.08, 8.15, x + s * 0.5 * uy + 0.08,
              y - s * 0.5 * ux + 0.08, 8.35, M["lamp"])


def banner_mat(M):
    """white cloth, KINEPOLIS reading upwards in blue, a blue logo square with a white star at the top"""
    if "banner_print" in L.MATS:
        return L.MATS["banner_print"]
    img = ROOT / "build" / "photomatch" / "outside" / "banner.png"
    if not img.exists():
        make_banner_png(img)
    m = L.image_mat("banner_print", img, rough=0.7)
    return m


def make_banner_png(path):
    """draw the banner artwork with Blender's own image API: a tiny raster (no photo pixels)"""
    W, H = 128, 640
    im = bpy.data.images.new("banner_art", W, H, alpha=False)
    import array
    px = array.array("f", [1.0] * (W * H * 4))
    blue = (0.02, 0.09, 0.5, 1.0)

    def rect(x0, y0, x1, y1, c):
        for yy in range(max(0, y0), min(H, y1)):
            for xx in range(max(0, x0), min(W, x1)):
                i = 4 * (yy * W + xx)
                px[i:i + 4] = array.array("f", c)
    rect(14, H - 130, 114, H - 30, blue)                     # logo square near the top
    rect(0, 0, 6, H, blue)
    rect(W - 6, 0, W, H, blue)
    # a blocky KINEPOLIS reading bottom to top: letters as bars (it reads as text at this distance)
    y = 40
    for _ in "KINEPOLIS":
        rect(40, y, 88, y + 44, blue)
        rect(52, y + 8, 76, y + 36, (1, 1, 1, 1))
        y += 50
    im.pixels = px
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save()


def stair(M):
    # flight rising east along the facade from x 33.3 (ground) to the landing at 1.75 m
    n, x0, x1 = 11, 33.3, 41.0
    rise, run = 1.75 / n, (x1 - x0) / n
    for i in range(n):
        L.box("step", x0 + i * run, -2.4, 0, x1 + 0.0, -0.05, rise * (i + 1), M["stair"])
    L.box("landing", 41.0, -2.4, 0, 43.2, -0.05, 1.75, M["stair"])
    L.box("landing-block", 43.2, -3.2, 0, 47.5, 0.0, 4.0, M["concrete"])
    # handrails
    for y in (-2.35, -0.15):
        L.tube("rail", (x0, y, 0.95), (x1, y, 1.75 + 0.95), 0.025, M["rail"])
    for k in range(5):
        x = x0 + 0.3 + k * (x1 - x0 - 0.6) / 4
        z = (x - x0) / (x1 - x0) * 1.75
        L.tube("rail-post", (x, -2.35, z), (x, -2.35, z + 0.95), 0.02, M["rail"])


def trees(M):
    """young maples in the verge across the road, every 5.3 m"""
    parts = load_model("tree_small_02")
    rng = random.Random(7)
    if not parts:
        for k in range(-6, 15):
            L.cylinder("trunk", 3.84 + 5.3 * k, -24.0, 0, 2.6, 0.1, M["black"])
        return
    meshes = list(parts.values())
    autumn({m for o in meshes for m in o.data.materials if m})
    zmin = min(min((o.matrix_world @ Vector(c)).z for c in o.bound_box) for o in meshes)
    zmax = max(max((o.matrix_world @ Vector(c)).z for c in o.bound_box) for o in meshes)
    h0 = zmax - zmin
    xs = [-8.5, -1.8, 4.1, 10.42, 19.7, 26.14, 32.3, 39.4, 46.0, 53.5, 60.2, 68.0, 75.5]
    for x in xs:
        y = KERB0 - 1.6 + SKEW * x
        h = rng.uniform(9.5, 15.0)
        s = h / h0
        for o in meshes:
            c = o.copy()
            c.location = (x, y, -zmin * s)
            c.scale = (s * rng.uniform(0.6, 0.72), s * rng.uniform(0.6, 0.72), s)
            c.rotation_euler = (0, 0, rng.uniform(0, 6.28))
            bpy.context.scene.collection.objects.link(c)


def autumn(materials):
    """late-summer maples: leaves shifted toward yellow-green"""
    for m in materials:
        print("tree material", m.name)
        if not m.use_nodes or any(k in m.name.lower() for k in ("bark", "trunk", "branch")):
            continue
        nt = m.node_tree
        # the colour map feeds a Principled BSDF or a node group: put a hue shift on that link
        for link in list(nt.links):
            name = link.to_socket.name.lower()
            if link.from_node.type == "TEX_IMAGE" and link.from_socket.name == "Color" and \
                    any(k in name for k in ("base", "color", "colour", "albedo", "diffuse")):
                src_s, dst_s, dst_name = link.from_socket, link.to_socket, link.to_socket.name
                nt.links.remove(link)                     # read the link once: later links.new calls can move it
                hs = nt.nodes.new("ShaderNodeHueSaturation")      # lighter yellow-green
                hs.inputs["Hue"].default_value = 0.455
                hs.inputs["Saturation"].default_value = 0.95
                hs.inputs["Value"].default_value = 1.75
                nt.links.new(src_s, hs.inputs["Color"])
                orange = nt.nodes.new("ShaderNodeHueSaturation")  # autumn patches: orange-brown
                orange.inputs["Hue"].default_value = 0.39
                orange.inputs["Saturation"].default_value = 1.3
                orange.inputs["Value"].default_value = 1.6
                nt.links.new(src_s, orange.inputs["Color"])
                co = nt.nodes.new("ShaderNodeTexCoord")
                oi = nt.nodes.new("ShaderNodeObjectInfo")
                nz = nt.nodes.new("ShaderNodeTexNoise")
                nz.noise_dimensions = "4D"
                nz.inputs["Scale"].default_value = 0.9
                nt.links.new(co.outputs["Object"], nz.inputs["Vector"])
                nt.links.new(oi.outputs["Random"], nz.inputs["W"])
                mr = nt.nodes.new("ShaderNodeMapRange")
                mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.47, 0.6
                nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
                per = nt.nodes.new("ShaderNodeMath")              # some trees turn more than others
                per.operation = "MULTIPLY"
                nt.links.new(mr.outputs[0], per.inputs[0])
                lift = nt.nodes.new("ShaderNodeMapRange")
                lift.inputs["To Min"].default_value = 0.35
                nt.links.new(oi.outputs["Random"], lift.inputs["Value"])
                nt.links.new(lift.outputs[0], per.inputs[1])
                mx = nt.nodes.new("ShaderNodeMix")
                mx.data_type = "RGBA"
                nt.links.new(per.outputs[0], mx.inputs["Factor"])
                nt.links.new(hs.outputs["Color"], mx.inputs[6])
                nt.links.new(orange.outputs["Color"], mx.inputs[7])
                nt.links.new(mx.outputs[2], dst_s)
                print("tinted", m.name, dst_name)
                break


def load_model(asset):
    p = ROOT / "data" / "models" / asset / f"{asset}.blend"
    if not p.exists():
        return {}
    with bpy.data.libraries.load(str(p)) as (src, dst):
        dst.objects = list(src.objects)
    for img in bpy.data.images:
        fp = img.filepath.replace("\\", "/")
        if "textures/" in fp and asset in fp:
            img.filepath = str(ROOT / "data" / "models" / asset / "textures" / fp.rsplit("/", 1)[-1])
    return {o.name: o for o in dst.objects if o and o.type == "MESH"}


def decathlon(M):
    """the Decathlon store at the far end of the street, facing back down it (x = 100)"""
    L.box("dec", 100, -19.4, 0, 130, 3.4, 14.6, M["dec_grey"])
    L.box("dec-wing", 101.5, 3.4, 0, 130, 15.0, 11.7, M["dec_dark"])
    L.box("dec-band", 99.9, -18.6, 5.7, 100.0, 2.6, 6.9, M["dec_win"])
    L.box("dec-entrance", 99.9, -15.0, 0, 100.0, -3.0, 3.3, M["dec_win"])
    L.box("dec-canopy", 98.5, -18.6, 3.3, 100.0, 1.0, 3.7, M["dec_dark"])
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    t = L.text("dec-sign", "DECATHLON", 1.0, (99.8, -0.5, 9.9), (math.pi / 2, 0, -math.pi / 2), M["white_sign"],
               extrude=0.05, font=font, align="LEFT")
    bpy.context.view_layer.update()
    t.scale = (15.8 / t.dimensions.x, 1.8 / t.dimensions.y, 1)
    L.tube("dec-logo", (99.8, 1.3, 10.8), (99.86, 1.3, 10.8), 0.85, M["white_sign"], segs=24)
    # lattice mast and lighting columns
    L.cylinder("mast", 98, -14.5, 0, 30, 0.25, M["dec_dark"], segs=8, r_top=0.08)
    for x in range(-20, 100, 25):
        L.cylinder("lamp-col", x, -25.3, 0, 9.0, 0.08, M["dec_grey"], segs=10)
    # a low grey building left of the street end, and the far side's sheds
    L.box("far-shed", 70, 15, 0, 98, 40, 7.5, M["dec_grey"])


def across(M):
    """what the glass reflects: the car park's far side, sheds and a tree line behind the Street View cameras"""
    for x0, x1, y0, y1, h, mat in ((-60, -10, -95, -75, 9.0, "dec_grey"), (-5, 40, -100, -82, 11.0, "dec_grey"),
                                  (45, 90, -95, -78, 8.0, "dec_dark"), (-10, -5, -90, -80, 6.0, "concrete")):
        L.box("across", x0, y0, 0, x1, y1, h, M[mat])
        L.box("across-band", x0, y1 - 0.02, h * 0.45, x1, y1, h * 0.55, M["dec_win"])
    for k in range(-14, 22):
        x = 4.0 * k
        for o in (L.cylinder("across-trunk", x, -62.0, 0, 3.0, 0.15, M["black"], segs=8),
                  L.sphere("across-crown", (x, -62.0, 5.5), 3.2, M["hedge"])):
            o.visible_camera = False                      # only there to be reflected in the glass


def lighting(root):
    """the sky (HDRI turned so its sun matches the photos' shadows) as the world: for the unified venue, called once
    by whoever assembles it. The sun is the HDRI's own (no separate lamp)."""
    global ROOT
    ROOT = Path(root)
    light()


def light():
    hdri = ROOT / "data" / "textures" / "hdri" / "kloofendal_48d_partly_cloudy_puresky_2k.exr"
    w = L.world_sky(1.0, hdri=hdri)
    # turn the HDRI so its sun sits where the photos' shadows say: azimuth toward (-0.91, -0.42), ~49 deg up
    nt = w.node_tree
    env = next(n for n in nt.nodes if n.type == "TEX_ENVIRONMENT")
    mp = next(n for n in nt.nodes if n.type == "MAPPING")
    coord = next(n for n in nt.nodes if n.type == "TEX_COORD")
    for l in list(nt.links):
        if l.to_node == mp:
            nt.links.remove(l)
    nt.links.new(coord.outputs["Generated"], mp.inputs["Vector"])
    img = env.image
    import numpy as np
    W, H = img.size
    a = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(a)
    lum = a.reshape(H, W, 4)[..., :3].sum(2)
    yy, xx = np.unravel_index(int(lum.argmax()), lum.shape)
    u = (xx + 0.5) / W
    th_img = (0.5 - u) * 2 * math.pi                      # Blender: u = 0.5 - atan2(d.y, d.x) / 2pi
    th_t = math.atan2(-0.42, -0.91)
    turn = th_img - th_t                                  # the lookup vector is turned by this before sampling
    mp.inputs["Rotation"].default_value = (0, 0, turn)
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    hs = nt.nodes.new("ShaderNodeHueSaturation")         # Street View's sky is a deeper blue than the HDRI's
    hs.inputs["Saturation"].default_value = 1.0
    nt.links.new(env.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], bg.inputs["Color"])
    # the sky as the camera sees it is brighter than the light it gives (the photos' sky reads lighter)
    seen = nt.nodes.new("ShaderNodeBackground")
    seen.inputs["Strength"].default_value = 1.6
    nt.links.new(hs.outputs["Color"], seen.inputs["Color"])
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(seen.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    print(f"HDRI sun at u {u:.3f} v {yy / H:.3f}; turned {math.degrees(turn):.1f} deg")


def jog(objs):
    """step the facade east of XJ out by JOG (toward -y): vertices of the facade skin there move"""
    for o in objs:
        if o.type != "MESH" or o.name.startswith(("building", "interior")):
            continue
        mw = o.matrix_world
        inv = mw.inverted()
        me = o.data
        xs = [(mw @ v.co).x for v in me.vertices]
        if min(xs) >= XJ - 1e-4:
            east = set(range(len(me.vertices)))
        elif len(me.vertices) == 4 * len(me.polygons):      # loose quads (the skin): decide per face
            east = {i for p in me.polygons if (mw @ p.center).x > XJ for i in p.vertices}
        else:
            east = {i for i, x in enumerate(xs) if x > XJ + 1e-4}
        for i in east:
            w = mw @ me.vertices[i].co
            if -1.5 < w.y < 1.0:
                w.y -= JOG
                me.vertices[i].co = inv @ w


def build(root, unified=False):
    """unified=False: the photo-match scene (world, white balance). unified=True: part of the one venue model: no
    stand-ins behind the glass, see-through glass, no world or view settings (call lighting(root) once)."""
    global ROOT, UNIFIED
    ROOT = Path(root)
    UNIFIED = unified
    mine = set(bpy.data.objects)
    M = mats()
    if UNIFIED:
        for k in ("glass_up", "glass_dn", "glass_door"):
            M[k] = clear_glass(f"{k}_clear", {"glass_up": 0xd8e2ea, "glass_dn": 0xc9d2d8, "glass_door": 0xc9d2d8}[k])
    before = set(bpy.data.objects)
    facade(M)
    bpy.context.view_layer.update()
    jog([o for o in bpy.data.objects if o not in before])
    ground(M)
    before = set(bpy.data.objects)
    stair(M)
    for o in set(bpy.data.objects) - before:
        o.location.y -= JOG
    street_furniture(M)
    trees(M)
    decathlon(M)
    across(M)
    if not UNIFIED:
        light()
    # everything of this area into the venue frame
    root_ob = bpy.data.objects.new("outside-root", None)
    bpy.context.scene.collection.objects.link(root_ob)
    for o in set(bpy.data.objects) - mine:
        if o.parent is None and o is not root_ob:
            o.parent = root_ob
    root_ob.scale = (VS, VS, VS)
    root_ob.location = (VA, VY, VZ)
    if not UNIFIED:
        vs = bpy.context.scene.view_settings
        if hasattr(vs, "use_white_balance"):              # Street View's grade is warmer than the HDRI's daylight
            vs.use_white_balance = True
            vs.white_balance_temperature = 7000


def clear_glass(name, tint):
    """thin glass you see through from both sides: transparent, with Fresnel reflections on top"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = L.srgb(tint)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.02
    fr = nt.nodes.new("ShaderNodeLayerWeight")
    fr.inputs["Blend"].default_value = 0.35
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs["Fresnel"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*L.srgb(tint)[:3], 0.3)
    L.MATS[name] = m
    return m
