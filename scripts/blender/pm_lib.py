"""Building blocks for the photo-matched areas (scripts/blender/pm_areas/*.py): materials, boxes, extrusions,
lights. Metres, z up. Every helper returns the object it made so an area can move or tag it."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

MATS = {}


def srgb(h):
    """0xRRGGBB (sRGB) -> linear RGBA"""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin((h >> 16) & 255), lin((h >> 8) & 255), lin(h & 255), 1.0)


def mat(name, color=0x808080, rough=0.8, metal=0.0, emit=None, strength=0.0, alpha=1.0, transmission=0.0,
        coat=0.0, bump=0.0, bump_scale=200.0, ior=1.45, spec=0.5):
    """Principled material, cached by name. color/emit as 0xRRGGBB (sRGB)."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["IOR"].default_value = ior
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        b.inputs["Emission Color"].default_value = srgb(emit)
        b.inputs["Emission Strength"].default_value = strength
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if bump:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        nt.links.new(tex.outputs["Fac"], bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = srgb(color)                       # Workbench / solid view colour
    MATS[name] = m
    return m


def emissive(name, color, strength):
    """pure light (screens, LED strips, light boxes)"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = srgb(color)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    m.diffuse_color = srgb(color)
    MATS[name] = m
    return m


def image_mat(name, path, strength=0.0, rough=0.6, emit_only=False):
    """a picture on a surface by its UVs (posters, screens): emit_only for screens"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(path), check_existing=True)
    out = nt.nodes["Material Output"]
    if emit_only:
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Strength"].default_value = strength
        nt.links.new(t.outputs["Color"], e.inputs["Color"])
        nt.links.new(e.outputs[0], out.inputs["Surface"])
    else:
        b = nt.nodes["Principled BSDF"]
        b.inputs["Roughness"].default_value = rough
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if strength:
            nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = strength
    MATS[name] = m
    return m


def _link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def mesh_obj(name, verts, faces, material=None, coll=None, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if uvs is not None:
        layer = me.uv_layers.new()
        for poly in me.polygons:
            for li in poly.loop_indices:
                layer.data[li].uv = uvs[me.loops[li].vertex_index]
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if material:
        me.materials.append(material)
    return _link(ob, coll)


def box(name, x0, y0, z0, x1, y1, z1, material=None, coll=None, bevel=0.0):
    """axis-aligned box between two corners"""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, material, coll)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 2, "ANGLE"
    return ob


def prism(name, outline, z0, z1, material=None, coll=None, bevel=0.0):
    """extrude a 2D outline (list of (x, y), counter-clockwise) from z0 to z1"""
    n = len(outline)
    v = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    ob = mesh_obj(name, v, f, material, coll)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 2, "ANGLE"
    return ob


def extrude_section(name, section, path_a, path_b, material=None, coll=None):
    """a straight member: a closed 2D section (in the plane across the member: (u, v) with v up) swept from
    point path_a to path_b"""
    a, b = Vector(path_a), Vector(path_b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    w = u.cross(d).normalized()
    n = len(section)
    v = [a + u * s + w * t for s, t in section] + [b + u * s + w * t for s, t in section]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    return mesh_obj(name, v, f, material, coll)


def quad(name, corners, material=None, coll=None, uv=True):
    """a single face through four corners (counter-clockwise seen from the front), UVs 0..1"""
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)] if uv else None
    return mesh_obj(name, corners, [(0, 1, 2, 3)], material, coll, uvs=uvs)


def cylinder(name, x, y, z0, z1, r, material=None, coll=None, segs=24, r_top=None):
    rt = r if r_top is None else r_top
    v = [(x + r * math.cos(2 * math.pi * i / segs), y + r * math.sin(2 * math.pi * i / segs), z0) for i in range(segs)]
    v += [(x + rt * math.cos(2 * math.pi * i / segs), y + rt * math.sin(2 * math.pi * i / segs), z1) for i in range(segs)]
    f = [tuple(range(segs - 1, -1, -1)), tuple(range(segs, 2 * segs))]
    f += [(i, (i + 1) % segs, segs + (i + 1) % segs, segs + i) for i in range(segs)]
    ob = mesh_obj(name, v, f, material, coll)
    for p in ob.data.polygons[2:]:
        p.use_smooth = True
    return ob


def tube(name, a, b, r, material=None, coll=None, segs=16):
    """a cylinder between two arbitrary points"""
    sec = [(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
    ob = extrude_section(name, sec, a, b, material, coll)
    for p in ob.data.polygons[2:]:
        p.use_smooth = True
    return ob


def sphere(name, loc, r, material=None, coll=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if material:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    return _link(ob, coll)


def text(name, body, size, loc, rot, material, extrude=0.01, font=None, align="CENTER", coll=None):
    """upright text: rot (rx, ry, rz) in radians; (pi/2, 0, 0) faces -y. Size = cap height-ish in metres."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "BOTTOM"
    if font:
        cu.font = bpy.data.fonts.load(str(font), check_existing=True)
    ob = bpy.data.objects.new(name, cu)
    ob.location, ob.rotation_euler = loc, rot
    cu.materials.append(material)
    return _link(ob, coll)


def area_light(name, loc, size, power, color=(1, 1, 1), rot=(0, 0, 0), size_y=None, shape="RECTANGLE", spread=None):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.color, li.shape = power, color, shape
    li.size = size
    li.size_y = size_y if size_y is not None else size
    if spread is not None:
        li.spread = spread
    ob = bpy.data.objects.new(name, li)
    ob.location, ob.rotation_euler = loc, rot
    return _link(ob)


def spot(name, loc, target, power, angle_deg=30, blend=0.3, color=(1, 1, 1), radius=0.05):
    li = bpy.data.lights.new(name, "SPOT")
    li.energy, li.color, li.spot_size, li.spot_blend = power, color, math.radians(angle_deg), blend
    li.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return _link(ob)


def point(name, loc, power, color=(1, 1, 1), radius=0.1):
    li = bpy.data.lights.new(name, "POINT")
    li.energy, li.color, li.shadow_soft_size = power, color, radius
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    return _link(ob)


def sun(name, direction, strength, color=(1, 1, 1), angle_deg=0.6):
    li = bpy.data.lights.new(name, "SUN")
    li.energy, li.color, li.angle = strength, color, math.radians(angle_deg)
    ob = bpy.data.objects.new(name, li)
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return _link(ob)


def world_color(color, strength):
    w = bpy.data.worlds.new("world") if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = srgb(color)
    bg.inputs["Strength"].default_value = strength
    return w


def world_sky(strength=1.0, sun_elevation=40, sun_rotation=0, hdri=None):
    """daylight: an HDRI if given, else Blender's sky texture"""
    w = bpy.context.scene.world or bpy.data.worlds.new("world")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if hdri:
        t = nt.nodes.new("ShaderNodeTexEnvironment")
        t.image = bpy.data.images.load(str(hdri), check_existing=True)
        coord, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(sun_rotation))
        nt.links.new(coord.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        nt.links.new(t.outputs["Color"], bg.inputs["Color"])
    else:
        sky = nt.nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "NISHITA"
        except TypeError:
            pass
        if hasattr(sky, "sun_elevation"):
            sky.sun_elevation = math.radians(sun_elevation)
            sky.sun_rotation = math.radians(sun_rotation)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return w


def array(objs, offset, count):
    """linked copies of objects, stepped by offset (x, y, z)"""
    made = []
    for i in range(1, count):
        for o in objs:
            c = o.copy()
            c.location = Vector(o.location) + Vector(offset) * i
            for coll in o.users_collection:
                coll.objects.link(c)
            made.append(c)
    return made


def copy_at(obj, loc=None, rot_z=None, coll=None):
    c = obj.copy()
    if loc is not None:
        c.location = loc
    if rot_z is not None:
        c.rotation_euler = (c.rotation_euler[0], c.rotation_euler[1], rot_z)
    for col in (obj.users_collection if coll is None else [coll]):
        col.objects.link(c)
    return c


def join(name, objs):
    """merge meshes into one object (fewer objects, faster scene build)"""
    objs = [o for o in objs if o.type == "MESH"]
    if not objs:
        return None
    ctx = {"active_object": objs[0], "selected_editable_objects": objs, "selected_objects": objs}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]
