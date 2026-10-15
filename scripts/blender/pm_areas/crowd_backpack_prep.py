"""Prepare the crowd's backpack once from the "Oakley Kitchen Sink Backpack Model" by qkuslic1 (CC BY 4.0,
data/models/backpack_oakley/backpack_oakley.glb; credit in data/venue/THIRD_PARTY.md):

- the shoulder straps, their buckles and the lower strap clips are removed: they are posed for a pack lying on a
  table (every loose part that reaches more than 6.5 cm behind the back panel goes), so the pack sits flush on
  the back with no strap ends floating;
- decimated from ~54k to ~8k faces, its own PBR textures kept (packed into the .blend);
- metres, Z up, the back panel facing -Y with the origin at its centre, scaled to a real pack: 32 cm wide,
  20 cm deep, 48 cm tall.

  scripts/photomatch/render.sh crowd_backpack_prep      (writes data/models/backpack_oakley/backpack_crowd.blend)
"""
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

SIZE = (0.32, 0.20, 0.48)
BEHIND = 6.5                     # cm behind the back panel: anything reaching further is a strap or its hardware
FACES = 8000


def build(root, unified=False):
    root = Path(root)
    src = root / "data" / "models" / "backpack_oakley" / "backpack_oakley.glb"
    out = root / "data" / "models" / "backpack_oakley" / "backpack_crowd.blend"
    bpy.ops.import_scene.gltf(filepath=str(src))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # one mesh in world space (centimetres), the three materials kept
    bm = bmesh.new()
    mats = []
    for o in meshes:
        b2 = bmesh.new()
        b2.from_mesh(o.data)
        b2.transform(o.matrix_world)
        off = len(mats)
        mats += list(o.data.materials)
        for f in b2.faces:
            f.material_index += off
        me = bpy.data.meshes.new("tmp")
        b2.to_mesh(me)
        b2.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    # drop the straps: loose parts reaching more than BEHIND cm behind the back panel (the panel sits near y = 0)
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    seen, parts = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index)
                    stack.append(y)
        parts.append(comp)
    straps = [comp for comp in parts if min(v.co.y for v in comp) < -BEHIND]
    gone = [v for comp in straps for v in comp]
    print(f"PREP removing {len(gone)} strap vertices in {len(straps)} of {len(parts)} parts", flush=True)
    bmesh.ops.delete(bm, geom=gone, context="VERTS")
    me = bpy.data.meshes.new("backpack_crowd")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    ob = bpy.data.objects.new("backpack_crowd", me)
    bpy.context.scene.collection.objects.link(ob)
    # decimate
    n0 = len(me.polygons)
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, FACES / max(1, n0))
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier="decimate")
    # metres, origin at the back panel's centre, real size
    co = [v.co.copy() for v in me.vertices]
    mn = Vector([min(c[i] for c in co) for i in range(3)])
    mx = Vector([max(c[i] for c in co) for i in range(3)])
    size = mx - mn
    S = Matrix.Diagonal((SIZE[0] / size.x, SIZE[1] / size.y, SIZE[2] / size.z, 1))
    T = Matrix.Translation(-Vector(((mn.x + mx.x) / 2, mn.y, (mn.z + mx.z) / 2)))
    me.transform(S @ T)
    for p in me.polygons:
        p.use_smooth = True
    print(f"PREP {n0} -> {len(me.polygons)} faces; source box {size.x:.1f} x {size.y:.1f} x {size.z:.1f} cm, "
          f"scaled {S[0][0]:.3f} {S[1][1]:.3f} {S[2][2]:.3f}", flush=True)
    for img in bpy.data.images:
        if img.has_data or img.packed_file is None:
            try:
                img.pack()
            except RuntimeError:
                pass
    ob.use_fake_user = True
    bpy.data.libraries.write(str(out), {ob}, fake_user=True, compress=True)
    print(f"PREP wrote {out}", flush=True)
    # a turntable of the result for checking
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type, sc.display.shading.light = "TEXTURE", "STUDIO"
    sc.render.resolution_x = sc.render.resolution_y = 500
    cd = bpy.data.cameras.new("c")
    cd.type, cd.ortho_scale = "ORTHO", 0.7
    c = bpy.data.objects.new("c", cd)
    sc.collection.objects.link(c)
    sc.camera = c
    outdir = Path("C:/Users/wilkojo/kino-renders/photomatch/crowd/backpack")
    outdir.mkdir(parents=True, exist_ok=True)
    for name, loc in (("side", (3, 0.1, 0.0)), ("front", (0, 3, 0.0)), ("back", (0, -3, 0.0)), ("top", (0, 0.1, 3))):
        c.location = loc
        c.rotation_euler = (Vector((0, 0.1, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(outdir / f"prep-{name}.png")
        bpy.ops.render.render(write_still=True)
    sys.exit(0)
