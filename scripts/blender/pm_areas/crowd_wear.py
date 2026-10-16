"""What the crowd wears on top of the Rocketbox avatars: a badge on a lanyard (everyone with a badge) and a
backpack (about a third), made clip-proof the layered way:

1. Skinned to the wearer's own armature: weights copied from the avatar's body (nearest face, interpolated),
   then restricted and smoothed: the pack to Spine / Spine1 / Spine2 (it bends with the torso), the lanyard cord
   to the neck, both clavicles and Spine2, the badge card 100% Spine2 (rigid and flat).
2. A Shrinkwrap after the Armature modifier (nearest surface point, outside surface): the lanyard cord on the
   shirt and neck at 4 mm, the pack's back panel (a "contact" vertex group) on the back at 6 mm, so on every frame
   nothing sinks in and nothing floats. The target is an invisible, unmasked copy of the body (a "proxy").
3. On backpack wearers only, a Mask modifier (inverted vertex group "under_pack") hides the patch of back, and of
   hair, that the pack's back panel covers.
4. verify() measures every wearer on 12 frames with the evaluated, deformed meshes: penetration of the pack, the
   cord and the badge into the body (arms included) and of the body into them, and how far the pack's back panel
   floats off the back. A badge an arm passes through is lifted or brought forward a little; if no small move
   clears it, that person gets no badge and no lanyard.

The backpack is "Oakley Kitchen Sink Backpack Model" by qkuslic1 (CC BY 4.0), prepared by crowd_backpack_prep.py.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

PACK_ALLOWED = ("Bip01 Spine2", "Bip01 Spine1", "Bip01 Spine")
CORD_ALLOWED = ("Bip01 Neck", "Bip01 L Clavicle", "Bip01 R Clavicle", "Bip01 Spine2")
TINTS = {"black": None, "charcoal": (0.10, 0.10, 0.11), "navy": (0.025, 0.045, 0.12), "olive": (0.07, 0.08, 0.035)}
REPORT = []
PACK_WIDTH = 0.9              # narrower than the model: its sides cut into hanging upper arms (16/10 critic)
NEAR_WRAP = 6.0               # m from the camera path: nearer people's accessories hug the body (Shrinkwrap), others
                              # just follow the skeleton (camera-priority rule; each Shrinkwrap re-runs every blur step)
MASK_UNDER_PACK = False        # the mask's hole showed round the pack's edges in the 15/10 close-ups: off until refitted


# ---------------------------------------------------------------------------------- weights
def body_tree_rest(body):
    me, Mw = body.data, body.matrix_world
    verts = [Mw @ v.co for v in me.vertices]
    return BVHTree.FromPolygons(verts, [p.vertices[:] for p in me.polygons]), verts


def transfer_weights(body, tree, bverts, points, allowed):
    """weights for points (world, rest) from the body's nearest face, interpolated by inverse distance to its
    corners, restricted to the allowed groups and renormalised"""
    me = body.data
    names = {g.index: g.name for g in body.vertex_groups}
    out = []
    for p in points:
        loc, n, fi, d = tree.find_nearest(p)
        acc = {}
        if fi is not None:
            poly = me.polygons[fi]
            ws = [1.0 / max(1e-4, (bverts[vi] - loc).length) for vi in poly.vertices]
            tot = sum(ws)
            for vi, w in zip(poly.vertices, ws):
                for g in me.vertices[vi].groups:
                    name = names.get(g.group)
                    if name in allowed:
                        acc[name] = acc.get(name, 0.0) + g.weight * w / tot
        s = sum(acc.values())
        out.append({k: v / s for k, v in acc.items()} if s > 1e-6 else {allowed[0]: 1.0})
    return out


def set_groups(ob, weights, extra=None):
    groups = {}
    for i, w in enumerate(weights):
        for name, v in w.items():
            if name not in groups:
                groups[name] = ob.vertex_groups.new(name=name)
            groups[name].add([i], v, "REPLACE")
    for name, vals in (extra or {}).items():
        g = ob.vertex_groups.new(name=name)
        for i, v in enumerate(vals):
            if v > 0:
                g.add([i], v, "REPLACE")


# ---------------------------------------------------------------------------------- rest geometry per avatar
def rest_frame(tmpl):
    """the rest-pose landmarks of an avatar (world, avatar at the origin facing -Y): neck, back surface on the
    spine line, shoulder height, chest front"""
    if "rest" in tmpl:
        return tmpl["rest"]
    rig, body = tmpl["rig"], tmpl["meshes"][0]
    W = rig.matrix_world
    tree, bverts = body_tree_rest(body)
    v = np.array([tuple(x) for x in bverts])
    neck = W @ rig.data.bones["Bip01 Neck"].head_local
    head = W @ rig.data.bones["Bip01 Head"].head_local
    m = (np.abs(v[:, 0] - 0.13) < 0.03) & (np.abs(v[:, 1] - neck.y) < 0.06) & (v[:, 2] < neck.z) & (v[:, 2] > neck.z - 0.15)
    sh_z = float(v[m][:, 2].max()) if m.any() else neck.z - 0.05
    tmpl["rest"] = {"tree": tree, "bverts": bverts, "v": v, "neck": neck, "head": head, "sh_z": sh_z, "W": W}
    return tmpl["rest"]


def project(R, p, off):
    """nearest point on the avatar's rest surface, pushed out off along the normal"""
    loc, n, fi, d = R["tree"].find_nearest(p)
    return loc + n * off


# ---------------------------------------------------------------------------------- the lanyard
def cord_points(R, badge_top_l, badge_top_r):
    """a loop from one top corner of the badge up the chest, over the collarbone, round the back of the neck and
    down the other side, every point on the rest surface 4 mm out"""
    neck, sh_z = R["neck"], R["sh_z"]
    base_z = sh_z + 0.01
    guides = []
    for s, top in ((-1, badge_top_l), (1, badge_top_r)):
        side = [top + Vector((0, -0.002, 0)),
                Vector((s * 0.042, top.y, (top.z + base_z - 0.05) / 2)),
                Vector((s * 0.058, neck.y - 0.07, base_z - 0.045)),
                Vector((s * 0.068, neck.y - 0.03, base_z - 0.005)),
                Vector((s * 0.066, neck.y + 0.02, base_z + 0.012)),
                Vector((s * 0.035, neck.y + 0.06, base_z + 0.018))]
        guides.append(side)
    left, right = guides
    path = left + [Vector((0.0, neck.y + 0.07, base_z + 0.02))] + list(reversed(right))
    dense = []
    for a, b in zip(path, path[1:]):
        for t in np.linspace(0, 1, 6, endpoint=False):
            dense.append(a.lerp(b, float(t)))
    dense.append(path[-1])
    pts = [dense[0]] + [project(R, p, 0.004) for p in dense[1:-1]] + [dense[-1]]
    for _ in range(3):                                  # smooth the projected path, keep the ends
        pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        pts = [pts[0]] + [project(R, p, 0.004) for p in pts[1:-1]] + [pts[-1]]
    return pts


def ribbon(points, R, width=0.014):
    verts, faces = [], []
    n = len(points)
    for k, p in enumerate(points):
        t = (points[min(k + 1, n - 1)] - points[max(k - 1, 0)]).normalized()
        loc, nrm, fi, d = R["tree"].find_nearest(p)
        w = t.cross(nrm)
        w = w.normalized() * (width / 2) if w.length > 1e-6 else Vector((width / 2, 0, 0))
        verts += [p - w, p + w]
    for k in range(n - 1):
        faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    return verts, faces


# ---------------------------------------------------------------------------------- the backpack
def load_pack(root):
    path = Path(root) / "data" / "models" / "backpack_oakley" / "backpack_crowd.blend"
    with bpy.data.libraries.load(str(path)) as (src, dst):
        dst.objects = ["backpack_crowd"]
    return dst.objects[0]


def tint_materials(base_mats):
    """per tint, copies of the pack's materials with the colour lifted towards the tint by the texture's own
    brightness (so its detail stays)"""
    out = {}
    for tname, tint in TINTS.items():
        mats = []
        for m in base_mats:
            if tint is None:
                mats.append(m)
                continue
            c = m.copy()
            c.name = f"{m.name}-{tname}"
            nt = c.node_tree
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            link = next((l for l in nt.links if l.to_socket == bsdf.inputs["Base Color"]), None)
            if link:
                src = link.from_socket
                lum = nt.nodes.new("ShaderNodeRGBToBW")
                nt.links.new(src, lum.inputs[0])
                scale = nt.nodes.new("ShaderNodeMath")
                scale.operation = "MULTIPLY_ADD"
                scale.inputs[1].default_value, scale.inputs[2].default_value = 4.0, 0.6
                nt.links.new(lum.outputs[0], scale.inputs[0])
                tcol = nt.nodes.new("ShaderNodeMix")
                tcol.data_type, tcol.blend_type = "RGBA", "MULTIPLY"
                tcol.inputs["Factor"].default_value = 1.0
                tcol.inputs[6].default_value = (*tint, 1)
                nt.links.new(scale.outputs[0], tcol.inputs[7])
                add = nt.nodes.new("ShaderNodeMix")
                add.data_type, add.blend_type = "RGBA", "ADD"
                add.inputs["Factor"].default_value = 1.0
                nt.links.new(src, add.inputs[6])
                nt.links.new(tcol.outputs[2], add.inputs[7])
                nt.links.new(add.outputs[2], bsdf.inputs["Base Color"])
            mats.append(c)
        out[tname] = mats
    return out


def pack_mesh_for(tmpl, base, crowd):
    """the pack's mesh for this avatar: its place on the back at rest, weights from the body (pack groups only,
    smoothed by height), the contact group of the back panel, and the avatar's under_pack mask group"""
    if "pack_mesh" in tmpl:
        return tmpl["pack_mesh"], tmpl["pack_rest"]
    R = rest_frame(tmpl)
    v = R["v"]
    # the back's surface on the spine line at the shoulder blades (a percentile: hair and hoods don't count)
    top = R["sh_z"] - 0.035
    zc = top - 0.24
    sel = v[(np.abs(v[:, 0]) < 0.06) & (np.abs(v[:, 2] - (zc + 0.08)) < 0.08) & (v[:, 1] > R["neck"].y)]
    back_y = float(np.percentile(sel[:, 1], 75)) if len(sel) else float(R["neck"].y + 0.12)
    rest = Matrix.Translation((0.0, back_y + 0.004, zc))
    me = base.data.copy()
    me.name = f"crowd-pack-{tmpl['name']}"
    pts = [rest @ x.co for x in me.vertices]
    body = tmpl["meshes"][0]
    w = transfer_weights(body, R["tree"], R["bverts"], pts, PACK_ALLOWED)
    # a rigid pack: blend towards Spine2 at the top, Spine1/Spine lower down (smooth by height)
    zs = [p.z for p in pts]
    z0, z1 = min(zs), max(zs)
    sm = []
    for p, wt in zip(pts, w):
        t = (p.z - z0) / max(1e-6, z1 - z0)
        s2 = 0.35 + 0.65 * t
        rest_w = {"Bip01 Spine2": s2, "Bip01 Spine1": (1 - s2) * 0.7, "Bip01 Spine": (1 - s2) * 0.3}
        sm.append({k: 0.75 * rest_w.get(k, 0) + 0.25 * wt.get(k, 0) for k in PACK_ALLOWED})
    # the back panel touching the back: the first 3.5 cm of depth, fading out to the panel's edges
    contact = []
    for x in me.vertices:
        c = x.co
        depth = max(0.0, 1.0 - c.y / 0.035)
        edge = max(0.0, min(1.0, (0.15 - abs(c.x)) / 0.03)) * max(0.0, min(1.0, (0.22 - abs(c.z)) / 0.03))
        contact.append(depth * edge)
    tmp = bpy.data.objects.new("tmp", me)
    set_groups(tmp, sm, {"contact": contact})
    bpy.data.objects.remove(tmp)
    # the body under the pack's back panel (and hair hanging there), for the wearer's Mask modifier
    if "under_pack" not in body.vertex_groups:
        g = body.vertex_groups.new(name="under_pack")
        Mw = body.matrix_world
        idx = []
        for x in body.data.vertices:
            p = Mw @ x.co
            if (abs(p.x) < 0.125 and zc - 0.20 < p.z < zc + 0.20 and p.y > R["neck"].y + 0.02
                    and p.y < back_y + 0.06):
                idx.append(x.index)
        g.add(idx, 1.0, "REPLACE")
    tmpl["pack_mesh"], tmpl["pack_rest"] = me, rest
    return me, rest


# ---------------------------------------------------------------------------------- dressing people
def proxy_for(p, coll):
    """the Shrinkwrap target: the body itself while nothing masks it, else an invisible, unmasked copy (a second
    skinned body per person made a crowd clip render at ~1 min a frame, 16/10)"""
    if p.get("proxy"):
        return p["proxy"]
    if not MASK_UNDER_PACK:
        p["proxy"] = p["body"][0]
        return p["proxy"]
    src = p["body"][0]
    ob = src.copy()
    ob.name = f"{p['name']}-proxy"
    ob.modifiers.clear()
    coll.objects.link(ob)
    ob.parent = p["rig"]
    ob.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    ob.matrix_basis = src.matrix_basis.copy()
    m = ob.modifiers.new("armature", "ARMATURE")
    m.object = p["rig"]
    for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter", "visible_shadow"):
        setattr(ob, attr, False)
    p["proxy"] = ob
    return ob


def wear(p, me, rest_world, name, coll, wrap=None, offset=0.004, group=None, materials=None):
    """an item skinned to the person's rig (armature modifier) with a shrinkwrap after it"""
    rig = p["rig"]
    ob = bpy.data.objects.new(f"{p['name']}-{name}", me)
    coll.objects.link(ob)
    ob.parent = rig
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = p["tmpl"]["rig"].matrix_world.inverted() @ rest_world
    arm = ob.modifiers.new("armature", "ARMATURE")
    arm.object = rig
    if wrap is not None:
        sw = ob.modifiers.new("shrinkwrap", "SHRINKWRAP")
        sw.target, sw.wrap_method, sw.wrap_mode, sw.offset = wrap, "NEAREST_SURFACEPOINT", "OUTSIDE_SURFACE", offset
        if group:
            sw.vertex_group = group
    if materials:
        for i, m in enumerate(materials):
            if i < len(ob.material_slots):
                ob.material_slots[i].link = "OBJECT"
                ob.material_slots[i].material = m
    return ob


def dress(crowd, root):
    """badges and lanyards on everyone who drew one, backpacks on a third, then the measurements"""
    coll = crowd.coll
    base = load_pack(root)
    pack_mats = tint_materials(list(base.data.materials))
    for p in crowd.people:
        tmpl = p["tmpl"]
        R = rest_frame(tmpl)
        if p.get("badge_on"):
            spot = tmpl["badge"]
            W = tmpl["rig"].matrix_world
            bw = W @ spot["badge"]                      # the badge's rest matrix in world (scaled by 100 from rig space)
            loc = bw.translation
            card_rest = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(-6), 4, "X")
            tops = [card_rest @ Vector((s * 0.03, 0, 0.065)) for s in (-1, 1)]
            key = "cord_mesh"
            if key not in tmpl:
                pts = cord_points(R, tops[0], tops[1])
                verts, faces = ribbon(pts, R)
                me = bpy.data.meshes.new(f"crowd-cord-{tmpl['name']}")
                me.from_pydata([tuple(x) for x in verts], [], faces)
                me.materials.append(crowd.cord)
                body = tmpl["meshes"][0]
                w = transfer_weights(body, R["tree"], R["bverts"], verts, CORD_ALLOWED)
                for _ in range(3):                      # smooth along the cord (pairs of vertices per step)
                    n = len(w) // 2
                    nw = []
                    for i in range(len(w)):
                        k = i // 2
                        nb = [w[2 * max(0, k - 1) + i % 2], w[i], w[2 * min(n - 1, k + 1) + i % 2]]
                        acc = {}
                        for d in nb:
                            for g, x in d.items():
                                acc[g] = acc.get(g, 0) + x / 3
                        nw.append(acc)
                    w = nw
                tmp = bpy.data.objects.new("tmp", me)
                set_groups(tmp, w)
                bpy.data.objects.remove(tmp)
                tmpl[key] = me
            target = proxy_for(p, coll) if p.get("near_cam", 0.0) < NEAR_WRAP else None
            p["cord_ob"] = wear(p, tmpl[key], Matrix.Identity(4), "lanyard", coll, wrap=target, offset=0.004)
            for k, me in enumerate((crowd.badge_mesh, p["band_mesh"])):
                if "Bip01 Spine2" not in [g for g in me.get("groups", [])]:
                    pass
                ob = wear(p, me, card_rest, f"badge{k}", coll)
                if "Bip01 Spine2" not in ob.vertex_groups:
                    g = ob.vertex_groups.new(name="Bip01 Spine2")
                    g.add(list(range(len(me.vertices))), 1.0, "REPLACE")
                p.setdefault("badge_obs", []).append(ob)
            p["card_rest"] = card_rest
        if p.get("backpack"):
            me, rest = pack_mesh_for(tmpl, base, crowd)
            s = p["pack_scale"]
            tint = p["pack_tint"]
            target = proxy_for(p, coll) if p.get("near_cam", 0.0) < NEAR_WRAP else None
            ob = wear(p, me, rest @ Matrix.Diagonal((s * PACK_WIDTH, s, s, 1)), "backpack", coll, wrap=target, offset=0.006,
                      group="contact", materials=pack_mats[tint])
            p["pack_ob"] = ob
            body = p["body"][0]
            if not MASK_UNDER_PACK:
                continue
            mk = body.modifiers.new("under_pack", "MASK")
            mk.vertex_group, mk.invert_vertex_group = "under_pack", True
            while body.modifiers.find("under_pack") > 0:
                body.modifiers.move(body.modifiers.find("under_pack"), 0)
    return pack_mats


# ---------------------------------------------------------------------------------- measuring
def _evaluated(ob, dg):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    M = np.array(ob.matrix_world)
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    polys = [p.vertices[:] for p in me.polygons]
    ev.to_mesh_clear()
    return co, polys


def _inside(tree, pts):
    """depth of each point inside a closed mesh (nearest-face normal test), 0 outside"""
    d = np.zeros(len(pts))
    for i, p in enumerate(pts):
        loc, n, fi, dist = tree.find_nearest(Vector(p), 0.08)
        if loc is not None and (Vector(p) - loc).dot(n) < 0:
            d[i] = dist
    return d


def _hull_tree(co):
    """the closed convex hull of a point set (the decimated pack isn't watertight, its hull is)"""
    bm = bmesh.new()
    for c in co:
        bm.verts.new(c)
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    doomed = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if doomed:                                  # the two lists overlap: delete each vertex once
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _arm_index(ob):
    """vertices of the arms and hands (> 0.5 weight on an upper arm, forearm, hand or finger bone)"""
    gi = {g.index for g in ob.vertex_groups if any(k in g.name for k in ("UpperArm", "Forearm", "Hand", "Finger"))}
    return np.array([v.index for v in ob.data.vertices if any(g.group in gi and g.weight > 0.5 for g in v.groups)],
                    dtype=int)


def verify(crowd, frame_end, step_frames=12):
    """per wearer, on 12 frames over their loop: penetration (mm) of pack, cord and badge into the body and of the
    body into the badge and the pack, and the share of the pack's contact panel within 2 cm of the back"""
    scene = bpy.context.scene
    people = [p for p in crowd.people if p.get("pack_ob") or p.get("cord_ob")]
    for p in people:
        if not p.get("proxy"):
            proxy_for(p, crowd.coll if hasattr(crowd, "coll") else p["rig"].users_collection[0])
    shared = sorted({1 + int(i * (frame_end - 1) / (step_frames - 1)) for i in range(step_frames)})
    for p in people:                  # one shared set of frames: per-person loop grids made hundreds of whole-crowd
        p["vframes"] = shared         # evaluations (16/10: a 170-person build sat 30+ min in this check)
        p["m"] = {"pack": 0.0, "body_in_pack": 0.0, "arm_in_pack": 0.0, "cord": 0.0, "badge": 0.0, "body_in_badge": 0.0, "near": [],
                  "badge_frames": []}
    for f in sorted({f for p in people for f in p["vframes"]}):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for p in people:
            if f not in p["vframes"]:
                continue
            bco, bpolys = _evaluated(p["proxy"], dg)
            btree = BVHTree.FromPolygons([tuple(x) for x in bco], bpolys)
            m = p["m"]
            if p.get("pack_ob"):
                pco, ppolys = _evaluated(p["pack_ob"], dg)
                m["pack"] = max(m["pack"], float(_inside(btree, pco).max()))
                # body points inside the deformed pack (an inside test against its evaluated mesh, near points only)
                ptree = BVHTree.FromPolygons([tuple(x) for x in pco], ppolys)
                c = pco.mean(axis=0)
                near = bco[np.linalg.norm(bco - c, axis=1) < 0.35]
                m["body_in_pack"] = max(m["body_in_pack"], float(_inside(ptree, near).max()) if len(near) else 0.0)
                if "arm_idx" not in p:
                    p["arm_idx"] = _arm_index(p["proxy"])
                if len(p["arm_idx"]):
                    arms = bco[p["arm_idx"]]
                    arms = arms[np.linalg.norm(arms - c, axis=1) < 0.4]
                    if len(arms):
                        m["arm_in_pack"] = max(m["arm_in_pack"], float(_inside(_hull_tree(pco), arms).max()))
                cg = p["pack_ob"].vertex_groups["contact"].index
                ci = [v.index for v in p["pack_ob"].data.vertices if any(g.group == cg and g.weight > 0.5 for g in v.groups)]
                for i in ci[::7]:
                    loc_, n_, fi_, dist = btree.find_nearest(Vector(pco[i]))
                    m["near"].append(dist)
            if p.get("cord_ob"):
                cco, _ = _evaluated(p["cord_ob"], dg)
                m["cord"] = max(m["cord"], float(_inside(btree, cco).max()))
                worst = through = 0.0
                for ob in p.get("badge_obs", []):
                    kco, kpolys = _evaluated(ob, dg)
                    worst = max(worst, float(_inside(btree, kco).max()))
                    # the body (an arm) through the deformed card: an inside test against the card's own mesh
                    ktree = BVHTree.FromPolygons([tuple(x) for x in kco], kpolys)
                    near = bco[np.linalg.norm(bco - kco.mean(axis=0), axis=1) < 0.12]
                    if len(near):
                        through = max(through, float(_inside(ktree, near).max()))
                m["badge"] = max(m["badge"], worst)
                m["body_in_badge"] = max(m["body_in_badge"], through)
                m["badge_frames"].append((f, worst, through))
    rows = []
    for p in people:
        m = p["m"]
        near = np.array(m["near"]) if m["near"] else np.array([0.0])
        flush = float((near < 0.02).mean())
        rows.append((p["name"], p["clip"], m))
        print(f"WEAR {p['name']} {p['clip']}: pack {m['pack'] * 1000:.1f} mm, body in pack {m['body_in_pack'] * 1000:.1f} mm,"
              f" arm in pack {m.get('arm_in_pack', 0) * 1000:.1f} mm,"
              f" panel within 2 cm {flush * 100:.0f}% (median gap {np.median(near) * 1000:.0f} mm),"
              f" lanyard {m['cord'] * 1000:.1f} mm, badge {m['badge'] * 1000:.1f} mm,"
              f" body through badge {m['body_in_badge'] * 1000:.1f} mm", flush=True)
        m["flush"] = flush
    REPORT.extend(rows)
    return rows
