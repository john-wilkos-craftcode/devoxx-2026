"""Hollywood room, the side aisles and booths, matched to three photos, in the venue frame of the plan
(data/venue/venue.json: metres, +x east, +y north, z up, hall floor z = 0):

  aisle  (inside_hollywood_right.jpg, RF 85 mm) camera (19.01, -33.98, 2.0) looking north up the east aisle between
         the plan's column rows x 15.59 and 22.17 to the north wall y 18.3; resected on the x 15.59 row's column faces.
  asml   (hollywood_booth_closeup_left.jpg, 85 mm) camera (-5.53, -17.12, 1.7) looking north at the ASML booth's slats
         13.5 m away, the plan column (-3.8, -7.77) at the frame's right edge (the bay is a guess, see build_asml).
  robot  (inside_hollywood_w_booths.jpg, ~55 mm) camera (-17.62, -32.42, 1.6) pitched 12 deg down, looking north-east
         at the JetBrains booth, whose front faces south on the column row y -20.75 (as in the hollywood set).

Structure (columns, walls) comes from the plan where the photo shows it; everything else is placed by its pixel
position in the photo through the solved camera (pm.Cam) at a chosen depth, which is how a long lens sees it.
Known sizes set the scale where the plan has nothing (high tables 1.10 m x 0.62 m, people). Heights follow the photos
(the plan's 3.2-3.4 m walls are lower than the photo's 4.1 m end wall). People and the robot are left out; booth
graphics are simple stand-ins, no photo pixels.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

import pm_lib as L

ROOT = None
CAMS = {}
LOOK = "AgX - Medium High Contrast"
EXPOSURE = 0.0
GRADE = {  # per photo: exposure, the white point the photo was balanced to (K), tint: the photographer's grade
    "inside_hollywood_right": (-0.65, 9000, 26),
    "hollywood_booth_closeup_left": (-1.5, 3800, 30),
    "inside_hollywood_w_booths": (-0.15, 8400, 40),
}
LOOKS = {"hollywood_booth_closeup_left": "AgX - High Contrast"}
DOF = {  # focus distance (m along the view), f-stop on the 36 mm sensor
    "inside_hollywood_right": (32.0, 1.2),
    "hollywood_booth_closeup_left": (3.9, 4.5),
    "inside_hollywood_w_booths": (3.3, 3.4),
}


def cam(name):
    from pm import Cam
    if name not in CAMS:
        spec = json.loads((ROOT / "data" / "photomatch" / "cameras" / "hollywood_side.json").read_text())[name]
        CAMS[name] = Cam(json.loads((ROOT / "data" / "photomatch" / spec["cal"]).read_text()), spec["C"], spec.get("turns", 0))
    return CAMS[name]


def at(c, u, v, depth, axis=1):
    """the world point that shows at photo pixel (u, v) on the plane world[axis] = depth (depth: absolute)"""
    return Vector(c.on_plane(u, v, axis, depth))


# ---------------------------------------------------------------------------------- materials
def painted_block(name, color=0xe4e2df, rough=0.85, course=0.2, block=0.4, mortar=0.004, bump=0.15):
    """painted concrete blockwork: flat paint over shallow mortar joints (world-space brick texture)"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, color, rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = mortar
    brick.inputs["Brick Width"].default_value = block
    brick.inputs["Row Height"].default_value = course
    # map so that both x-facing and y-facing walls get joints: use (x + y, z)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    add = nt.nodes.new("ShaderNodeMath")
    nt.links.new(coord.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = bump
    bn.inputs["Distance"].default_value = 0.004
    nt.links.new(brick.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m


def ao_paint(name, color, rough=0.75, depth=0.6):
    """painted surface that darkens into corners and towards the floor (ambient occlusion), so white columns
    are not flat cards"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, color, rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 1.2
    ao.inputs["Color"].default_value = L.srgb(color)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1 - depth, 1.0
    nt.links.new(ao.outputs["AO"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["A"].default_value = L.srgb(color)
    mix.inputs["B"].default_value = tuple(v * 0.55 for v in L.srgb(color)[:3]) + (1,)
    # occlusion 1 (open) keeps the paint; towards 0 it multiplies in the darker shade
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(mr.outputs[0], inv.inputs[1])
    nt.links.new(inv.outputs[0], mix.inputs["Factor"])
    # grime at the foot: the bottom 0.35 m a little darker and warmer, patchy
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs[0])
    foot = nt.nodes.new("ShaderNodeMapRange")
    foot.inputs["From Min"].default_value, foot.inputs["From Max"].default_value = 0.0, 0.35
    foot.inputs["To Min"].default_value, foot.inputs["To Max"].default_value = 0.35, 0.0
    nt.links.new(sep.outputs["Z"], foot.inputs["Value"])
    patch = nt.nodes.new("ShaderNodeTexNoise")
    patch.inputs["Scale"].default_value = 6.0
    nt.links.new(coord.outputs["Object"], patch.inputs["Vector"])
    fm = nt.nodes.new("ShaderNodeMath")
    fm.operation = "MULTIPLY"
    nt.links.new(foot.outputs[0], fm.inputs[0])
    nt.links.new(patch.outputs["Fac"], fm.inputs[1])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.inputs["B"].default_value = L.srgb(0x6f655c)
    nt.links.new(fm.outputs[0], dirt.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], dirt.inputs["A"])
    nt.links.new(dirt.outputs["Result"], b.inputs["Base Color"])
    return m


def spiral_duct(name, color=0xc9ccd0, rough=0.3, metal=1.0):
    """galvanised spiral duct: satin aluminium (metallic, roughness ~0.3) with the spiral lock seam as a raised
    helix (UV: u around the duct 0..1, v along it in metres; the seam climbs 0.17 m per turn)"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, color, rough, metal=metal)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["UV"], sep.inputs[0])
    helix = nt.nodes.new("ShaderNodeMath")
    helix.operation = "MULTIPLY_ADD"
    helix.inputs[1].default_value = 0.17
    nt.links.new(sep.outputs["X"], helix.inputs[0])
    nt.links.new(sep.outputs["Y"], helix.inputs[2])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(helix.outputs[0], comb.inputs["Y"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 6.0                  # one seam every 0.17 m
    wave.inputs["Distortion"].default_value = 0.0
    nt.links.new(comb.outputs[0], wave.inputs["Vector"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.8
    nt.links.new(wave.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    # broad mottling so the metal is not one even sheen
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.8
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = rough - 0.06, rough + 0.08
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
    nt.links.new(ramp.outputs[0], b.inputs["Roughness"])
    return m


def carpet(name, color, speckle=0.18, scale=60.0, rough=0.95, streak=0.0, streak_angle=0.0):
    """needle-felt / tufted carpet: base colour with fine light and dark speckle; streak: darker heathered
    streaks along streak_angle (radians from +x), the pattern of the exhibition carpet"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, color, rough, bump=0.15, bump_scale=300)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")                 # object space = metres (objects sit at the origin)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = 8.0
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.6
    n3 = nt.nodes.new("ShaderNodeTexNoise")                 # the fibre: fine grain
    n3.inputs["Scale"].default_value = 160.0
    for n in (n1, n2, n3):
        nt.links.new(coord.outputs["Object"], n.inputs["Vector"])
    mr3 = nt.nodes.new("ShaderNodeMapRange")
    mr3.inputs["To Min"].default_value, mr3.inputs["To Max"].default_value = 0.8, 1.15
    nt.links.new(n3.outputs["Fac"], mr3.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    base = L.srgb(color)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1 - speckle, 1 + speckle
    nt.links.new(n1.outputs["Fac"], mr.inputs["Value"])
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["To Min"].default_value, mr2.inputs["To Max"].default_value = 0.9, 1.08
    nt.links.new(n2.outputs["Fac"], mr2.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(mr.outputs[0], mul.inputs[0])
    nt.links.new(mr2.outputs[0], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mr3.outputs[0], mul2.inputs[1])
    if streak:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, -streak_angle)
        mp.inputs["Scale"].default_value = (1.3, 3.2, 1.0)
        nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
        n4 = nt.nodes.new("ShaderNodeTexNoise")
        n4.inputs["Scale"].default_value = 2.2
        n4.inputs["Detail"].default_value = 4.0
        n4.inputs["Roughness"].default_value = 0.65
        nt.links.new(mp.outputs["Vector"], n4.inputs["Vector"])
        mr4 = nt.nodes.new("ShaderNodeMapRange")
        mr4.inputs["From Min"].default_value, mr4.inputs["From Max"].default_value = 0.42, 0.62
        mr4.inputs["To Min"].default_value, mr4.inputs["To Max"].default_value = 1.0, 1.0 - streak
        nt.links.new(n4.outputs["Fac"], mr4.inputs["Value"])
        mul3 = nt.nodes.new("ShaderNodeMath")
        mul3.operation = "MULTIPLY"
        nt.links.new(mul2.outputs[0], mul3.inputs[0])
        nt.links.new(mr4.outputs[0], mul3.inputs[1])
        mul2 = mul3
    comb = nt.nodes.new("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        nt.links.new(mul2.outputs[0], comb.inputs[k])
    mix.inputs["A"].default_value = base
    nt.links.new(comb.outputs[0], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def carpet_tex(name, tint, tile=0.5, mottle=0.22, hatch=0.06, rough=0.95, mottle_scale=5.0, broad=0.08):
    """loop-pile carpet from the CC0 Carpet016 set (data/textures/carpet), one texture repeat per `tile` metres,
    turned grey and tinted to the photo; small-scale mottling and a faint cross-hatch of the loop rows on top"""
    if name in L.MATS:
        return L.MATS[name]
    d = ROOT / "data" / "textures" / "carpet"
    m = L.mat(name, tint, rough)
    if not (d / "color.jpg").exists():
        return m
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])

    def image(file, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(d / file), check_existing=True)
        t.image.colorspace_settings.name = cs
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t
    col = image("color.jpg", "sRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col.outputs["Color"], bw.inputs["Color"])
    lvl = nt.nodes.new("ShaderNodeMapRange")                 # the texture's own light/dark, around 1.0
    lvl.inputs["From Min"].default_value, lvl.inputs["From Max"].default_value = 0.35, 0.75
    lvl.inputs["To Min"].default_value, lvl.inputs["To Max"].default_value = 0.7, 1.25
    nt.links.new(bw.outputs["Val"], lvl.inputs["Value"])
    n1 = nt.nodes.new("ShaderNodeTexNoise")                  # mottling: patches a few centimetres to 20 cm
    n1.inputs["Scale"].default_value = mottle_scale
    n1.inputs["Detail"].default_value = 6.0
    n1.inputs["Roughness"].default_value = 0.6
    nt.links.new(coord.outputs["Object"], n1.inputs["Vector"])
    m1 = nt.nodes.new("ShaderNodeMapRange")                  # contrast: the noise sits mostly near 0.5
    m1.inputs["From Min"].default_value, m1.inputs["From Max"].default_value = 0.4, 0.6
    m1.inputs["To Min"].default_value, m1.inputs["To Max"].default_value = 1 - mottle, 1 + mottle * 0.4
    nt.links.new(n1.outputs["Fac"], m1.inputs["Value"])
    prod = nt.nodes.new("ShaderNodeMath")
    prod.operation = "MULTIPLY"
    nt.links.new(lvl.outputs[0], prod.inputs[0])
    nt.links.new(m1.outputs[0], prod.inputs[1])
    n0 = nt.nodes.new("ShaderNodeTexNoise")                  # a very soft variation over metres
    n0.inputs["Scale"].default_value = 0.35
    nt.links.new(coord.outputs["Object"], n0.inputs["Vector"])
    m0 = nt.nodes.new("ShaderNodeMapRange")
    m0.inputs["To Min"].default_value, m0.inputs["To Max"].default_value = 1 - broad, 1 + broad
    nt.links.new(n0.outputs["Fac"], m0.inputs["Value"])
    pb = nt.nodes.new("ShaderNodeMath")
    pb.operation = "MULTIPLY"
    nt.links.new(prod.outputs[0], pb.inputs[0])
    nt.links.new(m0.outputs[0], pb.inputs[1])
    prod = pb
    n2 = nt.nodes.new("ShaderNodeTexNoise")                  # fleck: single loops a few millimetres across
    n2.inputs["Scale"].default_value = 70.0
    n2.inputs["Detail"].default_value = 2.0
    nt.links.new(coord.outputs["Object"], n2.inputs["Vector"])
    m2 = nt.nodes.new("ShaderNodeMapRange")
    m2.inputs["From Min"].default_value, m2.inputs["From Max"].default_value = 0.3, 0.7
    m2.inputs["To Min"].default_value, m2.inputs["To Max"].default_value = 0.78, 1.12
    nt.links.new(n2.outputs["Fac"], m2.inputs["Value"])
    p0 = nt.nodes.new("ShaderNodeMath")
    p0.operation = "MULTIPLY"
    nt.links.new(prod.outputs[0], p0.inputs[0])
    nt.links.new(m2.outputs[0], p0.inputs[1])
    prod = p0
    for axis in ("X", "Y"):                                  # loop rows: fine bands both ways
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = axis
        w.inputs["Scale"].default_value = 120.0
        nt.links.new(coord.outputs["Object"], w.inputs["Vector"])
        mw = nt.nodes.new("ShaderNodeMapRange")
        mw.inputs["To Min"].default_value, mw.inputs["To Max"].default_value = 1 - hatch, 1.0
        nt.links.new(w.outputs["Fac"], mw.inputs["Value"])
        p2 = nt.nodes.new("ShaderNodeMath")
        p2.operation = "MULTIPLY"
        nt.links.new(prod.outputs[0], p2.inputs[0])
        nt.links.new(mw.outputs[0], p2.inputs[1])
        prod = p2
    tintn = nt.nodes.new("ShaderNodeMix")
    tintn.data_type = "RGBA"
    tintn.blend_type = "MULTIPLY"
    tintn.inputs["Factor"].default_value = 1.0
    tintn.inputs["A"].default_value = L.srgb(tint)
    comb = nt.nodes.new("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        nt.links.new(prod.outputs[0], comb.inputs[k])
    nt.links.new(comb.outputs[0], tintn.inputs["B"])
    nt.links.new(tintn.outputs["Result"], b.inputs["Base Color"])
    nrm = image("normal.jpg", "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.8
    nt.links.new(nrm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


# ---------------------------------------------------------------------------------- parts
def duct(name, a, b, dia, material):
    """a straight spiral duct between two points; UV v runs along the length in metres for the seam rings"""
    segs = 20
    r = dia / 2
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    w = u.cross(d).normalized()
    length = (b - a).length
    verts, faces, uvs = [], [], []
    for end, t in ((a, 0.0), (b, length)):
        for i in range(segs + 1):
            ang = 2 * math.pi * i / segs
            verts.append(end + u * r * math.cos(ang) + w * r * math.sin(ang))
            uvs.append((i / segs, t))
    n = segs + 1
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(segs)]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    layer = me.uv_layers.new()
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def pendant(name, x, y, z_bottom, dia, height, shade, bulb, light_power=60, color=(1.0, 0.92, 0.82)):
    """industrial aluminium dome pendant (a lathed bell, open at the bottom, a lit reflector inside) on a neck and
    a cord up to the duct level; it throws a pool of light below"""
    r = dia / 2
    segs = 32
    prof = [(r, 0.0), (r * 0.98, 0.08), (r * 0.9, 0.22), (r * 0.74, 0.42), (r * 0.52, 0.62), (r * 0.36, 0.78),
            (r * 0.3, 0.9), (r * 0.3, 1.0)]
    verts, faces = [], []
    for rr, t in prof:
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((x + rr * math.cos(a), y + rr * math.sin(a), z_bottom + t * height))
    for j in range(len(prof) - 1):
        for k in range(segs):
            i0, i1 = j * segs + k, j * segs + (k + 1) % segs
            faces.append((i0, i1, i1 + segs, i0 + segs))
    L.mesh_obj(f"{name}-dome", verts, faces, shade, smooth=True)
    L.cylinder(f"{name}-reflector", x, y, z_bottom + height * 0.55, z_bottom + height * 0.6, r * 0.5, bulb, segs=24)
    L.cylinder(f"{name}-cord", x, y, z_bottom + height, z_bottom + height + 0.8, 0.006, L.mat("cord", 0x111111, 0.5), segs=6)
    L.spot(f"{name}-light", (x, y, z_bottom + height * 0.5), (x, y, 0.0), light_power, angle_deg=75, blend=0.6,
           color=color, radius=r * 0.4)


def star_logo(name, center, size, facing, back, star):
    """the Kinepolis bin label: a blue square with a white five-pointed star (facing: 'y-' or 'x+')"""
    cx, cy, cz = center
    h = size / 2
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = size * (0.36 if i % 2 == 0 else 0.15)
        pts.append((rr * math.cos(ang), rr * math.sin(ang)))
    if facing == "y-":
        sq = [(cx - h, cy, cz - h), (cx + h, cy, cz - h), (cx + h, cy, cz + h), (cx - h, cy, cz + h)]
        st = [(cx + px, cy - 0.002, cz + py) for px, py in pts]
    else:
        sq = [(cx, cy - h, cz - h), (cx, cy + h, cz - h), (cx, cy + h, cz + h), (cx, cy - h, cz + h)]
        st = [(cx + 0.002, cy + px, cz + py) for px, py in pts]
    L.quad(f"{name}-sq", sq, back)
    L.mesh_obj(f"{name}-star", st, [tuple(range(10))], star)


def bin_(name, x0, y0, w, d, h, logo=True):
    white = L.mat("bin-white", 0xeeeeec, 0.45)
    L.box(name, x0, y0, 0, x0 + w, y0 + d, h, white, bevel=0.01)
    L.box(f"{name}-lid", x0 - 0.01, y0 - 0.01, h, x0 + w + 0.01, y0 + d + 0.01, h + 0.03, white, bevel=0.005)
    if logo:
        star_logo(f"{name}-logo", (x0 + w / 2, y0 - 0.003, h * 0.62), 0.2, "y-",
                  L.mat("kine-blue", 0x1d4f9c, 0.5), L.mat("star-white", 0xf4f4f4, 0.5))


def truss(name, a, b, width, material, step=0.5):
    """square aluminium box truss: four chords and diagonal lacing between a and b"""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    w = u.cross(d).normalized()
    hw = width / 2
    corners = [u * hw + w * hw, -u * hw + w * hw, -u * hw - w * hw, u * hw - w * hw]
    for i, c in enumerate(corners):
        L.tube(f"{name}-chord{i}", a + c, b + c, 0.025, material, segs=8)
    n = max(1, int((b - a).length / step))
    for k in range(n):
        p0, p1 = a + d * (k * step), a + d * ((k + 1) * step)
        for i in range(4):
            c0, c1 = corners[i], corners[(i + 1) % 4]
            L.tube(f"{name}-lace{k}-{i}", p0 + c0, p1 + c1, 0.01, material, segs=6)


# ---------------------------------------------------------------------------------- set: aisle
# the Hollywood room in the venue plan (data/venue/venue.json, floor 0): column rows and walls near the east aisle
PLAN_ROWS_Y = (-27.28, -20.75, -14.57, -7.77, -1.32, 5.17)
PLAN_COLS_X = (9.13, 15.59, 22.17)
PLAN_NORTH_Y = 18.3
PLAN_EAST_X, PLAN_EAST_Y0 = 22.02, -8.15            # east wall north of y -8.15 (x 24.42 south of it)
COL = 0.7


def build_aisle():
    """the east aisle between the plan's column rows x 15.59 and 22.17, seen from y -34 looking north to the
    north wall. Structure from the plan; everything else placed by its pixel position in the photo at a depth
    chosen to sit right against that structure (depths mapped from the first, plan-free layout by DEPTHS)."""
    c = cam("inside_hollywood_right")
    white = ao_paint("col-white-ao", 0xe9e8e6, 0.7)
    block = painted_block("block-white", 0xe2e0dd)
    black = L.mat("ceiling-black", 0x07080d, 0.95)
    metal = spiral_duct("duct")
    alu = L.mat("alu-dome", 0xd4d6d9, 0.22, metal=1.0)
    bulb = L.emissive("bulb-warm", 0xfff1dd, 40.0)
    floor = carpet_tex("aisle-carpet", 0x6c6868, tile=0.5, mottle=0.14, hatch=0.08, mottle_scale=20.0, broad=0.07)
    OX, OY, H = c.C
    import numpy as np
    old = [0.0, 13.5, 19.0, 25.3, 48.8, 80.0]                # depths of the first layout (no plan) ...
    new = [0.0, 19.06, 25.86, 32.3, PLAN_NORTH_Y - OY, 83.0]  # ... and where the plan puts the same things

    def Y(d):
        """world y of a depth d of the first layout (d in its 5000 px units, as written below)"""
        return OY + float(np.interp(d * 5856 / 5000.0, old, new))
    END = PLAN_NORTH_Y

    def W(xr, d, z):
        """a point given relative to the camera in the first layout -> the venue, keeping its pixel position"""
        dr = d * 5856 / 5000.0
        sc = (Y(d) - OY) / dr
        return Vector((OX + xr * sc, Y(d), H + (z - H) * sc))

    L.box("aisle-floor", 5.0, -40.0, -0.05, 30.0, END + 1.0, 0, floor)
    # a purple-grey carpet patch in the aisle, low centre-right (measured in the photo)
    pts = [at(c, 1160, 1654, 0, 2), at(c, 1550, 1654, 0, 2), at(c, 1510, 1240, 0, 2), at(c, 1255, 1240, 0, 2)]
    L.mesh_obj("aisle-runner", [(p.x, p.y, 0.004) for p in pts], [(0, 1, 2, 3)], carpet_tex("runner-carpet", 0x5a4e72, tile=0.35, mottle=0.1, hatch=0.12, mottle_scale=28.0))
    L.box("aisle-ceiling", 5.0, -40.0, 5.4, 30.0, END + 1.0, 5.5, black)

    # --- the plan: columns (white to 3.0 m, black above: the photo's upper zone is dark), north and east walls
    for cx in PLAN_COLS_X:
        for cy in PLAN_ROWS_Y:
            zw = 2.3 if cx > 20 else (4.0 if (cx, cy) == (15.59, -14.57) else 3.3)
            L.box(f"aisle-col-{cx}-{cy}", cx - COL / 2, cy - COL / 2, 0, cx + COL / 2, cy + COL / 2, zw, white)
            L.box(f"aisle-col-top-{cx}-{cy}", cx - COL / 2, cy - COL / 2, zw, cx + COL / 2, cy + COL / 2, 5.4, black)
    wall_top = 4.13                                            # the photo's end-wall top (plan walls: 3.2-3.4 m)
    L.box("aisle-endwall", 8.0, END, 0, PLAN_EAST_X, END + 0.3, wall_top, block)
    L.box("aisle-endwall-above", 5.0, END + 0.3, wall_top, 30.0, END + 0.6, 5.4, black)
    split = Y(22.0)                                            # where the planter beam crosses
    L.box("aisle-wall-e", PLAN_EAST_X, PLAN_EAST_Y0, 0, PLAN_EAST_X + 0.3, END, 2.9, block)
    L.box("aisle-wall-e-top", PLAN_EAST_X, split, 2.9, PLAN_EAST_X + 0.3, END, wall_top, block)
    L.box("aisle-wall-e-black", PLAN_EAST_X, PLAN_EAST_Y0, 2.9, PLAN_EAST_X + 0.3, split, 5.4, black)
    L.box("aisle-wall-e-cap", PLAN_EAST_X, split, wall_top, PLAN_EAST_X + 0.3, END, wall_top + 0.1, white)
    dark = L.mat("booth-black", 0x070708, 0.9)
    L.box("aisle-wall-e2", 24.42, -22.35, 0, 24.72, PLAN_EAST_Y0, 5.4, dark)
    L.box("aisle-wall-e2-n", PLAN_EAST_X, PLAN_EAST_Y0 - 0.3, 0, 24.72, PLAN_EAST_Y0, 5.4, dark)
    L.box("aisle-booths-e", 22.6, -30.0, 0, 22.7, -22.35, 2.6, dark)
    # a linear fluorescent fitting on the end wall, just under the ducts
    p0, p1 = at(c, 1055, 583, END - 0.6), at(c, 1335, 583, END - 0.6)
    L.box("aisle-tube", p0.x, END - 0.65, p0.z - 0.035, p1.x, END - 0.55, p0.z + 0.035, L.emissive("tube", 0xf4f6ff, 12.0))
    L.box("aisle-tube-body", p0.x - 0.05, END - 0.5, p0.z + 0.03, p1.x + 0.05, END - 0.4, p0.z + 0.08, white)
    # a dark double door in the east wall (u 1800-1850)
    d0, d1 = at(c, 1800, 900, PLAN_EAST_X, 0), at(c, 1855, 900, PLAN_EAST_X, 0)
    for k, p in enumerate((d0, d1)):
        L.box(f"aisle-doorpost-{k}", PLAN_EAST_X - 0.05, p.y - 0.03, 0, PLAN_EAST_X, p.y + 0.03, 2.4,
              L.mat("black-metal", 0x141414, 0.5, metal=0.6))
    L.box("aisle-door", PLAN_EAST_X - 0.02, d1.y, 0, PLAN_EAST_X + 0.01, d0.y, 2.35, L.mat("door-dark", 0x2a2a2c, 0.6))
    # dark duct across the right half at the planter, hiding the wall's top (v ~ 500-550 at u 1500-2100)
    a_, b_ = at(c, 1500, 525, split), at(c, 2100, 525, split)
    duct("aisle-beam-r", (a_.x, split, a_.z), (PLAN_EAST_X, split, a_.z), 0.5 * (split - OY) / 25.5,
         spiral_duct("duct-black", 0x1a1c22, 0.4))
    # hanging planter shelf with ferns along the east wall (u 1700-2050, v 610-690)
    yp = Y(24.0)
    s0, s1 = at(c, 1700, 610, yp), at(c, 2050, 690, yp)
    frame = L.mat("black-metal", 0x141414, 0.5, metal=0.6)
    L.box("aisle-planter-frame", s0.x, yp - 1.0, s1.z, min(s1.x, PLAN_EAST_X - 0.05), yp + 0.5, s1.z + 0.04, frame)
    for k in range(5):
        x = s0.x + (s1.x - s0.x) * (k + 0.5) / 5
        L.box(f"aisle-pot{k}", x - 0.1, yp - 0.4, s1.z - 0.26, x + 0.1, yp - 0.2, s1.z, L.mat("pot-black", 0x101010, 0.6))
    fern("aisle-fern", (s0.x + s1.x) / 2, yp - 0.3, s1.z + 0.02, s1.x - s0.x, 1.1, dense=True)
    fern("aisle-fern-hang", (s0.x + s1.x) / 2, yp - 0.3, s1.z - 0.05, s1.x - s0.x, 0.7)
    q = at(c, 1585, 1000, END - 1.2)
    fern("aisle-shrub", q.x, END - 1.2, 0.9, 1.3, 1.3, dense=True)

    # glowing high counter (u 1700-1960, top v 1100, base v 1440): white top, blue LED body
    yc = OY + H * c.f / (1440 - c.c[1])
    a_, b_ = at(c, 1700, 1100, yc), at(c, 1960, 1100, yc)
    L.box("aisle-counter-top", a_.x, yc, 1.0, b_.x, yc + 0.6, 1.06, L.emissive("counter-white", 0xeef2ff, 6.0))
    L.box("aisle-counter-body", a_.x + 0.04, yc + 0.02, 0.0, b_.x - 0.04, yc + 0.58, 1.0, L.emissive("counter-blue", 0x2d3cff, 5.0))

    # the first layout's small items, carried over keeping their pixel positions
    ys = -14.57 - COL / 2 - 0.05                              # a black loudspeaker on the nearest column's face
    s0, s1 = at(c, 160, 470, ys), at(c, 300, 180, ys)
    L.box("aisle-speaker", s0.x, ys - 0.45, s0.z, s1.x, ys, s1.z, L.mat("speaker-black", 0x161616, 0.6))
    L.box("aisle-booth-left", 8.9, -30.0, 0, 9.0, -24.0, 2.5, L.mat("booth-print", 0x5a3a44, 0.7))
    a_, b_ = W(-3.4, 6.5, 4.2), W(-3.4, 13.0, 4.2)
    truss("aisle-truss", a_, b_, 0.3 * (b_.y - OY) / 15.2, L.mat("truss-alu", 0xc8cacc, 0.3, metal=1.0))

    # ducts across the aisle, placed by their photo rows: (v centre, apparent diameter px, depth, u from, u to)
    hanger = L.mat("cord", 0x111111, 0.5)
    for i, (v, dia_px, d, u0, u1) in enumerate([(140, 90, 13.0, -400, 2900), (326, 60, 22.0, 250, 1880),
                                              (380, 40, 25.0, 350, 1520), (428, 26, 33.0, 600, 1360),
                                              (485, 28, 38.0, 700, 1350), (520, 22, 40.5, 600, 1400),
                                              (250, 42, 16.5, -400, 2900), (360, 26, 23.5, 300, 1700),
                                              (455, 20, 31.0, 500, 1450), (505, 18, 36.0, 650, 1420)]):
        y = Y(d)
        pc = at(c, 1240, v, y)
        dia = dia_px * (y - OY) / c.f
        a_, b_ = at(c, u0, v, y), at(c, u1, v, y)
        x1 = min(b_.x, PLAN_EAST_X)
        duct(f"aisle-duct{i}", (a_.x, y, pc.z), (x1, y, pc.z), dia, metal)
        for k in range(int((x1 - a_.x) / 3.0) + 1):
            L.cylinder(f"aisle-hanger{i}-{k}", a_.x + 1.0 + 3.0 * k, y, pc.z + dia / 2, 5.4, 0.008, hanger, segs=6)
    # vertical spiral drops: near the end wall (u 1320-1400), the elbow on the left, one mid-way
    for name_, u, v_top, v_bot, d, dia_px in (("drop-end", 1360, 485, 565, 38.0, 30), ("drop-left", 480, 300, 430, 15.0, 70),
                                             ("drop-mid", 905, 455, 540, 31.0, 24)):
        y = Y(d)
        top, bot = at(c, u, v_top, y), at(c, u, v_bot, y)
        duct(f"aisle-{name_}", top, bot, dia_px * (y - OY) / c.f, metal)
    # dome pendants: (u centre, v bottom, apparent dia px, depth)
    for i, (u, vb, dpx, d) in enumerate([(2280, 370, 190, 13.0), (1820, 480, 130, 18.0), (1550, 520, 95, 24.0),
                                       (540, 520, 90, 15.0), (725, 560, 70, 20.0), (870, 570, 50, 27.0),
                                       (940, 560, 40, 33.0), (1300, 575, 45, 33.0), (1150, 545, 34, 38.0),
                                       (140, 200, 120, 11.5), (1450, 548, 50, 29.0), (1040, 565, 32, 40.0),
                                       (640, 545, 60, 22.0)]):
        y = Y(d)
        pc = at(c, u, vb, y)
        dia = dpx * (y - OY) / c.f
        pendant(f"aisle-pend{i}", pc.x, y, pc.z, dia, dia * 0.9, alu, bulb, light_power=320)
    for i, (u, v, d) in enumerate([(1910, 205, 14.0), (1725, 320, 17.0), (1590, 410, 22.0), (1640, 420, 22.0)]):
        y = Y(d)
        pc = at(c, u, v, y)
        L.sphere(f"aisle-spot{i}", (pc.x, y, pc.z), 0.004 * (y - OY), L.emissive("spot-hot", 0xfff6e8, 60.0))

    # bins with the Kinepolis star, stood on the floor where the photo has them
    yb = OY + 15.2
    q0, q1 = at(c, 385, 1654, yb), at(c, 550, 1654, yb)
    bin_("aisle-bin1", q0.x, yb, q1.x - q0.x, 0.4, 0.95)
    yb = OY + H * c.f / (1435 - c.c[1])
    q0, q1 = at(c, 615, 1435, yb), at(c, 755, 1435, yb)
    bin_("aisle-bin2", q0.x, yb, q1.x - q0.x, 0.4, 0.95)
    q = at(c, 1370, 1040, END - 6.0)
    L.cylinder("aisle-cloth-table", q.x, END - 6.0, 0, 1.1, 0.4, L.mat("cloth-black", 0x0d0d0d, 0.9), r_top=0.42)
    q = at(c, 900, 900, END - 2.0)
    blossom("aisle-blossom", q.x, END - 2.0)

    # light: pools under the pendants (above), the end wall washed bright, a dim fill, a dark ceiling zone
    L.area_light("aisle-wash-end", (OX, END - 9, 4.4), 9.0, 2400, color=(1.0, 0.97, 0.93),
                 rot=(math.radians(55), 0, 0), size_y=3.0)
    L.area_light("aisle-wash-mid", (OX, OY + 30, 3.0), 5.0, 420, color=(1.0, 0.97, 0.93), size_y=14.0)
    L.area_light("aisle-wash-near", (OX, OY + 17, 3.0), 5.0, 260, color=(1.0, 0.97, 0.93), size_y=8.0)
    # light from below onto the duct runs (the hall's floor and booths bounce it up): their silver undersides
    # strip lights just under the ceiling: the bright streak along the top of each duct
    for k, dy in enumerate((14.0, 20.0, 27.0, 34.0, 42.0)):
        L.area_light(f"aisle-duct-strip{k}", (OX, OY + dy, 5.25), 12.0, 260, color=(1.0, 0.98, 0.95), size_y=0.4)
    # the far end hazier and warmer: a thin warm haze in the aisle
    haze = bpy.data.materials.new("aisle-haze")
    haze.use_nodes = True
    hn = haze.node_tree
    hn.nodes.remove(hn.nodes["Principled BSDF"])
    vol = hn.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.0012
    vol.inputs["Color"].default_value = L.srgb(0xf2e2d2)
    hn.links.new(vol.outputs[0], hn.nodes["Material Output"].inputs["Volume"])
    L.box("aisle-haze", 8.0, OY + 3.0, 0.02, PLAN_EAST_X - 0.01, END - 0.05, 5.35, haze)
    L.area_light("aisle-fill-back", (OX - 0.5, OY + 2.0, 2.6), 7.0, 1400, color=(0.95, 0.97, 1.0),
                 rot=(math.radians(80), 0, 0), size_y=2.5)


def fern(name, x, y, z, width, height, dense=False):
    """a clump of drooping leaf blades (no photo texture): thin green strips arching down from z"""
    import random
    rnd = random.Random(hash(name) & 0xffff)
    green = L.mat("leaf-green", 0x2f5a26, 0.55)
    verts, faces = [], []
    n = 90 if dense else 60
    for k in range(n):
        x0 = x + rnd.uniform(-width / 2, width / 2)
        y0 = y + rnd.uniform(-0.3, 0.3)
        ang = rnd.uniform(0, 2 * math.pi)
        length = rnd.uniform(0.4, height)
        dx, dy = math.cos(ang), math.sin(ang)
        w = 0.05
        base = len(verts)
        steps = 6
        for s in range(steps + 1):
            t = s / steps
            reach = length * 0.6 * t
            drop = (length * t) ** 1.6 * (0.9 if not dense else -0.6)
            px, py = x0 + dx * reach, y0 + dy * reach
            pz = z - drop if not dense else z + length * t * 0.9 - (reach ** 2) * 0.6
            ww = w * (1 - t * 0.8)
            verts += [(px - dy * ww, py + dx * ww, pz), (px + dy * ww, py - dx * ww, pz)]
        for s in range(steps):
            i = base + 2 * s
            faces.append((i, i + 1, i + 3, i + 2))
    L.mesh_obj(name, verts, faces, green, smooth=True)


def blossom(name, x, y):
    """artificial cherry-blossom tree: dark trunk, a cloud of pink blossom balls"""
    import random
    rnd = random.Random(7)
    L.cylinder(f"{name}-trunk", x, y, 0, 1.6, 0.05, L.mat("bark", 0x3b2a22, 0.8))
    pink = L.mat("blossom-pink", 0xe6a3bf, 0.7)
    for k in range(40):
        L.sphere(f"{name}-b{k}", (x + rnd.uniform(-0.55, 0.55), y + rnd.uniform(-0.4, 0.4), rnd.uniform(1.3, 2.5)),
                 rnd.uniform(0.08, 0.16), pink)


# ---------------------------------------------------------------------------------- set: robot
def hit(c, u, v, p0, normal):
    """where the ray through photo pixel (u, v) meets the plane through p0 with this normal"""
    d = Vector(c.ray(u, v))
    C = Vector(c.C)
    t = (Vector(p0) - C).dot(Vector(normal)) / d.dot(Vector(normal))
    return C + d * t


def high_table(name, cx, cy, turn, side=0.62, height=1.10, top_color=0xcfcdcb):
    """bar table: black square-tube frame (legs, a base square, a top square) under a thin pale top"""
    frame = L.mat("table-frame", 0x121212, 0.45, metal=0.5)
    top = L.mat("table-top", top_color, 0.5)
    h = side / 2
    ca, sa = math.cos(turn), math.sin(turn)
    P = lambda x, y, z: Vector((cx + x * ca - y * sa, cy + x * sa + y * ca, z))  # noqa: E731
    corners = [(-h, -h), (h, -h), (h, h), (-h, h)]
    t = 0.025
    for i, (x, y) in enumerate(corners):
        L.tube(f"{name}-leg{i}", P(x, y, 0.0), P(x, y, height - 0.02), t / 2, frame, segs=4)
        x2, y2 = corners[(i + 1) % 4]
        for z in (0.0125, height - 0.035):
            L.tube(f"{name}-bar{i}-{z:.2f}", P(x, y, z), P(x2, y2, z), t / 2, frame, segs=4)
    v = [P(x * 1.02, y * 1.02, height - 0.02) for x, y in corners] + [P(x * 1.02, y * 1.02, height) for x, y in corners]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    L.mesh_obj(f"{name}-top", v, f, top)


def gradient_print(name, c0, c1, c2, scale=1.2):
    """booth print: dark violet ground with soft magenta/pink waves (procedural, no artwork copied)"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, c0, 0.6)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = scale * 0.4
    wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail Scale"].default_value = 0.6
    nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = L.srgb(c0)
    ramp.color_ramp.elements[1].color = L.srgb(c2)
    e = ramp.color_ramp.elements.new(0.55)
    e.color = L.srgb(c1)
    ramp.color_ramp.elements[0].position = 0.35
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 0.25
    return m


def build_robot():
    c = cam("inside_hollywood_w_booths")
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    X0, Y0 = c.C[0], c.C[1]
    floor = carpet_tex("robot-carpet", 0x7b7377, tile=0.5, mottle=0.16, hatch=0.1, mottle_scale=20.0, broad=0.07)
    L.box("robot-floor", X0 - 20, Y0 - 5, -0.05, X0 + 25, Y0 + 30, 0, floor)
    # high tables, square to the hall: table 1 solved with the camera (0.62 m, 1.10 m); table 2's left leg shows
    # at the photo's right edge (u 1600, foot v 1680); table 3 stands behind the woman (base corners v ~1080-1110)
    turn = -0.075
    high_table("robot-table1", -13.151, -26.437, turn)
    leg = c.floor(1600, 1680)
    d = 0.62 / math.sqrt(2)
    a_ = turn - math.pi / 4                                   # leftmost corner -> centre, in the hall's frame
    high_table("robot-table2", leg[0] + d * math.cos(a_), leg[1] + d * math.sin(a_), turn)
    lc, rc = c.floor(1201, 1083), c.floor(1543, 1078)
    high_table("robot-table3", (lc[0] + rc[0]) / 2, (lc[1] + rc[1]) / 2, turn)

    # the booth row: its floor edge runs across the photo (v 1000 at the left edge to v 850 at u 1300)
    E0, E1 = Vector(c.floor(0, 1000)), Vector(c.floor(1300, 850))
    U = (E1 - E0).normalized()
    N = Vector((-U.y, U.x, 0))                                  # into the booth, away from the camera
    ang = math.atan2(U.y, U.x)
    t0, t1 = -6.0, 9.0

    def pt(t, b, z=0.0):
        return E0 + U * t + N * b + Vector((0, 0, z))

    def slab(name, ta, tb, ba, bb, za, zb, mat):
        v = [pt(ta, ba, za), pt(tb, ba, za), pt(tb, bb, za), pt(ta, bb, za),
             pt(ta, ba, zb), pt(tb, ba, zb), pt(tb, bb, zb), pt(ta, bb, zb)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return L.mesh_obj(name, v, f, mat)

    def tz(u, v, b):
        """(t along the booth, height) of photo pixel (u, v) on the plane b metres behind the booth edge"""
        p = hit(c, u, v, pt(0, b), N)
        return (p - E0).dot(U), p.z

    slab("robot-platform", t0, t1, 0.0, 4.0, 0.0, 0.05, L.mat("booth-floor", 0x26252a, 0.8))
    slab("robot-platform-edge", t0, t1, -0.02, 0.0, 0.0, 0.055, L.mat("edge-trim", 0xd9d6da, 0.35, metal=0.3))
    B = 2.4                                                    # the printed back wall
    tA, _ = tz(500, 300, B)
    tK, _ = tz(990, 300, B)
    slab("robot-wall-left", t0, tA, B, B + 0.06, 0.05, 3.6, gradient_print("print-waves", 0x45375f, 0xc23a8c, 0xe86aa8))
    slab("robot-wall-kotlin", tA, tK + 0.3, B, B + 0.06, 0.05, 3.6, L.mat("print-charcoal", 0x37343f, 0.6))
    slab("robot-post", tA - 0.03, tA + 0.03, B - 0.04, B, 0.05, 3.6, L.mat("post-alu", 0xc9c9cc, 0.35, metal=0.8))
    white = L.mat("text-white", 0xf2f2f2, 0.5)
    rot = (math.pi / 2, 0, ang)

    def label(name, body, u, v, b, size, mat=white, align="LEFT"):
        t, z = tz(u, v, b)
        L.text(name, body, size, pt(t, b - 0.005, z), rot, mat, extrude=0.0, font=font, align=align)
    label("robot-q", "How do you feel about AI\nat work?", 150, 150, B, 0.12)
    label("robot-jb", "JETBRAINS", 625, 98, B, 0.1)
    t, z = tz(595, 105, B)
    slab("robot-jb-icon", t, t + 0.12, B - 0.01, B - 0.005, z, z + 0.12, L.mat("jb-orange", 0xf0542a, 0.5))
    label("robot-kotlin", "Kotlin", 590, 195, B, 0.26)
    label("robot-sub", "Going Agent with Less Boilerplate", 590, 245, B, 0.07)
    label("robot-sub2", "Kotlin for AI agents - booth talks all day", 590, 290, B, 0.05)

    # the TV tower: a magenta header with the mascot, a TV, a violet glow panel, a counter in front
    T = 1.1
    ta, _ = tz(960, 300, T)
    tb, _ = tz(1265, 300, T)
    _, z_tv0 = tz(1100, 402, T)
    _, z_tv1 = tz(1100, 165, T)
    _, z_pp = tz(1100, 540, T)
    slab("robot-tower", ta, tb, T, T + 0.4, 0.05, 3.6, L.mat("tower-dark", 0x1d1b22, 0.7))
    slab("robot-header", ta, tb, T - 0.01, T, z_tv1, 3.6, gradient_print("print-magenta", 0xc0207a, 0xe2338c, 0xd02a90, 0.5))
    ta2, _ = tz(988, 300, T)
    tb2, _ = tz(1281, 300, T)
    slab("robot-tv", ta2, tb2 - 0.04, T - 0.06, T - 0.01, z_tv0, z_tv1, L.mat("tv-black", 0x050506, 0.15, coat=0.6))
    slab("robot-glow", ta, tb, T - 0.01, T, z_pp, z_tv0, L.emissive("violet-glow", 0x4a2ea8, 1.5))
    # mascot: a blue rounded head with two ears and big white eyes
    tm, zm = tz(1120, 85, T)
    blue = L.mat("mascot-blue", 0x3b63e0, 0.5)
    slab("robot-mascot", tm - 0.25, tm + 0.25, T - 0.03, T - 0.015, zm - 0.22, zm + 0.18, blue)
    for side in (-1, 1):
        slab(f"robot-ear{side}", tm + side * 0.2 - 0.06, tm + side * 0.2 + 0.06, T - 0.03, T - 0.015, zm + 0.18, zm + 0.3, blue)
        L.sphere(f"robot-eye{side}", pt(tm + side * 0.1, T - 0.04, zm), 0.08, white)
    # counter in front of the tower
    C0 = 0.45
    _, z_ct = tz(1100, 525, C0)
    slab("robot-counter", ta, tb, C0, T - 0.05, 0.05, z_ct, L.mat("counter-charcoal", 0x2b2930, 0.55))
    t, z = tz(1030, 600, C0)
    slab("robot-counter-logo", t, t + 0.12, C0 - 0.006, C0 - 0.001, z - 0.12, z, L.mat("jb-orange", 0xf0542a, 0.5))
    # the white wall of the next booth, square to the booth row, at the tower's right side
    slab("robot-side-wall", tb, tb + 0.08, 0.0, 4.0, 0.05, 3.6, L.mat("wall-white", 0xe9e6ea, 0.8))
    slab("robot-next-booth", tb + 0.08, t1, 3.0, 3.1, 0.05, 3.6, L.mat("wall-white", 0xe9e6ea, 0.8))
    for k, (u, v0, v1) in enumerate([(1285, 130, 300), (1430, 300, 380)]):
        p0 = hit(c, u, v0, pt(tb + 0.08, 0), U)
        p1 = hit(c, u, v1, pt(tb + 0.08, 0), U)
        b = (p0 - E0).dot(N)
        slab(f"robot-frame{k}", tb + 0.08, tb + 0.1, b, b + 0.3, p1.z, p0.z, L.mat("frame-dark", 0x222224, 0.5))
    # an orange-lit bar on the left, in front of the printed wall
    ta3, z_bar = tz(40, 500, 1.2)
    tb3, _ = tz(220, 500, 1.2)
    # three glowing orange panels with dark joints, and the warm light they throw
    glow = L.emissive("bar-orange", 0xff5200, 2.2)
    for k in range(3):
        a3 = ta3 + (tb3 - ta3) * k / 3
        slab(f"robot-bar{k}", a3 + 0.02, a3 + (tb3 - ta3) / 3 - 0.02, 1.2, 1.25, 0.05, z_bar, glow)
    slab("robot-bar-body", ta3, tb3, 1.25, 1.8, 0.05, z_bar, L.mat("bar-dark", 0x1a1210, 0.6))
    L.point("robot-bar-light", pt((ta3 + tb3) / 2, 0.8, 0.8), 120, color=(1.0, 0.45, 0.12), radius=0.4)

    # light: an even, bright exhibition-hall overhead light
    mid = c.floor(827, 1240)
    L.area_light("robot-key", (mid[0], mid[1], 6.0), 14.0, 2000, color=(1.0, 0.93, 0.95), size_y=16.0)
    L.area_light("robot-front", (X0, Y0, 4.0), 6.0, 700, color=(1.0, 0.98, 0.96),
                 rot=(math.radians(70), 0, math.radians(-44)), size_y=3.0)


# ---------------------------------------------------------------------------------- set: asml
def oak(name, tone):
    """warm oak board: its own base tone with long vertical grain streaks (object space, metres)"""
    if name in L.MATS:
        return L.MATS[name]
    m = L.mat(name, tone, 0.7)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (60.0, 60.0, 1.5)       # stretched along z: grain runs up the board
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 1.0
    grain.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], grain.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    lo, hi = L.srgb(tone), L.srgb(tone)
    ramp.color_ramp.elements[0].color = tuple(v * 0.62 for v in lo[:3]) + (1,)
    ramp.color_ramp.elements[1].color = tuple(min(1, v * 1.25) for v in hi[:3]) + (1,)
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.35, 0.65
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.2
    nt.links.new(grain.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m


def wood_slats(name, x0, x1, y, z0, z1, n, depth=0.04):
    """a wall of vertical oak boards with dark gaps; every board its own warm tone"""
    import random
    rnd = random.Random(3)
    gap = L.mat("slat-gap", 0x0d0907, 0.9)
    L.box(f"{name}-back", x0, y + depth, z0, x1, y + depth + 0.03, z1, gap)
    w = (x1 - x0) / n
    tones = [0x8d6540, 0x76522f, 0x9a7450, 0x6a4628, 0x85613e, 0xa07a52, 0x7c5735]
    for i in range(n):
        m = oak(f"oak-{i}", tones[rnd.randrange(len(tones))])
        a = x0 + i * w + 0.01
        L.box(f"{name}-{i}", a, y + rnd.uniform(0, 0.012), z0, a + w - 0.02, y + depth, z1, m)


def build_asml():
    """the ASML booth seen past three people, the plan's column (-3.8, -7.77) at the right edge of the frame.
    Which bay the stand is in is not known: x follows from the white lowered ceiling of the room's central zone
    showing top right (its edge on the column line x -3.8); the bay y -7.77 is the one that keeps the view clear
    of the JetBrains booth (y ~ -21) and of the west stair (from y -1.32). Depths: metres in front of the camera."""
    c = cam("hollywood_booth_closeup_left")
    X0, OY, H = c.C
    font = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"

    def A(u, v, d):
        return at(c, u, v, OY + d)

    def Yd(d):
        return OY + d
    D = 13.5                                                   # the slat wall
    navy = L.mat("booth-navy", 0x0c1226, 0.7)
    floor = carpet("asml-floor", 0x4c4852, speckle=0.25, scale=10.0)
    L.box("asml-floor", X0 - 12, OY - 1, -0.05, X0 + 12, OY + 40, 0, floor)
    L.box("asml-ceiling", X0 - 12, OY - 1, 5.4, X0 + 12, OY + 40, 5.5, L.mat("ceiling-navy", 0x04060d, 0.9))
    # slat wall (u 1060-1580, top v 527)
    a, b = A(1060, 527, D), A(1580, 527, D)
    wood_slats("asml-slats", a.x, b.x, Yd(D), 0.0, a.z, 10)
    # ASML letters standing on the wall's top on short posts, seen from behind (so they read mirrored)
    lt = A(1461, 480, D + 0.05)
    lh = (480 - 287) * (D + 0.05) / c.f
    letters = L.text("asml-letters", "ASML", lh * 1.38, (lt.x, Yd(D + 0.05), lt.z), (math.pi / 2, 0, math.pi),
                     L.mat("letter-white", 0xf4f6ff, 0.4, emit=0xf0f4ff, strength=9.0), extrude=0.04, font=font)
    letters.data.space_character = 1.0
    for u in (1150, 1240, 1330, 1420, 1520, 1610, 1700, 1790):
        p = A(u, 505, D + 0.05)
        L.box(f"asml-post-{u}", p.x - 0.012, Yd(D + 0.03), a.z, p.x + 0.012, Yd(D + 0.07), lt.z, L.mat("post-white", 0xe6e6e6, 0.5))
    # a white, softly glowing counter in front of the slats (top v ~1060)
    ct, cr = A(1070, 1060, D - 0.9), A(1300, 1060, D - 0.9)
    L.box("asml-counter", ct.x, Yd(D - 0.9), 0, cr.x, Yd(D - 0.3), ct.z, L.mat("counter-glow", 0xf2f4f8, 0.3, emit=0xdfe6ff, strength=0.6))
    L.box("asml-display", ct.x + 0.55, Yd(D - 0.8), ct.z, ct.x + 0.95, Yd(D - 0.45), ct.z + 0.4,
          L.mat("glass", 0xdfe8f0, 0.05, transmission=1.0))
    # right: the plan's column, white, at the frame's edge (u 2140 on), a blue backlit box on the booth beside it
    cx, cy = -3.8, -7.77
    L.box("asml-plan-column", cx - COL / 2, cy - COL / 2, 0, cx + COL / 2, cy + COL / 2, 2.6, ao_paint("col-white-ao", 0xe9e8e6, 0.7))
    L.box("asml-plan-column-top", cx - COL / 2, cy - COL / 2, 2.6, cx + COL / 2, cy + COL / 2, 5.4, L.mat("ceiling-navy", 0x04060d, 0.9))
    dc = cy - COL / 2 - OY
    bl0, bl1 = A(1870, 512, dc + 0.6), A(2140, 434, dc + 0.6)
    L.box("asml-bluebox", bl0.x, Yd(dc + 0.6), bl0.z, bl1.x, Yd(dc + 0.8), bl1.z, L.emissive("blue-box", 0x7aa8ff, 4.0))
    L.box("asml-booth-r", bl0.x - 0.1, Yd(dc + 0.8), 0, cx - COL / 2, Yd(dc + 1.0), 2.6, L.mat("wall-white-neutral", 0xeeeeee, 0.8))
    # left: a white pillar (u 403-510), a booth with a red sign and a poster, a truss over it
    q0, q1 = A(403, 700, 11.0), A(510, 700, 11.0)
    L.box("asml-pillar", q0.x, Yd(11.0), 0, q1.x, Yd(11.0) + (q1.x - q0.x), 5.4, ao_paint("col-white-ao", 0xe9e8e6, 0.7))
    r0, r1 = A(163, 713, 12.0), A(240, 635, 12.0)
    L.box("asml-red-sign", r0.x, Yd(12.0), r0.z, r1.x, Yd(12.1), r1.z, L.emissive("red-sign", 0xe0302a, 3.0))
    p0, p1 = A(0, 1085, 8.0), A(93, 590, 8.0)
    L.box("asml-poster", p0.x - 0.5, Yd(8.0), 0.05, p1.x, Yd(8.05), p1.z, gradient_print("print-red", 0x8a2a24, 0xd04a3a, 0xe8d0c0, 0.8))
    L.box("asml-booth-l", p0.x - 1.5, Yd(13.0), 0, q0.x - 0.1, Yd(13.1), 1.9, navy)
    t0, t1 = A(0, 330, 9.0), A(390, 500, 9.0)
    truss("asml-truss", (t0.x - 1.0, Yd(9.0), t0.z + 0.2), (t1.x, Yd(9.0), t1.z), 0.3,
          L.mat("truss-alu", 0xc8cacc, 0.3, metal=1.0))
    for k, u in enumerate((110, 170, 240, 300, 370)):
        p = A(u, 600, 12.5)
        L.sphere(f"asml-spot{k}", (p.x, Yd(12.5), p.z), 0.015, L.emissive("spot-hot", 0xfff6e8, 60.0))
    # ceiling: spiral ducts, an aluminium dome pendant, track spots; top right the white lowered ceiling of the
    # room's central zone (3.0 m, as in the hollywood set), its edge at u ~1395
    metal = spiral_duct("duct")
    d0, d1 = A(0, 58, 22.0), A(990, 58, 22.0)
    duct("asml-duct1", (d0.x - 2, Yd(22.0), d0.z), (d1.x, Yd(22.0), d1.z), 0.6, metal)
    e0, e1 = A(495, 260, 20.0), A(990, 260, 20.0)
    duct("asml-duct2", (e0.x, Yd(20.0), e0.z), (e1.x, Yd(20.0), e1.z), 0.4, metal)
    f0, f1 = A(1750, 120, 18.0), A(2480, 300, 14.0)
    duct("asml-duct3", (f0.x, Yd(18.0), f0.z), (f1.x + 1.0, Yd(13.0), f1.z - 0.2), 0.55, metal)
    pl = A(1117, 248, 16.0)
    pendant("asml-pend", pl.x, Yd(16.0), pl.z, 0.55, 0.35, L.mat("alu-shade", 0xc4c6c8, 0.28, metal=1.0),
            L.emissive("bulb-warm", 0xfff1dd, 30.0), light_power=150)
    for k, (u, v) in enumerate([(852, 112), (915, 155), (925, 263)]):
        p = A(u, v, 17.0)
        L.sphere(f"asml-tspot{k}", (p.x, Yd(17.0), p.z), 0.02, L.emissive("spot-hot", 0xfff6e8, 60.0))
    dw = (3.0 - H) * c.f / (780 - 200)                        # depth where v 200 meets the 3.0 m ceiling
    w0 = A(1395, 200, dw)
    L.box("asml-white-ceiling", w0.x, Yd(dw), 3.0, w0.x + 14.0, Yd(dw) + 20.0, 3.2,
          L.mat("coffer-white", 0xf0f2f6, 0.6, emit=0xdde6ff, strength=0.8))
    L.area_light("asml-white-ceiling-light", (w0.x + 2.0, Yd(dw) + 3.0, 2.9), 4.0, 900, color=(0.85, 0.9, 1.0),
                 size_y=4.0, rot=(math.pi, 0, 0))
    # strips under the black ceiling: the silver streak along the tops of the ducts
    for k, dy in enumerate((15.0, 19.0, 23.0)):
        L.area_light(f"asml-duct-strip{k}", (X0 - 1.0, Yd(dy), 5.3), 10.0, 220, color=(1.0, 0.98, 0.95), size_y=0.4)
    # the far side of the hall, dark navy booth walls under the black ceiling
    L.box("asml-far-wall", X0 - 12, Yd(32.0), 0, X0 + 12, Yd(32.3), 3.8, L.mat("far-wall", 0x141c38, 0.8))
    for k, (x, w, col) in enumerate([(-4.0, 1.6, 0x1e3a78), (-2.2, 1.2, 0x8a8e98), (-6.5, 2.0, 0x7a2a2a)]):
        L.box(f"asml-far-booth{k}", X0 + x, Yd(26.0), 0, X0 + x + w, Yd(26.4), 2.6, L.mat(f"far-booth{k}", col, 0.7))
    L.area_light("asml-far-light", (X0 - 2, Yd(27.0), 3.7), 12.0, 220, color=(0.75, 0.85, 1.0), size_y=8.0)
    # foreground: the dark navy demo console with a tablet on a stand (bottom of the frame)
    k0, k1 = A(465, 1540, 3.2), A(1900, 1540, 3.2)
    L.box("asml-console", k0.x, Yd(3.2), 0, k1.x, Yd(3.9), k0.z, L.mat("console-navy", 0x141a2e, 0.5))
    s0, s1 = A(1000, 1450, 3.4), A(1190, 1180, 3.4)
    L.box("asml-tablet", s0.x, Yd(3.4), k0.z, s1.x, Yd(3.42), s1.z, L.mat("tablet-black", 0x0a0a0c, 0.2, coat=0.5))
    # light: dim blue overhead, a warm spot on the slats, a cool light on the column
    L.area_light("asml-key", (X0, Yd(9.0), 5.0), 10.0, 260, color=(0.6, 0.72, 1.0), size_y=10.0)
    L.area_light("asml-front", (X0, Yd(1.0), 3.5), 4.0, 120, color=(0.6, 0.72, 1.0),
                 rot=(math.radians(75), 0, 0), size_y=2.0)
    L.spot("asml-slat-spot", (X0 + 0.3, Yd(D - 3.0), 3.8), (a.x + 0.4, Yd(D), 1.6), 700, angle_deg=35, blend=0.5,
           color=(1.0, 0.78, 0.55), radius=0.1)
    L.area_light("asml-column-light", (cx - 2.0, cy - 3.0, 3.0), 1.5, 500, color=(1.0, 1.0, 1.0),
                 rot=(math.radians(60), 0, math.radians(-35)))


# ---------------------------------------------------------------------------------- build
def build(root):
    global ROOT
    ROOT = Path(root)
    build_aisle()
    build_robot()
    build_asml()
    L.world_color(0x0c0c10, 0.6)


def before_render(name):
    scene = bpy.context.scene
    cobj = scene.camera
    vs = scene.view_settings
    ev, kelvin, tint = GRADE.get(name, (0.0, 6500, 0))
    vs.exposure = ev
    try:
        vs.look = LOOKS.get(name, LOOK)
    except TypeError:
        pass
    if hasattr(vs, "use_white_balance"):
        vs.use_white_balance = True
        vs.white_balance_temperature = kelvin
        vs.white_balance_tint = tint
    if name in DOF and scene.render.engine == "CYCLES":
        dist, fstop = DOF[name]
        cobj.data.dof.use_dof = True
        cobj.data.dof.focus_distance = dist
        cobj.data.dof.aperture_fstop = fstop
