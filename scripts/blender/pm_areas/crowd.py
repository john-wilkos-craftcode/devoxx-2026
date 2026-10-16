"""The crowd for the venue fly-through: Microsoft Rocketbox avatars (data/models/rocketbox, MIT) moved by the
library's own motion capture (data/models/rocketbox_anims, fetched by scripts/fetch_rocketbox_anims.py, MIT).

Why it looks better than the old crowd (scripts/blender/look/crowd.py, hand-posed): every person plays a real
mocap clip (idling, talking, listening, texting, drinking, holding a bag, walking), each with its own start offset
and speed, so no two people move alike; badges hang on the chest front, worked out from each avatar's own mesh.

Retargeting: the clips' skeleton has the avatars' bones but a different rest pose, so the bone-local curves can't be
reused as they are. bake_library() copies each bone's armature-space rotation from the clip onto a reference avatar
(all women share one rest pose, all men another) and stores bone-local quaternion keys, plus the root's sway, as
one action per clip in data/models/rocketbox_anims/baked-v<n>.blend (rebuilt when a clip is newer than it).

Rig facts (Blender 5.2 FBX import): armature object "Bip01" at z 0.923 (women) / 0.895 (men), rot z -pi/2, scale
0.01; in armature space X is forward, so an avatar at rest faces world -Y. People stand on an anchor empty (floor
position, yaw, height scale); yaw = atan2(dx, -dy) faces them along (dx, dy).

build(root, unified=True) places the venue crowd (unified=True, needs the other areas built for its floor and
clearance checks); build(root) without unified builds six people for close-up checks.
"""
import json
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

import numpy as np

import pm_areas.crowd_wear as crowd_wear

FPS = 30
FACE = ("Eye", "Jaw", "Lip", "lip", "Mouth", "Masseter", "Caninus", "Cheek", "brow", "Nose", "Tongue", "Blink")
STEP = 2                                      # bake a key every 2 frames (15 per second)
BAKE_VERSION = 3                              # bump when bake_library changes
PEOPLE = []                                   # (name, role, clip) for reports
ROOT = None


# ---------------------------------------------------------------------------------- the clip library
def _channelbag(act, slot):
    layer = act.layers[0] if act.layers else act.layers.new("Layer")
    strip = layer.strips[0] if layer.strips else layer.strips.new(type="KEYFRAME")
    try:
        return strip.channelbag(slot, ensure=True)
    except TypeError:
        return strip.channelbags.new(slot)


def _fcurve_keys(cb, path, index, frames, values, group=None):
    fc = cb.fcurves.new(path, index=index)
    if group:
        g = cb.groups.get(group) or cb.groups.new(group)
        fc.group = g
    fc.keyframe_points.add(len(frames))
    co = [0.0] * (2 * len(frames))
    co[0::2], co[1::2] = frames, values
    fc.keyframe_points.foreach_set("co", co)
    for k in fc.keyframe_points:
        k.interpolation = "LINEAR"
    fc.update()


def _import(path, anim):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=anim)
    return list(set(bpy.data.objects) - before)


def _all_fcurves(act):
    return [f for l in act.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves]


def bake_library(root):
    """one baked action per clip (bone-local quaternions for the avatars' rest pose + the root's sway), cached"""
    anim_dir = Path(root) / "data" / "models" / "rocketbox_anims"
    out = anim_dir / f"baked-v{BAKE_VERSION}.blend"
    clips = sorted(anim_dir.glob("[fm]_*.fbx"))
    if not clips:
        raise FileNotFoundError("no clips: run scripts/fetch_rocketbox_anims.py")
    if out.exists() and out.stat().st_mtime > max(c.stat().st_mtime for c in clips):
        return out
    scene = bpy.context.scene
    scene.render.fps = FPS
    refs = {}
    for sex, avatar in (("f", "Female_Adult_01"), ("m", "Male_Adult_01")):
        objs = _import(Path(root) / "data" / "models" / "rocketbox" / avatar / f"{avatar}.fbx", False)
        refs[sex] = next(o for o in objs if o.type == "ARMATURE")
        for o in objs:
            if o is not refs[sex]:
                bpy.data.objects.remove(o)
    baked = []
    for path in clips:
        sex = path.stem[0]
        ref = refs[sex]
        objs = _import(path, True)
        arm = next(o for o in objs if o.type == "ARMATURE")
        helper = next((o for o in objs if o.name.startswith("MotionExtractionHelper")), None)
        src = arm.animation_data.action
        f0, f1 = (int(round(v)) for v in src.frame_range)
        frames = list(range(f0, f1 + 1, STEP))
        if frames[-1] != f1:
            frames.append(f1)
        bones = [b for b in ref.data.bones if not any(k in b.name for k in FACE) and b.name in arm.pose.bones]
        rest = {b.name: b.matrix_local.to_quaternion() for b in ref.data.bones}
        quats = {b.name: [] for b in bones}
        objloc, objrot = [], []
        travel = []
        hands = {"L": [], "R": []}
        for f in frames:
            scene.frame_set(f)
            q_arm = {b.name: arm.pose.bones[b.name].matrix.to_quaternion() for b in bones}
            for b in bones:
                q = rest[b.name].inverted() @ q_arm[b.name]
                if b.parent and b.parent.name in q_arm:
                    q = rest[b.name].inverted() @ rest[b.parent.name] @ q_arm[b.parent.name].inverted() @ q_arm[b.name]
                prev = quats[b.name][-1] if quats[b.name] else None
                if prev is not None and prev.dot(q) < 0:
                    q = -q
                quats[b.name].append(q)
            for side in "LR":
                hb = arm.pose.bones.get(f"Bip01 {side} Hand")
                if hb:
                    hands[side].append(hb.head.z)
            objloc.append(arm.location.copy())
            objrot.append(arm.rotation_euler.copy())
            if helper:
                travel.append(helper.matrix_world.translation.copy())
        act = bpy.data.actions.new(f"crowd-{path.stem}")
        slot = act.slots.new(id_type="OBJECT", name="rig")
        cb = _channelbag(act, slot)
        rel = [f - f0 + 1 for f in frames]                 # every baked clip starts at frame 1
        for name, qs in quats.items():
            for i in range(4):
                _fcurve_keys(cb, f'pose.bones["{name}"].rotation_quaternion', i, rel, [q[i] for q in qs], name)
        z_ref = ref.location.z
        for i in range(3):
            if i < 2:
                vals = [l[i] - objloc[0][i] for l in objloc]
            else:
                vals = [z_ref + l[2] - objloc[0][2] for l in objloc]
            _fcurve_keys(cb, "location", i, rel, vals, "root")
            base = -math.pi / 2 if i == 2 else 0.0
            vals = [base + r[i] - objrot[0][i] if i == 2 else r[i] for r in objrot]
            _fcurve_keys(cb, "rotation_euler", i, rel, vals, "root")
        act["length"] = rel[-1]
        speed = 0.0
        if len(travel) > 1:
            d = (travel[-1] - travel[0])
            d.z = 0
            speed = d.length / ((frames[-1] - frames[0]) / FPS)
        act["speed"] = speed                                # walks: metres per second the feet travel
        avg = {k: sum(v) / len(v) for k, v in hands.items() if v}
        act["hand"] = max(avg, key=avg.get) if avg else "R"   # the hand held higher: the one with the phone/cup
        act.use_fake_user = True
        baked.append(act)
        for o in objs:
            bpy.data.objects.remove(o)
        print(f"BAKED {path.stem}: {rel[-1]} frames, {len(bones)} bones, speed {speed:.2f} m/s")
    bpy.data.libraries.write(str(out), set(baked), fake_user=True)
    for a in baked:
        bpy.data.actions.remove(a)
    for r in refs.values():
        bpy.data.objects.remove(r)
    return out


def load_clips(root):
    path = bake_library(root)
    with bpy.data.libraries.load(str(path)) as (src, dst):
        dst.actions = [n for n in src.actions if n.startswith("crowd-")]
    return {a.name[len("crowd-"):]: a for a in dst.actions if a}


# ---------------------------------------------------------------------------------- avatars
def _texture(path, image=None):
    image = image or bpy.data.images.load(str(path), check_existing=True)
    image.filepath = str(path)
    image.reload()
    if max(image.size) > 1024:
        r = 1024 / max(image.size)
        image.scale(max(1, round(image.size[0] * r)), max(1, round(image.size[1] * r)))
    return image


def load_avatars(root, coll):
    """each avatar imported once, textures remapped, clothing varied per object (hue and value from the object's
    random number); the sources live in a hidden collection"""
    templates = []
    done = set()
    for path in sorted((Path(root) / "data" / "models" / "rocketbox").glob("*/*.fbx")):
        objs = _import(path, False)
        rig = next(o for o in objs if o.type == "ARMATURE")
        meshes = [o for o in objs if o.type == "MESH"]
        pngs = {p.stem.lower(): p for p in (path.parent / "Textures").glob("*.png")}
        for ob in objs:
            ob.animation_data_clear()
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            coll.objects.link(ob)
            if ob.type != "MESH":
                continue
            for mod in list(ob.modifiers):
                if mod.type == "SUBSURF":
                    ob.modifiers.remove(mod)
            for slot in ob.material_slots:
                mat = slot.material
                if not mat or mat in done or not mat.use_nodes:
                    continue
                done.add(mat)
                nodes, links = mat.node_tree.nodes, mat.node_tree.links
                shader = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
                if shader:
                    shader.inputs["Roughness"].default_value = 0.75
                    if "Specular IOR Level" in shader.inputs:
                        shader.inputs["Specular IOR Level"].default_value = 0.3
                for node in list(nodes):
                    if node.type != "TEX_IMAGE" or not node.image:
                        continue
                    stem = Path(node.image.filepath.replace("\\", "/")).stem.lower()
                    if stem not in pngs:
                        for o_ in node.outputs:
                            for l_ in list(o_.links):
                                links.remove(l_)
                        node.image = None
                        continue
                    node.image = _texture(pngs[stem], node.image)
                    node.image.colorspace_settings.name = "Non-Color" if ("normal" in stem or "opacity" in stem) else "sRGB"
                    if shader and "body_color" in stem:
                        info = nodes.new("ShaderNodeObjectInfo")
                        hue = nodes.new("ShaderNodeHueSaturation")
                        h = nodes.new("ShaderNodeMapRange")
                        h.inputs["To Min"].default_value, h.inputs["To Max"].default_value = 0.46, 0.54
                        links.new(info.outputs["Random"], h.inputs["Value"])
                        links.new(h.outputs["Result"], hue.inputs["Hue"])
                        v = nodes.new("ShaderNodeMath")                    # value from a second random
                        v.operation = "FRACT"
                        m = nodes.new("ShaderNodeMath")
                        m.operation = "MULTIPLY"
                        m.inputs[1].default_value = 7.31
                        links.new(info.outputs["Random"], m.inputs[0])
                        links.new(m.outputs[0], v.inputs[0])
                        vr = nodes.new("ShaderNodeMapRange")
                        vr.inputs["To Min"].default_value, vr.inputs["To Max"].default_value = 0.82, 1.12
                        links.new(v.outputs[0], vr.inputs["Value"])
                        links.new(vr.outputs["Result"], hue.inputs["Value"])
                        links.new(node.outputs["Color"], hue.inputs["Color"])
                        links.new(hue.outputs["Color"], shader.inputs["Base Color"])
                    if shader and "opacity_color" in stem:
                        alpha_path = next((p for k, p in pngs.items() if "opacity_color" in k), None)
                        if alpha_path:
                            a = nodes.new("ShaderNodeTexImage")
                            a.image = _texture(alpha_path)
                            a.image.colorspace_settings.name = "Non-Color"
                            links.new(a.outputs["Color"], shader.inputs["Alpha"])
        sex = "f" if path.stem.startswith("Female") else "m"
        templates.append({"name": path.stem, "sex": sex, "rig": rig, "meshes": meshes,
                          "badge": badge_spot(rig, meshes)})
    return templates


def badge_spot(rig, meshes):
    """where the badge hangs, from the avatar's own mesh at rest: on the chest front, on the midline, about 26 cm
    under the shoulders. Returns the badge's matrix in rig space and the lanyard's two neck points (rig space)."""
    bpy.context.view_layer.update()
    W = rig.matrix_world
    spine = rig.data.bones["Bip01 Spine2"]
    neck = rig.data.bones["Bip01 Neck"]
    # in world (avatar at rest at the origin, facing -Y): chest height from the neck
    neck_w = W @ neck.head_local
    target_z = neck_w.z - 0.24
    front = None
    for ob in meshes:
        M = ob.matrix_world
        for v in ob.data.vertices:
            w = M @ v.co
            if abs(w.z - target_z) < 0.035 and abs(w.x) < 0.05:
                if front is None or w.y < front.y:
                    front = w
    if front is None:
        front = Vector((0, neck_w.y - 0.12, target_z))
    centre = Vector((0.0, front.y - 0.02, target_z - 0.02))
    badge_w = Matrix.Translation(centre) @ Matrix.Rotation(math.radians(-6), 4, "X")   # hangs a little forward
    inv = W.inverted()
    neck_pts = []
    for s in (-1, 1):                                  # the lanyard leaves the collar on its surface, 3 mm out
        nz = neck_w.z - 0.03
        best = None
        for ob in meshes:
            M = ob.matrix_world
            for v in ob.data.vertices:
                w = M @ v.co
                if abs(w.z - nz) < 0.02 and abs(w.x - s * 0.055) < 0.015 and (best is None or w.y < best.y):
                    best = w
        p = (best + Vector((0, -0.003, 0))) if best is not None else Vector((s * 0.055, neck_w.y - 0.07, nz))
        neck_pts.append(inv @ p)
    top = [inv @ Vector((s * 0.03, centre.y, centre.z + 0.065)) for s in (-1, 1)]
    # the cords run over the chest, not through it: a middle point on the chest surface, 6 mm out
    mids = []
    for k, s in enumerate((-1, 1)):
        a, b = W @ neck_pts[k], W @ top[k]
        m = (a + b) / 2
        best = None
        for ob in meshes:
            M = ob.matrix_world
            for v in ob.data.vertices:
                w = M @ v.co
                if abs(w.z - m.z) < 0.015 and abs(w.x - m.x) < 0.015 and (best is None or w.y < best.y):
                    best = w
        p = Vector((m.x, min(m.y, best.y - 0.006) if best is not None else m.y, m.z))
        mids.append(inv @ p)
    return {"badge": inv @ badge_w, "neck": neck_pts, "mid": mids, "top": top, "spine": spine.name}


# ---------------------------------------------------------------------------------- one person
class Crowd:
    def __init__(self, root, coll, rng):
        self.coll, self.rng = coll, rng
        src = bpy.data.collections.new("crowd-sources")
        bpy.context.scene.collection.children.link(src)
        src.hide_render = src.hide_viewport = True
        self.templates = load_avatars(root, src)
        self.clips = load_clips(root)
        self.n = 0
        self.people = []

        white = bpy.data.materials.new("crowd-badge")
        white.use_nodes = True
        b = white.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.92, 0.92, 0.9, 1)
        b.inputs["Roughness"].default_value = 0.5
        self.badge_mesh = self._card(0.09, 0.13, white)
        self.band_mats = []
        for c in ((0.95, 0.45, 0.05), (0.1, 0.35, 0.85), (0.85, 0.1, 0.2), (0.1, 0.6, 0.3)):
            m = bpy.data.materials.new("crowd-band")
            m.use_nodes = True
            m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*c, 1)
            self.band_mats.append(m)
        self.band_meshes = [self._card(0.092, 0.028, m, zc=0.05, dy=-0.001) for m in self.band_mats]
        cord = bpy.data.materials.new("crowd-cord")
        cord.use_nodes = True
        cord.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
        self.cord = cord
        self.cord_meshes = {}


    def _card(self, w, h, mat, zc=0.0, dy=0.0):
        """a thin card in the XZ plane facing -Y (the front), centred on (0, dy, zc), in metres"""
        me = bpy.data.meshes.new("crowd-card")
        t = 0.0025
        zb, zt = zc - h / 2, zc + h / 2
        v = [(-w / 2, dy - t, zb), (w / 2, dy - t, zb), (w / 2, dy - t, zt), (-w / 2, dy - t, zt),
             (-w / 2, dy + t, zb), (w / 2, dy + t, zb), (w / 2, dy + t, zt), (-w / 2, dy + t, zt)]
        f = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0)]
        me.from_pydata(v, [], f)
        me.materials.append(mat)
        return me

    def _cord(self, a, b):
        """a thin flat strap between two rig-space points (rig space is in centimetres)"""
        key = (tuple(round(c, 1) for c in a), tuple(round(c, 1) for c in b))
        if key not in self.cord_meshes:
            d = (b - a)
            side = d.cross(Vector((0, 0, 1)))
            side = side.normalized() * 0.6 if side.length > 1e-6 else Vector((0.6, 0, 0))
            me = bpy.data.meshes.new("crowd-cord")
            me.from_pydata([a - side, a + side, b + side, b - side], [], [(0, 1, 2, 3)])
            me.materials.append(self.cord)
            self.cord_meshes[key] = me
        return self.cord_meshes[key]

    def person(self, tmpl, clip, x, y, z, yaw, offset=0, speed=1.0, height=1.0, walk=None, badge=True, role="",
               backpack=False):
        """tmpl: an avatar from self.templates; clip: a baked clip name; walk: (start, end, frames) moves the
        anchor along a straight line at the clip's own pace"""
        scene = bpy.context.scene
        i = self.n
        self.n += 1
        anchor = bpy.data.objects.new(f"crowd-{i:03d}", None)
        self.coll.objects.link(anchor)
        anchor.location, anchor.rotation_euler = (x, y, z), (0, 0, yaw)
        anchor.scale = (height,) * 3
        src = tmpl["rig"]
        rig = src.copy()
        rig.data = src.data
        rig.animation_data_clear()
        rig.name = f"crowd-{i:03d}-rig"
        self.coll.objects.link(rig)
        rig.parent = anchor
        rig.matrix_parent_inverse = Matrix.Identity(4)
        rig.matrix_basis = src.matrix_world.copy()
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
        for m in tmpl["meshes"]:
            ob = m.copy()
            ob.animation_data_clear()
            ob.name = f"crowd-{i:03d}-body"
            self.coll.objects.link(ob)
            ob.parent = rig
            ob.matrix_parent_inverse = m.matrix_parent_inverse.copy()
            ob.matrix_basis = m.matrix_basis.copy()
            for mod in ob.modifiers:
                if mod.type == "ARMATURE":
                    mod.object = rig
        act = self.clips[clip]
        ad = rig.animation_data_create()
        track = ad.nla_tracks.new()
        length = act["length"]
        scale = 1.0 / speed
        strip = track.strips.new(clip, int(1 - offset), act)
        if hasattr(strip, "action_slot") and act.slots:
            strip.action_slot = act.slots[0]
        strip.scale = scale
        strip.repeat = math.ceil((900 + offset) / (length * scale)) + 1
        strip.extrapolation = "HOLD"
        if walk:
            (sx, sy), (ex, ey), frames = walk
            for f, (px, py) in ((1, (sx, sy)), (frames, (ex, ey))):
                anchor.location = (px, py, z)
                anchor.keyframe_insert("location", frame=f)
            for fc in _all_fcurves(anchor.animation_data.action):
                for k in fc.keyframe_points:
                    k.interpolation = "LINEAR"
                fc.extrapolation = "LINEAR"
        self.people.append({"name": anchor.name, "rig": rig, "tmpl": tmpl, "loop": length * scale, "clip": clip,
                            "body": [o for o in rig.children if o.type == "MESH" and o.name.endswith("-body")],
                            "badge_on": badge, "band_mesh": self.band_meshes[self.rng.randrange(len(self.band_meshes))],
                            "backpack": backpack, "pack_scale": self.rng.uniform(0.95, 1.05),
                            "pack_tint": self.rng.choice(["black", "black", "charcoal", "navy", "olive"])})
        PEOPLE.append((anchor.name, role, clip))
        return anchor


# ---------------------------------------------------------------------------------- roles
CLIPS = {           # nothing that mimes holding an object (no phones, cups, bags, documents, headphones)
    "idle": ["idle_neutral_01", "idle_neutral_02", "idle_neutral_03", "idle_neutral_04", "idle_neutral_05",
             "idle_breathe_01", "idle_look_around_01", "idle_look_around_02", "idle_touch_face_01"],
    "wait": ["idle_waiting_01", "idle_neutral_02", "idle_look_around_01", "idle_look_around_02", "idle_breathe_01"],
    "talk": ["gestic_talk_neutral_01", "gestic_talk_neutral_02", "gestic_talk_neutral_03", "gestic_talk_relaxed_01",
             "gestic_talk_relaxed_02", "gestic_talk_self-assured_01", "gestic_laugh_low", "gestic_shrug_01",
             "gestic_shrug_02"],
    "listen": ["gestic_listen_neutral_01", "gestic_listen_neutral_02", "gestic_listen_neutral_03",
               "gestic_listen_accept_01", "gestic_listen_accept_02", "gestic_listen_relaxed", "gestic_laugh_low"],
    "walk": ["walk_neutral_01", "walk_neutral_02", "walk_neutral_03", "walk_stroll_01", "walk_stroll_02",
             "walk_slow_01", "walk_slow_02"],
}
BACKPACK_SHARE = 0.35


def pick(crowd, role, sex=None):
    """an avatar and a clip for a role, both drawn so neighbours differ"""
    rng = crowd.rng
    for _ in range(40):
        tmpl = rng.choice(crowd.templates) if sex is None else rng.choice([t for t in crowd.templates if t["sex"] == sex])
        name = f'{tmpl["sex"]}_{rng.choice(CLIPS[role])}'
        if name in crowd.clips:
            return tmpl, name
    tmpl = rng.choice(crowd.templates)
    return tmpl, f'{tmpl["sex"]}_idle_neutral_01'


def add(crowd, role, x, y, z, yaw, sex=None, walk_to=None, backpack=None):
    tmpl, clip = pick(crowd, role, sex)
    rng = crowd.rng
    speed = rng.uniform(0.9, 1.1)
    walk = None
    if walk_to is not None:
        v = crowd.clips[clip].get("speed", 1.2) or 1.2
        v *= speed
        dist = math.hypot(walk_to[0] - x, walk_to[1] - y)
        frames = 1 + dist / v * FPS
        walk = ((x, y), walk_to, frames)
        yaw = math.atan2(walk_to[0] - x, -(walk_to[1] - y))
    return crowd.person(tmpl, clip, x, y, z, yaw, offset=rng.randrange(0, 600), speed=speed,
                        height=rng.uniform(0.96, 1.04), walk=walk, badge=rng.random() < 0.85, role=role,
                        backpack=(rng.random() < BACKPACK_SHARE) if backpack is None else backpack)


# ---------------------------------------------------------------------------------- the test set
TEST_SPEC = [("f", "talk", False), ("m", "listen", True), ("f", "idle", False), ("m", "talk", True),
             ("f", "wait", True), ("m", "idle", False)]


def build_test(crowd):
    """six people in a row for close-up checks: 3 women, 3 men, different clips"""
    L_ = __import__("pm_lib")
    L_.box("floor", -8, -8, -0.1, 8, 8, 0, L_.mat("grey", 0x6a6a6e, 0.9))
    L_.world_color(0x9aa0aa, 0.6)
    L_.area_light("key", (2, -4, 6), 6, 2500, rot=(math.radians(30), 0, math.radians(20)))
    L_.area_light("fill", (-3, -2, 4), 4, 600, rot=(math.radians(40), 0, math.radians(-40)))
    L_.area_light("rim", (0, 4, 5), 5, 900, rot=(math.radians(-40), 0, 0))
    for k, (sex, role, pack) in enumerate(TEST_SPEC):
        add(crowd, role, -6.25 + k * 2.5, 0, 0, 0.0, sex=sex, backpack=pack)


# ---------------------------------------------------------------------------------- the venue crowd
def build(root, unified=False):
    global ROOT
    ROOT = Path(root)
    bpy.context.scene.render.fps = FPS
    coll = bpy.data.collections.new("crowd")
    bpy.context.scene.collection.children.link(coll)
    crowd = Crowd(root, coll, random.Random(20261015))
    horizon = 740
    if not unified:
        build_test(crowd)
    else:
        import pm_areas.crowd_place as crowd_place                  # placement lives in crowd_place.py
        crowd_place.place(crowd, ROOT)
        horizon = crowd_place.HORIZON
    crowd_wear.dress(crowd, ROOT)
    fix_badges(crowd, horizon)
    if unified:
        crowd_place.hide_unseen(crowd)
    print(f"CROWD {crowd.n} people, {sum(1 for p in crowd.people if p.get('pack_ob'))} backpacks, "
          f"{sum(1 for p in crowd.people if p.get('cord_ob'))} badges", flush=True)
    return crowd


def fix_badges(crowd, frame_end):
    """measure everyone; a badge an arm goes through moves up the chest or out a little, else it goes (with its
    lanyard); the numbers for the report are the final ones"""
    crowd_wear.verify(crowd, frame_end)
    for p in [p for p in crowd.people if p.get("pack_ob")]:
        m = p["m"]
        # body_in_pack is reported but not used yet: its inside test misfires on the decimated pack (not watertight)
        if m["pack"] > 0.003 or m["flush"] < 0.6 or m.get("arm_in_pack", 0) > 0.005:
            body = p["body"][0]
            mk = body.modifiers.get("under_pack")
            if mk:
                body.modifiers.remove(mk)
            bpy.data.objects.remove(p["pack_ob"])
            p["pack_ob"] = None
            print(f"PACK {p['name']}: no backpack (pack {m['pack'] * 1000:.0f} mm into the body, body "
                  f"{m['body_in_pack'] * 1000:.0f} mm into the pack, an arm {m.get('arm_in_pack', 0) * 1000:.0f} mm into it, "
                  f"{m['flush'] * 100:.0f}% of the panel within 2 cm)", flush=True)
    moves = [Vector((0, 0, 0.02)), Vector((0, -0.006, 0.0)), Vector((0, -0.006, 0.03)), Vector((0, 0, 0.045))]
    failing = [p for p in crowd.people if p.get("cord_ob")
               and (p["m"]["badge"] > 0.0005 or p["m"]["body_in_badge"] > 0.0005)]
    for mv in moves:                  # each move tried on all failing badges at once (one check per move, not per person)
        if not failing:
            break
        for p in failing:
            for ob in p["badge_obs"]:
                ob.matrix_basis = p["tmpl"]["rig"].matrix_world.inverted() @ Matrix.Translation(mv) @ p["card_rest"]
        crowd_wear.REPORT.clear()
        crowd_wear.verify(_Some(failing), frame_end)
        still = []
        for p in failing:
            if p["m"]["badge"] <= 0.0005 and p["m"]["body_in_badge"] <= 0.0005:
                print(f"BADGE {p['name']}: moved {tuple(round(c, 3) for c in mv)} to clear the arms", flush=True)
            else:
                still.append(p)
        failing = still
    for p in failing:
        for ob in p["badge_obs"] + [p["cord_ob"]]:
            bpy.data.objects.remove(ob)
        p["badge_obs"], p["cord_ob"] = [], None
        print(f"BADGE {p['name']}: no badge (an arm passes through it whatever the small move)", flush=True)


class _Only:
    def __init__(self, crowd, p):
        self.people = [p]


class _Some:
    def __init__(self, people):
        self.people = people
