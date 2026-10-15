"""The hall's schedule screen, carried over from build_scene.py (where John liked it) onto the north wall of the
photo-matched hall, between the stairwells: a 16:10 panel with a thin satin bezel in front of the curtains, a blue LED
line at the curtain head with ivy trailing from the ceiling over the screen's top margin, a pachira in a tall
anthracite planter either side leaning a leaf or two over the glass, and the phone's portrait schedule totem to the
right with its own plant.

The plants and the ivy are kept as their own objects (FRONT) so the page's cut-out layer can lay them over the HTML
pinned on the screen ("programme" quads), as before. fit_plants(camera) slides each planter until its leaves just
cross the screen's edge as that camera sees it.

Venue coordinates (hall floor z = 0). Used by venue.py.
"""
import math
import random

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

import pm_lib as L

SX = 2.4                                         # centred between the stairwells (x -4.85 .. 9.65)
NORTH = 18.3 - 0.15                              # inner face of the north wall's curtains
SCREEN = {"x": SX, "y": NORTH - 0.32, "z": 1.7, "w": 3.6, "h": 2.25}
BEZEL, CHIN = 0.05, 0.05
TOTEM = {"x": SX + 3.2, "y": NORTH - 2.6, "z": 1.5, "w": 0.70, "h": 1.42}
CEIL = 3.26                                      # the hall's lowered ceiling (hollywood.LOW)
HEAD = 3.0                                       # the curtain head: a pelmet drops the ceiling to the old hall's 3.0 m
LAPTOP, PHONE = (1920, 1080), (1080, 2340)
ASPECT = 16 / 9

FRONT = set()                                    # object names of the cut-out layer: plants and ivy
PLANTS = []                                      # (root, corners, side, camera name)
screen_corners, totem_corners = [], []


def mats():
    foliage = L.mat("hs-foliage", 0x4a7a3a, 0.55)
    nt = foliage.node_tree
    if not any(n.type == "BSDF_TRANSLUCENT" for n in nt.nodes):   # thin leaves: backlit ivy glows
        tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
        tr.inputs["Color"].default_value = L.srgb(0x7fb04a)
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = 0.3
        nt.links.new(nt.nodes["Principled BSDF"].outputs["BSDF"], mix.inputs[1])
        nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], nt.nodes["Material Output"].inputs["Surface"])
    return {"bezel": L.mat("hs-bezel", 0x0b0b0e, 0.28, 0.4), "programme": L.emissive("programme", 0x1d2c7a, 6.0),
            "cove": L.emissive("hs-cove", 0xD9D2FF, 18.0), "foliage": foliage,
            "planter": L.mat("hs-planter", 0x2a2c31, 0.5), "soil": L.mat("hs-soil", 0x241c16, 1.0, bump=0.4),
            "frame": L.mat("hs-frame", 0x1a1b1e, 0.45, 0.6)}


def model_parts(root, asset):
    """mesh objects of a Poly Haven model fetched by scripts/fetch_models.py, by name, not linked into the scene"""
    p = root / "data" / "models" / asset / f"{asset}.blend"
    if not p.exists():
        print(f"model {asset} missing (run scripts/fetch_models.py); leaving it out")
        return {}
    with bpy.data.libraries.load(str(p)) as (src, dst):
        dst.objects = list(src.objects)
    for img in bpy.data.images:
        fp = img.filepath.replace("\\", "/")
        if "textures/" in fp and asset in fp:
            img.filepath = str(root / "data" / "models" / asset / "textures" / fp.rsplit("/", 1)[-1])
    return {o.name.replace(asset + "_", ""): o for o in dst.objects if o and o.type == "MESH"}


def planter_plant(name, x, y, tree, turn, parts_src, M, size=0.46, height=0.62):
    """a square planter with a tree and low clumps round its trunk, parented to an empty at its foot"""
    scene = bpy.context.scene
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0)
    scene.collection.objects.link(root)
    bm = bmesh.new()
    t, hs = 0.025, size / 2
    for (bx, by, bw, bh) in ((-hs, -hs, size, t), (-hs, hs - t, size, t), (-hs, -hs, t, size), (hs - t, -hs, t, size)):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((bx + bw / 2, by + bh / 2, height / 2)) @ Matrix.Diagonal((bw, bh, height, 1)))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.004, segments=2, affect="EDGES")
    soil = bmesh.new()
    bmesh.ops.create_cube(soil, size=1.0, matrix=Matrix.Translation((0, 0, height - 0.05)) @ Matrix.Diagonal((size - 2 * t, size - 2 * t, 0.02, 1)))
    parts = []
    for nm, b_, mat in ((f"{name}-pot", bm, M["planter"]), (f"{name}-soil", soil, M["soil"])):
        me = bpy.data.meshes.new(nm)
        b_.to_mesh(me)
        b_.free()
        ob = bpy.data.objects.new(nm, me)
        ob.data.materials.append(mat)
        parts.append(ob)
    rng = random.Random(name)
    pachira, calathea = parts_src
    for key, loc, rz, s in [(f"leaves_{tree}", (0, 0, height - 0.05), turn, 1.0), (f"bark_{tree}", (0, 0, height - 0.05), turn, 1.0)] + \
            [(k, (rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), height - 0.05), rng.uniform(0, 6.3), 0.8) for k in ("a", "c", "b")]:
        src = pachira.get(key) or calathea.get(key)
        if not src:
            continue
        ob = src.copy()
        ob.name = f"{name}-{key}"
        ob.location, ob.rotation_euler, ob.scale = loc, (0, 0, rz), (s, s, s)
        parts.append(ob)
    for ob in parts:
        ob.parent = root
        scene.collection.objects.link(ob)
    return root


def build(root, unified=True):
    global screen_corners, totem_corners
    M = mats()
    S = SCREEN
    # the screen: bezel and the emissive "programme" the page pins its HTML onto
    L.box("hs-bezel", SX - S["w"] / 2 - BEZEL, S["y"] - 0.05, S["z"] - S["h"] / 2 - CHIN,
          SX + S["w"] / 2 + BEZEL, S["y"] + 0.05, S["z"] + S["h"] / 2 + BEZEL, M["bezel"], bevel=0.006)
    sy_ = S["y"] - 0.055
    screen_corners = [(SX - S["w"] / 2, sy_, S["z"] - S["h"] / 2), (SX + S["w"] / 2, sy_, S["z"] - S["h"] / 2),
                      (SX + S["w"] / 2, sy_, S["z"] + S["h"] / 2), (SX - S["w"] / 2, sy_, S["z"] + S["h"] / 2)]
    L.mesh_obj("programme", screen_corners, [(0, 1, 2, 3)], M["programme"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # mounting: two dark posts to the wall behind
    for dx in (-1.2, 1.2):
        L.box("hs-mount", SX + dx - 0.04, S["y"] + 0.05, S["z"] - 0.3, SX + dx + 0.04, NORTH, S["z"] + 0.3, M["frame"])
    # the phone's portrait schedule totem, right of the screen
    T = TOTEM
    tb = 0.035
    L.box("hs-totem-bezel", T["x"] - T["w"] / 2 - tb, T["y"] - 0.03, T["z"] - T["h"] / 2 - 0.09,
          T["x"] + T["w"] / 2 + tb, T["y"] + 0.04, T["z"] + T["h"] / 2 + tb, M["bezel"], bevel=0.004)
    L.box("hs-totem-post", T["x"] - 0.06, T["y"] + 0.04, 0.04, T["x"] + 0.06, T["y"] + 0.1, T["z"] - T["h"] / 2, M["frame"])
    L.box("hs-totem-foot", T["x"] - 0.3, T["y"] - 0.2, 0.0, T["x"] + 0.3, T["y"] + 0.22, 0.04, M["frame"])
    ty_ = T["y"] - 0.035
    totem_corners = [(T["x"] - T["w"] / 2, ty_, T["z"] - T["h"] / 2), (T["x"] + T["w"] / 2, ty_, T["z"] - T["h"] / 2),
                     (T["x"] + T["w"] / 2, ty_, T["z"] + T["h"] / 2), (T["x"] - T["w"] / 2, ty_, T["z"] + T["h"] / 2)]
    L.mesh_obj("programme-totem", totem_corners, [(0, 1, 2, 3)], M["programme"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # a pelmet over the curtains between the stairwells, down to the old hall's ceiling height, with a blue-white LED
    # line under its front edge (the ivy hangs from it, as it did from the old ceiling)
    L.box("hs-pelmet", -4.6, NORTH - 0.62, HEAD, 9.4, NORTH + 0.15, CEIL + 0.02, L.mat("hs-pelmet", 0xe9e9ec, 0.85))
    L.box("hs-cove", -4.6, NORTH - 0.33, HEAD - 0.025, 9.4, NORTH - 0.30, HEAD, M["cove"])
    # ivy trailing from the ceiling; over the screen the strands stop a few centimetres onto the glass's margin
    rng = random.Random(7)
    verts, faces = [], []
    for gx in [SX + k * 0.9 for k in range(-6, 7)]:
        for _ in range(9):
            x, y, z = gx + rng.uniform(-0.45, 0.45), NORTH - 0.55 + rng.uniform(-0.12, 0.12), HEAD - 0.01
            steps = int(rng.uniform(0.1, 0.55) ** 1.3 / 0.025) + 2
            if abs(x - SX) < S["w"] / 2 + 0.15:
                steps = min(steps, rng.choice((2, 3, 4, 5, 6)))
            for _ in range(steps):
                x, y, z = x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.015, 0.015), z - 0.025
                u = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1.6, -0.2))).normalized()
                v = u.cross(Vector((0, 0, 1))).normalized() if abs(u.z) < 0.98 else Vector((1, 0, 0))
                c, a_, b_ = Vector((x, y, z)), 0.045 * rng.uniform(0.7, 1.25), 0.026 * rng.uniform(0.7, 1.25)
                fold = u.cross(v) * b_ * 0.35
                k = len(verts)
                verts += [c, c + u * a_ * 0.35 + v * b_ + fold, c + u * a_, c + u * a_ * 0.35 - v * b_ + fold]
                faces += [(k, k + 1, k + 2), (k, k + 2, k + 3)]
    L.mesh_obj("ivy", verts, faces, M["foliage"])
    FRONT.add("ivy")
    # the plants: either side of the screen, crowns leaning in; one beside the totem
    src = (model_parts(root, "pachira_aquatica_01"), model_parts(root, "calathea_orbifolia_01"))
    if src[0]:
        for sgn in (-1, 1):
            r = planter_plant(f"plant-hall-{'w' if sgn < 0 else 'e'}", SX + sgn * 2.2, S["y"] - 0.75, "d",
                              0.6 if sgn < 0 else 3.6, src, M)
            PLANTS.append((r, screen_corners, sgn, "cam-hall"))
        r = planter_plant("plant-totem", T["x"] + 0.75, T["y"] - 0.45, "d", 2.2, src, M)
        PLANTS.append((r, totem_corners, 1, "cam-hall-phone"))
    for r, *_ in PLANTS:
        FRONT.update(o.name for o in [r, *r.children])


def fit_distance(w, h, fov_deg, fill):
    t = math.tan(math.radians(fov_deg) / 2)
    return max(h / 2 / t, w / 2 / (t * ASPECT)) / fill


def hall_pose():
    """square on to the screen, close enough that it fills most of a laptop's view (as build_scene.py had it)"""
    d = fit_distance(SCREEN["w"] + 2 * BEZEL, SCREEN["h"] + BEZEL + CHIN, 40, 0.86)
    return (SCREEN["x"], SCREEN["y"] - d, SCREEN["z"]), (SCREEN["x"], SCREEN["y"], SCREEN["z"]), 40


def cameras():
    """cam-hall (laptop) and cam-hall-phone (phone, on the totem), as before"""
    scene = bpy.context.scene

    def still(name, loc, look, fov, dof=None):
        data = bpy.data.cameras.new(name)
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        data.sensor_fit, data.angle_y = "VERTICAL", math.radians(fov)
        data.clip_start = 0.05
        if dof:
            data.dof.use_dof, data.dof.focus_distance, data.dof.aperture_fstop = True, dof[0], dof[1]
        return ob
    pos, look, fov = hall_pose()
    hall = still("cam-hall", pos, look, fov)
    tdist = 1.7
    hfov = 2 * math.atan(TOTEM["w"] / 2 / 0.8 / tdist)
    phone = still("cam-hall-phone", (TOTEM["x"], TOTEM["y"] - tdist, TOTEM["z"]), (TOTEM["x"], TOTEM["y"], TOTEM["z"]),
                  2 * math.degrees(math.atan(math.tan(hfov / 2) * PHONE[1] / PHONE[0])), dof=(tdist, 1.8))
    bpy.context.view_layer.update()
    return hall, phone


def fit_plants(cams):
    """slide each planter along x until its leaves cross its screen's edge by a hair (as build_scene.py did)"""
    scene = bpy.context.scene
    for root, corners, sgn, cam_name in PLANTS:
        camera = cams[cam_name]
        wh, overlap = (LAPTOP, 0.012) if cam_name == "cam-hall" else (PHONE, 0.015)
        scene.render.resolution_x, scene.render.resolution_y = wh
        leaves = [o for o in root.children if "leaves" in o.name]
        edge = (min if sgn < 0 else max)(world_to_camera_view(scene, camera, Vector(c)).x for c in corners)
        zs, glass_y = sorted(c[2] for c in corners), min(c[1] for c in corners)

        def reach():
            bpy.context.view_layer.update()
            ws = [o.matrix_world @ v.co for o in leaves for v in o.data.vertices]
            us = [world_to_camera_view(scene, camera, w).x for w in ws if zs[0] < w.z < zs[-1] and w.y < glass_y - 0.03]
            return (max if sgn < 0 else min)(us) if us else None
        for _ in range(4):
            r0 = reach()
            if r0 is None:
                break
            root.location.x += 0.05
            r1 = reach()
            root.location.x -= 0.05
            if abs(r1 - r0) < 1e-6:
                break
            root.location.x += 0.05 * ((edge - sgn * overlap) - r0) / (r1 - r0)
        bpy.context.view_layer.update()
        print(f"PLANT {root.name}: x {root.location.x:.2f}")
