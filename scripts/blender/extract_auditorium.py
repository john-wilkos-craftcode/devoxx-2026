"""Cut one auditorium out of a saved old-scene file (scripts/blender/save_rooms.sh -> kino-room-<n>.blend) into a small
.blend the photo-matched venue appends (pm_areas/auditoriums.py), so the room walks end in exactly the seats of the
published stills. The old builder merges objects by material across the whole venue, so this works face by face: every
face whose centre lies inside room n (venue.json's aud-<n> and its stage, west of the corridor wall or east of it) is
kept, per object; people seated there are frozen as posed in the file; the room's lights come along.

  blender -b kino-room-<n>.blend --python extract_auditorium.py -- --root <repo> --room <n> --out <dir>
Writes <dir>/aud-<n>.blend.
"""
import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--room", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args(argv)

FH = 6.2
venue = json.loads((Path(a.root) / "data" / "venue" / "venue.json").read_text())["venue"]
rooms = {r["id"]: r["bounds"] for r in venue["rooms"]}
b = rooms[f"aud-{a.room}"]
x0, x1, y0, y1 = b["x"], b["x"] + b["w"], b["y"], b["y"] + b["h"]
WEST = x1 <= -7.0
# inside the room, clear of the corridor's wall line (the venue's upstairs builds the corridor side itself)
xa, xb = (x0 - 0.5, -7.2) if WEST else (12.7, x1 + 0.5)


rake = next(ln for ln in venue["links"] if ln["id"] == f"rake-{a.room}")
rb = rake["bounds"]


def floor_z(x):
    """the auditorium's raked floor at x (venue.json's rake link; flat stage beyond it, floor 1 at the door end)"""
    u = min(1.0, max(0.0, (x - rb["x"]) / rb["w"]))
    u = u if rake["ascending"] else 1 - u
    return FH + rake["base"] + rake["rise"] * u


def inside(p):
    """in the room and above its floor: the hall below the room's footprint stays out"""
    return xa < p.x < xb and y0 - 0.05 < p.y < y1 + 0.05 and floor_z(p.x) - 0.3 < p.z < FH + 12.0


dg = bpy.context.evaluated_depsgraph_get()
keep = []
for ob in list(bpy.context.scene.objects):
    if ob.type == "LIGHT" and inside(ob.matrix_world.translation) and not ob.hide_render:
        keep.append(ob)
# every evaluated instance: plain meshes, instanced seats (collection / geometry-node instances), text and curves;
# instances of the same source are joined into one mesh per source
groups = {}
for inst in dg.object_instances:
    ob = inst.object
    if ob.type not in ("MESH", "CURVE", "FONT", "SURFACE"):
        continue
    src = ob.original
    if not inst.is_instance and (src.hide_render or any(c.hide_render for c in src.users_collection)):
        continue                                  # (instances render even when their template is hidden)
    M = inst.matrix_world.copy()
    corners = [M @ Vector(c) for c in ob.bound_box]
    lo = Vector([min(v[i] for v in corners) for i in range(3)])
    hi = Vector([max(v[i] for v in corners) for i in range(3)])
    if hi.x < xa or lo.x > xb or hi.y < y0 or lo.y > y1:
        continue
    try:
        me = ob.to_mesh()
    except RuntimeError:
        continue
    if me is None or not me.polygons:
        ob.to_mesh_clear()
        continue
    bm = bmesh.new()
    bm.from_mesh(me)
    mats = [sl.material for sl in src.material_slots] or [m for m in me.materials]   # the original holds the real slots
    ob.to_mesh_clear()
    bm.transform(M)
    # slice big faces (a ceiling spanning several rooms) at the room's walls first, so the part over the room stays
    for co, no in (((xa, 0, 0), (1, 0, 0)), ((xb, 0, 0), (1, 0, 0)), ((0, y0, 0), (0, 1, 0)), ((0, y1, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    gone = [f for f in bm.faces if not inside(f.calc_center_median())]
    if len(gone) == len(bm.faces):
        bm.free()
        continue
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    key = src.name + "|" + ",".join(m.name if m else "-" for m in mats)   # one mesh per source and material set
    g = groups.setdefault(key, {"bm": bmesh.new(), "mats": mats, "cam": src.visible_camera, "shadow": src.visible_shadow})
    tmp = bpy.data.meshes.new("tmp")
    bm.to_mesh(tmp)
    bm.free()
    g["bm"].from_mesh(tmp)                       # appends the faces (material indices kept: same source, same slots)
    bpy.data.meshes.remove(tmp)
for key, g in groups.items():
    key = key.split("|")[0]
    new = bpy.data.meshes.new(f"aud{a.room}-{key}")
    g["bm"].to_mesh(new)
    g["bm"].free()
    for m in g["mats"]:
        new.materials.append(m)
    nob = bpy.data.objects.new(f"aud{a.room}-{key}", new)
    bpy.context.scene.collection.objects.link(nob)
    nob.visible_camera, nob.visible_shadow = g["cam"], g["shadow"]
    keep.append(nob)
out = Path(a.out) / f"aud-{a.room}.blend"
bpy.data.libraries.write(str(out), set(keep), fake_user=True, compress=True)
print(f"AUD {a.room}: {sum(1 for o in keep if o.type == 'MESH')} meshes, "
      f"{sum(len(o.data.polygons) for o in keep if o.type == 'MESH')} faces, "
      f"{sum(1 for o in keep if o.type == 'LIGHT')} lights -> {out}", flush=True)
