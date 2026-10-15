"""Entrance and reception on Ghost Light's floor plan (data/venue/venue.json, via entrance_plan.py), in venue
coordinates: metres, +x east, +y north, z up, the frame build_scene.py uses. The reception floor is at z 1.2, the
glass facade's inside face at y -60.4, the west wall at x -13.45, the grand stair x -2.4..12.4 rises north from the
facade (1.2) to floor 1 (6.2) at y -49.25 between 5 m side walls at x -2.7 and 12.4..12.7.

Walls, columns, the stair, the facade's mullions and bands, the plan's desks and partitions all come from the plan.
The photos add what the plan can't know: the ceiling height (underside at z 5.6, both photos agree within 0.15 m),
the Devoxx 2026 dressing, and where the facade above 3.2 m is glazed.

Cameras, resected against the plan's facade mullions (scripts/photomatch, data/photomatch/cameras/entrance.json):
- entrance_line_wide_angle_with_reception: in the west bay at (-6.04, -43.21, 3.21), 2.0 m above the floor, looking
  south at the doors between mullions -7.3 and -10.17; the west wall is the white wall on its right, the column at
  (-4.15, -49.19) is the white pillar, and the reception (counter, wood slats, TVs, white soffit) stands under the
  grand stair's top end on its left.
- entrance_line: in the west bay at (-9.99, -49.10, 2.35), 1.15 m up by a counter corner, looking south-south-west
  into the low sun; the west wall (navy south of y -53.65, white north of it) is on its right.
"""
import json
import math
from pathlib import Path

import bpy

import pm_lib as L
from pm_areas import entrance_flora as F
from pm_areas import entrance_plan as P

LOOK = "AgX - Medium High Contrast"
EXPOSURE = 0.0

FLOOR = P.FLOOR                # 1.2
CEIL = 5.6                     # underside of the ceiling (both photos: 5.42-5.73)
FACADE = -60.4
WEST_IN = -13.45               # inside face of the west wall
NAVY_FROM = -53.65             # the west wall is navy from here to the facade (portrait)
STAIR_W = -2.7                 # west face of the grand stair's west wall
STAIR_N = -49.25               # the stair's top end; the reception's slat wall is on this face, under the stair
STAIR_W_TOP = 4.0              # ...which in the wide photo stops at the white soffit's line (v 150-160): above it the stair's
                               # blue-lit concrete underside shows, not a 5 m wall
CAMS = {}
ROOT_DIR = []
UNIFIED = [False]              # build(root, unified=True): part of the whole venue, no photo hacks
NORTH = -37.4                  # the reception's north edge; the Hollywood module owns the hall steps beyond
HALL_CEIL = 3.76               # the hall's ceiling (absolute), the bulkhead over the opening starts here


def cams(root):
    from pm import Cam
    spec = json.loads((root / "data" / "photomatch" / "cameras" / "entrance.json").read_text())
    for k, v in spec.items():
        if "cal" not in v:
            continue                                    # check views have no solved photo camera
        CAMS[k] = Cam(json.loads((root / "data" / "photomatch" / v["cal"]).read_text()), v["C"], v.get("turns", 0))


def px(cam, u, v, axis, value):
    """world point where photo pixel (u, v) of camera 'wide'/'line' meets the plane world[axis] = value"""
    c = CAMS["entrance_line_wide_angle_with_reception" if cam == "wide" else "entrance_line"]
    return tuple(c.on_plane(u, v, "xyz".index(axis), value))


def hide_from_camera(ob):
    ob.visible_camera = False
    return ob


def screen_mat(name, c0, c1, strength=3.0, bands=3.0):
    """a lit screen with a simple diagonal two-colour graphic (no photo pixels)"""
    if name in L.MATS:
        return L.MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = bands
    wave.inputs["Distortion"].default_value = 4.0
    nt.links.new(tc.outputs["UV"], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = L.srgb(c0)
    ramp.color_ramp.elements[1].color = L.srgb(c1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    nt.links.new(ramp.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    m.diffuse_color = L.srgb(c0)
    L.MATS[name] = m
    return m


def thin_glass():
    """window glass as a thin sheet: mostly transparent with a faint reflection, so sunlight and the sky pass
    straight through (refractive glass blocks direct light when caustics are off)"""
    if "glass" in L.MATS:
        return L.MATS["glass"]
    m = bpy.data.materials.new("glass")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.9, 0.93, 0.92, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.02
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.5
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    m.diffuse_color = (0.8, 0.9, 0.95, 0.3)
    L.MATS["glass"] = m
    return m


def concrete_ceiling(root=None):
    """sprayed concrete slab: blotchy tone, the board/trowel marks of a CC0 concrete scan (ambientCG
    Concrete031, data/textures/entrance-ceiling) in colour and normal, and a coarse spray bump on top"""
    if "ceiling" in L.MATS:
        return L.MATS["ceiling"]
    m = L.mat("ceiling", 0x707078, 0.95)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 3.0
    n1.inputs["Detail"].default_value = 4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = L.srgb(0x24242c)
    ramp.color_ramp.elements[1].color = L.srgb(0x5e5e68)
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 45
    fine.inputs["Detail"].default_value = 6
    ramp2 = nt.nodes.new("ShaderNodeValToRGB")
    ramp2.color_ramp.elements[0].position, ramp2.color_ramp.elements[1].position = 0.35, 0.65
    ramp2.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
    ramp2.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    nt.links.new(fine.outputs["Fac"], ramp2.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(ramp2.outputs["Color"], mix.inputs["B"])
    tex_dir = ROOT_DIR[0] / "data" / "textures" / "entrance-ceiling" if ROOT_DIR else None
    normal_out = None
    if tex_dir and (tex_dir / "color.jpg").exists():
        coord, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / 2.4,) * 3
        nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])

        def image(name, cs):
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(str(tex_dir / name), check_existing=True)
            t.image.colorspace_settings.name = cs
            nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
            return t
        col = image("color.jpg", "sRGB")
        bc = nt.nodes.new("ShaderNodeBrightContrast")
        bc.inputs["Bright"].default_value, bc.inputs["Contrast"].default_value = 0.45, 0.6
        nt.links.new(col.outputs["Color"], bc.inputs["Color"])
        mix2 = nt.nodes.new("ShaderNodeMix")
        mix2.data_type, mix2.blend_type = "RGBA", "MULTIPLY"
        mix2.inputs["Factor"].default_value = 1.0
        nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
        nt.links.new(bc.outputs["Color"], mix2.inputs["B"])
        nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 2.0
        nt.links.new(image("normal.jpg", "Non-Color").outputs["Color"], nm.inputs["Color"])
        normal_out = nm.outputs["Normal"]
    else:
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 25
    n2.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    if normal_out is not None:
        nt.links.new(normal_out, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def glare(scene, strength):
    """bloom round the blown-out glass, as the lens did (fog glow in the compositor)"""
    try:
        tree = scene.compositing_node_group
        if tree is None:
            tree = bpy.data.node_groups.new("pm-comp", "CompositorNodeTree")
            scene.compositing_node_group = tree
            rl = tree.nodes.new("CompositorNodeRLayers")
            gl = tree.nodes.new("CompositorNodeGlare")
            out = tree.nodes.new("NodeGroupOutput")
            tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            tree.links.new(rl.outputs["Image"], gl.inputs["Image"])
            tree.links.new(gl.outputs["Image"], out.inputs[0])
        gl = next(n for n in tree.nodes if n.bl_idname == "CompositorNodeGlare")
        gl.inputs["Type"].default_value = "Fog Glow"
        for key, val in (("Threshold", 1.0), ("Strength", strength), ("Size", 0.9), ("Quality", "High")):
            if key in gl.inputs:
                gl.inputs[key].default_value = val
        scene.render.use_compositing = strength > 0
    except Exception as e:                                  # noqa: BLE001 - glare is a nicety
        print("glare unavailable:", e)


def plan_geometry(root):
    """walls, columns, desks, partitions, the stair and the facade straight from the plan"""
    boxes, links, _ = P.load(root)
    white = L.mat("wall-white", 0xdcdde6, 0.85)
    navy = L.mat("wall-navy", 0x1d2a4a, 0.8)
    alu = L.mat("alu-dark", 0x2c2e33, 0.4, metal=0.6)
    band = L.mat("facade-band", 0xc9cbd0, 0.6)
    counter = L.mat("counter-white", 0xeee8de, 0.35, coat=0.3)
    stair_side = L.mat("stair-side", 0x1a2138, 0.7)
    pole = L.mat("pole", 0xb8bcc2, 0.35, metal=0.8)
    vx0, vy0, vx1, vy1 = P.STAIR_VOID
    for i, b in enumerate(boxes):
        mat = b["material"]
        if mat in ("sign", "signAccent"):
            continue                                    # the outside lettering sits above the ceiling line
        x0, y0, x1, y1, z0, z1 = b["x0"], b["y0"], b["x1"], b["y1"], b["z0"], b["z1"]
        # the plan's heights are game guesses; the photos win on anything vertical or narrow:
        if b["exterior"] and mat == "structure" and z1 - z0 >= 1.0:
            continue                                    # no solid band 3.2-5 m: glass up to the ceiling (wide)
        if b["kind"] == "obstacles" and abs(x0 + 13.6) < 0.01 and abs(y0 + 60.55) < 0.01:
            continue                                    # no 0.75 m corner pier: glass up to the west wall (portrait)
        if b["kind"] == "obstacles" and abs(y0 + 48.05) < 0.01 and y1 - y0 < 0.2:
            continue                                    # the partitions at y -48.05 aren't there in 2026 (wide photo)
        if b["kind"] == "obstacles" and abs(x0 - STAIR_W) < 0.01 and abs(y0 + 57.1) < 0.01:
            z1 = STAIR_W_TOP                            # the stair's west side stops at the reception's white soffit
        if (b["kind"] == "obstacles" and mat != "desk" and -4.3 < (x0 + x1) / 2 < 1.5
                and -49.6 < (y0 + y1) / 2 < -47.9):
            z1 = min(z1, STAIR_W_TOP)                   # the column, stub and partition under the stair end at the soffit
        in_void = vx0 <= (x0 + x1) / 2 <= vx1 and vy0 <= (y0 + y1) / 2 <= vy1
        if UNIFIED[0] and (b["exterior"] and b["kind"] == "decor" or (y0 + y1) / 2 > NORTH + 0.01
                           or (y0 + y1) / 2 < -60.2):
            continue                                    # the facade skin (posts too) is outside's, north of -37.4 Hollywood's
        if b["exterior"] and b["kind"] == "decor":
            if mat == "glazing":
                L.box(f"plan-glazing{i}", x0, y0, z0, x1, y1, z1, thin_glass())
            elif mat == "paving":
                L.cylinder(f"plan-pole{i}", (x0 + x1) / 2, (y0 + y1) / 2, FLOOR, z1, 0.06, pole)
            elif mat == "structure":
                L.box(f"plan-band{i}", x0, y0, z0, x1, y1, z1, band if z1 - z0 < 1.0 or x1 - x0 < 0.2 else white)
            else:
                L.box(f"plan-mullion{i}", x0, y0, z0, x1, y1, min(z1, CEIL), alu)
            continue
        if b["link"] == "grand-stair":
            L.box(f"plan-stair{i}", x0, y0, z0, x1, y1, z1, stair_side)
            continue
        if b["link"]:
            continue                                    # hall-steps colliders: the treads are built below
        top = z1 if in_void else min(z1, CEIL)
        if b["exterior"] and z1 - z0 >= 3.0 and max(x1 - x0, y1 - y0) > 3.0:
            top = CEIL                                  # the envelope walls run up to the ceiling (portrait)
        if UNIFIED[0] and z1 - z0 >= 2.5 and max(x1 - x0, y1 - y0) > 2.5 and z1 < CEIL:
            top = CEIL                                  # whole venue: walls close up to the ceiling, no gaps
        if mat == "desk":
            L.box(f"plan-desk{i}", x0, y0, z0, x1, y1, FLOOR + 1.1, counter)   # real counters are ~1.1 m
            continue
        if abs(x0 + 13.75) < 0.05 and x1 - x0 < 0.5:    # the west wall: navy towards the facade (portrait)
            L.box(f"plan-west-navy{i}", x0, y0, z0, x1, NAVY_FROM, top, navy)
            L.box(f"plan-west-white{i}", x0, NAVY_FROM, z0, x1, y1, top, white)
            continue
        L.box(f"plan-wall{i}", x0, y0, z0, x1, y1, top, white)
    tread = L.mat("stair-tread", 0x2a2f3c, 0.8, bump=0.2, bump_scale=300)
    for ln in links:
        if UNIFIED[0] and ln["id"] != "grand-stair":
            continue
        for j, (x0, y0, x1, y1, z0, z1) in enumerate(P.stair_steps(ln)):
            L.box(f"{ln['id']}-step{j}", x0, y0, max(z0, 0), x1, y1, z1, tread)


def shell():
    """floor, ceiling (with the stair void); in photo mode also the facade glass, the forecourt and the hall floor"""
    carpet = L.mat("carpet", 0x1b1f2e, 0.95, bump=0.25, bump_scale=300)
    ceil = concrete_ceiling()
    vx0, vy0, vx1, vy1 = P.STAIR_VOID
    east = 23.8 if UNIFIED[0] else 30.0
    L.box("floor", -13.6, FACADE, FLOOR - 0.2, 22.85 if UNIFIED[0] else 22.7, NORTH, FLOOR, carpet)
    for name, a, b, c, d in (("w", -13.75, FACADE, vx0, NORTH), ("e", vx1, FACADE, east, NORTH),
                             ("s", vx0, FACADE, vx1, vy0), ("n", vx0, vy1, vx1, NORTH)):
        L.box(f"ceiling-{name}", a, b, CEIL, c, d, 6.2, ceil)
    if UNIFIED[0]:
        return
    L.box("hall-floor", -16, -37.4, -0.2, 25, -30, 0, carpet)
    # glass in every facade opening, from the floor to the ceiling (the plan's bands and mullions sit in front)
    L.box("facade-glass", -13.45, FACADE - 0.12, FLOOR, 22.6, FACADE - 0.1, CEIL, thin_glass())
    # transoms the portrait shows above the plan's bands (3.9 m) and the head frame under the ceiling
    alu = L.mat("alu-dark", 0x2c2e33, 0.4, metal=0.6)
    L.box("transom-3.9", -13.45, FACADE - 0.15, FLOOR + 3.86, 22.6, FACADE + 0.05, FLOOR + 3.94, alu)
    L.box("glazing-head", -13.45, FACADE - 0.15, CEIL - 0.08, 22.6, FACADE + 0.05, CEIL, alu)
    L.box("bof-back", 29.0, FACADE, FLOOR - 0.6, 29.3, -37.4, CEIL, L.mat("bof-dark", 0x3a3d48, 0.9))
    L.box("forecourt", -40, -90, FLOOR - 0.15, 50, FACADE - 0.2, FLOOR - 0.02, L.mat("paving", 0x9a8f86, 0.9))


def closure():
    """whole venue: close the reception except for the hall opening and the facade (outside's skin)"""
    white = L.mat("wall-white", 0, 0)
    dark = L.mat("bof-dark", 0x3a3d48, 0.9)
    # bulkhead over the opening to the hall steps (x -10.55..9.03), from the hall's ceiling up to ours
    L.box("hall-bulkhead", -10.55, -37.55, HALL_CEIL, 9.03, -37.25, CEIL, white)
    # the BOF doorways and the toilet lobby on the east side open into a dark back-of-house, not the sky
    L.box("bof-back", 23.5, FACADE, FLOOR - 0.6, 23.8, NORTH, CEIL, dark)
    L.box("bof-floor", 22.85, FACADE, FLOOR - 0.75, 23.5, NORTH, FLOOR - 0.54, dark)
    # the stair void, capped: its walls rise from floor 1 (6.2) to the top of the upper glazing (9.4)
    vx0, vy0, vx1, vy1 = P.STAIR_VOID
    for name, a, b, c, d in (("w", vx0 - 0.3, vy0, vx0, vy1), ("e", vx1, vy0, vx1 + 0.3, vy1),
                             ("n", vx0 - 0.3, vy1, vx1 + 0.3, vy1 + 0.3)):
        L.box(f"void-wall-{name}", a, b, 6.2, c, d, 9.4, white)
    L.box("void-cap", vx0 - 0.3, FACADE, 9.4, vx1 + 0.3, vy1 + 0.3, 9.7, concrete_ceiling())
    # a header over the BOF line (the plan's walls there stop at 3.86) up to the ceiling
    L.box("bof-header", 22.55, FACADE, 3.86, 22.85, NORTH, CEIL, white)


def queue_west():
    """the entrance queue west of the stair: a three-lane snake of belt posts (x -12.3..-8.4, y -57..-47), in at
    the south end of the first lane by the doors, out at the north end of the third, towards the counter"""
    chrome = L.mat("chrome", 0xd0d0d0, 0.18, 1.0)
    base_m = L.mat("post-base", 0x1a1a1c, 0.35, 0.6)
    belt = L.mat("belt-blue", 0x1b56c8, 0.5)
    H = FLOOR + 0.95
    ys, yn = -57.0, -47.0
    xs = (-12.3, -11.0, -9.7, -8.4)                     # east edge at -8.4: 1.2 m clear of the walk (x -7.0..-7.2)
    lines = [((xs[0], ys), (xs[0], yn)), ((xs[1], ys + 1.4), (xs[1], yn)), ((xs[2], ys), (xs[2], yn - 1.4)),
             ((xs[3], ys + 1.4), (xs[3], yn)), ((xs[0], yn), (xs[2], yn)), ((xs[1], ys), (xs[3], ys))]
    posts = set()
    k = 0
    for (xa, ya), (xb, yb) in lines:
        n = max(1, round(math.hypot(xb - xa, yb - ya) / 1.8))
        pts = [(round(xa + (xb - xa) * t / n, 3), round(ya + (yb - ya) * t / n, 3)) for t in range(n + 1)]
        for p, q in zip(pts, pts[1:]):
            L.tube(f"q-belt{k}", (p[0], p[1], H - 0.03), (q[0], q[1], H - 0.03), 0.025, belt)
            k += 1
        posts.update(pts)
    for j, (x, y) in enumerate(sorted(posts)):
        L.cylinder(f"q-post{j}", x, y, FLOOR + 0.02, H, 0.03, chrome)
        L.cylinder(f"q-post{j}-base", x, y, FLOOR, FLOOR + 0.025, 0.17, base_m, segs=32)
        L.cylinder(f"q-post{j}-head", x, y, H, H + 0.05, 0.035, base_m)


def stair_cladding():
    """the grand stair as a solid piece: a white soffit under the treads where the plan leaves it open
    (y -54.95..-49.25), and a white face where it lands on floor 1"""
    white = L.mat("wall-white", 0, 0)
    under = concrete_ceiling()                          # the underside is the same blue-lit sprayed concrete
    vx0, vy0, vx1, vy1 = P.STAIR_VOID
    n = 60
    for i in range(n):
        y0 = -54.95 + (vy1 + 54.95) * i / n
        y1 = -54.95 + (vy1 + 54.95) * (i + 1) / n
        z = FLOOR + 5.0 * ((y0 + y1) / 2 - vy0) / (vy1 - vy0) - 0.45
        L.box(f"stair-soffit{i}", vx0, y0, z - 0.05, vx1, y1, z, under)
    L.box("stair-head", vx0, vy1 - 0.3, 5.6 - 0.6, vx1, vy1, 6.2, under)


def downlights():
    """whole venue: recessed downlights on a 4 m grid over the reception so the walk is lit end to end"""
    disc = L.emissive("downlight", 0xfff1dc, 12.0)
    vx0, vy0, vx1, vy1 = P.STAIR_VOID
    for x in range(-12, 23, 4):
        for y in range(-58, -38, 4):
            if vx0 - 0.5 < x < vx1 + 0.5 and vy0 - 0.5 < y < vy1 + 0.5:
                continue
            L.cylinder(f"downlight{x}_{y}", x, y, CEIL - 0.01, CEIL, 0.09, disc, segs=16)
            L.spot(f"downlight-light{x}_{y}", (x, y, CEIL - 0.05), (x, y, FLOOR), 320, 80, 0.6, color=(1.0, 0.94, 0.86))


def outside():
    """daylight beyond the glass: a red-leaved tree, green trees, a parked car, low buildings"""
    x, _, _ = px("line", 80, 280, "y", -70)
    F.tree_blob("tree-red", x, -70, FLOOR, 4.5, 1.8, 0xa04050, seed=7)
    for k, tx in enumerate((-4, 8, 18)):
        F.tree_blob(f"tree-green{k}", tx, -72, FLOOR, 6, 2.4, 0x56713a, seed=8 + k)
    L.box("car-blue", x - 2.4, -67.5, FLOOR + 0.2, x - 0.2, -65.7, FLOOR + 1.3, L.mat("car", 0x2a5aa8, 0.3, 0.4))
    L.box("building-opposite", -60, -110, FLOOR, 70, -108, FLOOR + 4, L.mat("building", 0xd8d4cc, 0.8))


def reception():
    """the wide photo's reception: counter, wood slats and TVs against the grand stair's west face (x -2.7),
    the stair's white soffit above them, the pendant and plants over the counter, palms and a banner by the doors,
    registration tables in front of the camera"""
    wide = "entrance_line_wide_angle_with_reception"
    white = L.mat("wall-white", 0, 0)
    wood = L.mat("oak", 0xa98058, 0.55)
    slat_mat = L.mat("oak-slat", 0x8f6a45, 0.6)
    # the reception stands under the grand stair's top end: wood slats on its north face (y -49.25), a white soffit
    # above them, the counter in front (top 1.14 m above the floor at v 281), the plan's column (-4.15, -49.19)
    # the white pillar at u 133-178
    face = STAIR_N + 0.05
    zt = FLOOR + 1.14
    xc, yc, _ = px("wide", 95, 281, "z", zt)
    x_east = 1.0
    L.box("counter", max(xc, -3.4), yc - 0.6, FLOOR, x_east, yc, zt - 0.05, L.mat("counter-white", 0, 0))
    L.box("counter-top", max(xc, -3.4) - 0.03, yc - 0.6, zt - 0.05, x_east, yc + 0.03, zt, wood)
    L.box("counter-kick", max(xc, -3.4), yc - 0.6, FLOOR, x_east, yc - 0.08, FLOOR + 0.08, L.mat("kick", 0x303030, 0.6))
    L.box("counter-printer", -2.6, yc - 0.45, zt, -2.2, yc - 0.15, zt + 0.2, L.mat("printer", 0xdedede, 0.4))
    xb, xo = px("wide", 105, 230, "y", face)[0], px("wide", 133, 230, "y", face)[0]
    top = px("wide", 60, 197, "y", face)[2]
    L.box("slat-backing", xb, STAIR_N - 0.1, FLOOR, x_east + 1.5, face, top, L.mat("slat-back", 0x2a2018, 0.9))
    x, i = xb, 0
    while x < x_east + 1.5:
        L.box(f"slat{i}", x, face, FLOOR, x + 0.045, face + 0.06, top, slat_mat)
        x += 0.075
        i += 1
    L.box("oak-panel", xo, STAIR_N - 0.1, FLOOR, xb, face + 0.02, top, wood)
    L.box("slat-led", xo, face + 0.06, top, x_east + 1.5, face + 0.09, top + 0.03, L.emissive("led-blue", 0x2a48ff, 6.0))
    # TVs: a landscape screen on the slats (u 30-78), a portrait one on the oak panel (u 122-133)
    for name, (u0, u1), m in (("tv-reception", (30, 78), screen_mat("scr-purple", 0x7a2cc8, 0x2e7bff, 2.5)),
                              ("tv-portrait", (122, 133), screen_mat("scr-blue", 0x1c4fd8, 0xc03cc8, 2.5))):
        a, b = px("wide", u0, 205, "y", face + 0.08), px("wide", u1, 232, "y", face + 0.08)
        yq = face + 0.09
        L.quad(name, [(b[0], yq, b[2]), (a[0], yq, b[2]), (a[0], yq, a[2]), (b[0], yq, a[2])], m)
        L.box(name + "-bezel", b[0] - 0.02, face + 0.06, b[2] - 0.02, a[0] + 0.02, yq - 0.005, a[2] + 0.02, L.mat("black-gloss", 0x101012, 0.3))
    # the stair's white soffit over the reception, from the slats' top to its front edge at v 150
    s_top = px("wide", 60, 150, "y", STAIR_N + 0.6)[2]
    L.box("stair-soffit-face", -3.45, STAIR_N, top, x_east + 1.5, STAIR_N + 0.6, s_top, white)
    L.box("stair-soffit-led", -3.45, STAIR_N + 0.6, top, x_east + 1.5, STAIR_N + 0.63, top + 0.03, L.emissive("led-blue", 0, 0))
    # white panel in the facade between the mullions at -4.81 and -2.32 (u 178-290) with a small dark door
    if not UNIFIED[0]:
        x0 = px("wide", 290, 200, "y", FACADE + 0.2)[0]
        L.box("facade-panel", x0, FACADE + 0.15, FLOOR, -2.4, FACADE + 0.3, CEIL, white)
        a, b = px("wide", 196, 207, "y", FACADE + 0.3), px("wide", 190, 226, "y", FACADE + 0.3)
        L.box("facade-door-panel", a[0], FACADE + 0.3, b[2], b[0], FACADE + 0.32, a[2], L.mat("black-gloss", 0, 0))
    # the west wall's box (u 555-575, v 165-200) and the long shelf (v 155-172)
    a, b = px("wide", 575, 165, "x", WEST_IN), px("wide", 555, 200, "x", WEST_IN)
    L.box("wall-box", WEST_IN, b[1], b[2], WEST_IN + 0.3, a[1], a[2], white)
    L.box("wall-box-light", WEST_IN + 0.02, b[1] + 0.05, b[2] - 0.02, WEST_IN + 0.31, a[1] - 0.05, b[2],
          L.emissive("warm-strip", 0xffe2b8, 4.0))
    s0, s1 = px("wide", 640, 155, "x", WEST_IN), px("wide", 555, 172, "x", WEST_IN)
    L.box("wall-shelf", WEST_IN, s1[1], (s0[2] + s1[2]) / 2 - 0.04, WEST_IN + 0.22, s0[1], (s0[2] + s1[2]) / 2 + 0.04, white)
    # exit signs over the doors and on the panel
    sign = L.emissive("exit-green", 0x18c060, 4.0)
    for u, v in ((368, 194), (276, 193)):
        sx, sy, sz = px("wide", u, v, "y", FACADE + 0.35)
        L.box(f"exit-sign-{u}", sx - 0.2, sy - 0.03, sz - 0.1, sx + 0.2, sy, sz + 0.1, sign)
    # tracks and spots on the ceiling, the round pendant hung from the second track's end
    black = L.mat("black-metal", 0x141416, 0.45, 0.5)
    for name, p0, p1 in (("track-a", (0, 45), (110, 100)), ("track-b", (140, 0), (230, 97))):
        a, b = px("wide", *p0, "z", CEIL), px("wide", *p1, "z", CEIL)
        xm = (a[0] + b[0]) / 2
        L.box(name, xm - 0.018, min(a[1], b[1]) - 1.5, CEIL - 0.035, xm + 0.018, max(a[1], b[1]), CEIL, black)
    for k, (u, v) in enumerate(((48, 87), (105, 116))):
        x, y, _ = px("wide", u, v, "z", CEIL - 0.2)
        L.cylinder(f"spot{k}", x, y, CEIL - 0.28, CEIL - 0.08, 0.05, L.mat("spot-white", 0xe8e8e8, 0.4))
    cam = CAMS[wide]
    cx, cy, _ = px("wide", 231, 98, "z", CEIL)
    d = cam.R[:, 2] @ ([cx, cy, CEIL] - cam.C)
    r = 44 * d / cam.f
    cz = cam.height_at((cx, cy, CEIL), 234, 169)
    L.cylinder("pendant", cx, cy, cz - 0.05, cz + 0.05, r, L.mat("pendant-grey", 0xc8c8cc, 0.5), segs=64)
    L.cylinder("pendant-diffuser", cx, cy, cz - 0.056, cz - 0.05, r - 0.03, L.emissive("pendant-light", 0xbfdcff, 9.0), segs=64)
    for a in (0, 2.1, 4.2):
        L.tube(f"pendant-wire{a}", (cx + (r - 0.08) * math.cos(a), cy + (r - 0.08) * math.sin(a), cz + 0.05), (cx, cy, CEIL), 0.003, black)
    # hanging greenery: over the counter, at the soffit's south end, beside the pendant
    for name, (u0, u1, v), axis, val, ln, n in (("plants-reception", (25, 100, 165), "y", STAIR_N + 0.9, 0.9, 60),
                                              ("plants-soffit", (172, 200, 150), "x", STAIR_W - 0.3, 1.4, 30),
                                              ("plants-pendant", (255, 285, 150), "y", cy - 1.2, 1.4, 24)):
        a, b = px("wide", u0, v, axis, val), px("wide", u1, v, axis, val)
        F.hanging(name, a[0], a[1], b[0], b[1], a[2] + 0.15, length=ln, strands=n, seed=len(name), leaf=0.075)
    # palms by the doors and a roll-up banner by the glazing
    x, y, _ = px("wide", 260, 250, "y", FACADE + 0.8)
    if UNIFIED[0]:
        x, y = -3.4, FACADE + 0.9                       # flank the entrance door instead of standing in it
    F.palm("palm-facade-a", x, y, height=1.9, spread=0.8 if not UNIFIED[0] else 0.5, fronds=10, seed=31, pot_h=0.55, z0=FLOOR)
    x, y, _ = px("wide", 420, 240, "y", FACADE + 0.9)
    if UNIFIED[0]:
        x, y = -9.2, FACADE + 0.9                       # west of the door pair (x -8.26..-5.69)
    F.palm("palm-facade-b", x, y, height=2.2, spread=1.1 if not UNIFIED[0] else 0.5, fronds=12, seed=32, pot_h=0.55, z0=FLOOR)
    a, b = px("wide", 455, 195, "y", FACADE + 0.5), px("wide", 470, 232, "y", FACADE + 0.5)
    if UNIFIED[0]:
        a, b = (-12.6, a[1], a[2]), (-13.0, b[1], b[2])
    L.box("banner-frame", b[0], FACADE + 0.48, FLOOR, a[0], FACADE + 0.52, a[2], L.mat("black-gloss", 0, 0))
    L.quad("banner", [(a[0] - 0.02, FACADE + 0.53, FLOOR + 0.2), (b[0] + 0.02, FACADE + 0.53, FLOOR + 0.2),
                      (b[0] + 0.02, FACADE + 0.53, a[2] - 0.03), (a[0] - 0.02, FACADE + 0.53, a[2] - 0.03)],
           screen_mat("banner-print", 0x141c38, 0x5a6a9a, 0.4, 1.0))
    if UNIFIED[0]:
        return                                          # the registration tables stood across the walk
    # registration tables in front of the camera: tablets facing the photographer, black crates
    zt = FLOOR + 0.75
    y0 = px("wide", 320, 418, "z", zt)[1]
    C = cam.C
    L.box("reg-table", C[0] - 4.5, y0 - 0.8, zt - 0.03, C[0] + 4.5, y0, zt, L.mat("table-top", 0x2b2c30, 0.5))
    L.box("reg-skirt", C[0] - 4.5, y0 - 0.8, FLOOR, C[0] + 4.5, y0 - 0.78, zt - 0.03, L.mat("skirt", 0x1c1c20, 0.8))
    for k, (u0, u1, v0, v1) in enumerate(((45, 80, 383, 405), (250, 290, 393, 415), (545, 575, 395, 412))):
        a, b = px("wide", u0, v1, "z", zt + 0.01), px("wide", u1, v1, "z", zt + 0.01)
        h = cam.height_at(a, u0, v0) - zt
        y = a[1] - 0.1
        L.quad(f"tablet{k}", [(b[0], y, zt), (a[0], y, zt), (a[0], y - 0.05, zt + h), (b[0], y - 0.05, zt + h)],
               screen_mat(f"scr-tab{k}", 0xe8f0f0, 0xb8d8c0, 1.4, 0.3))
        L.box(f"tablet{k}-back", b[0], y - 0.1, zt, a[0], y - 0.06, zt + h, L.mat("black-gloss", 0, 0))
    for u0, u1 in ((470, 560), (600, 640)):
        a, b = px("wide", u0, 420, "z", zt), px("wide", u1, 420, "z", zt)
        L.box(f"crate{u0}", b[0], a[1] - 0.4, zt, a[0], a[1], zt + 0.3, L.mat("crate", 0x18181a, 0.6))


def west_bay():
    """the portrait's queue lane along the west wall"""
    chrome = L.mat("chrome", 0xd0d0d0, 0.18, 1.0)
    base_m = L.mat("post-base", 0x1a1a1c, 0.35, 0.6)
    belt = L.mat("belt-blue", 0x1b56c8, 0.5)
    H = FLOOR + 0.95
    posts = {}
    photo_posts = {} if UNIFIED[0] else {"P1": (158, 377), "P2": (304, 366.5), "P3": (330, 405), "P4": (209, 416)}
    for name, (u, v) in photo_posts.items():          # whole venue: the queue snake replaces the photo's posts
        x, y, _ = px("line", u, v, "z", FLOOR)
        if name == "P2":                               # its base is hidden; read it from the belt at its top
            x, y, _ = px("line", 304, 311, "z", H)
        posts[name] = (x, y)
        L.cylinder(f"post-{name}", x, y, FLOOR + 0.02, H, 0.03, chrome)
        L.cylinder(f"post-{name}-base", x, y, FLOOR, FLOOR + 0.025, 0.17, base_m, segs=32)
        L.cylinder(f"post-{name}-head", x, y, H, H + 0.05, 0.035, base_m)
    if posts:
        for a, b in (("P1", "P2"), ("P2", "P3"), ("P3", "P4")):
            (xa, ya), (xb, yb) = posts[a], posts[b]
            L.tube(f"belt-{a}{b}", (xa, ya, H - 0.03), (xb, yb, H - 0.03), 0.025, belt)
        p2 = posts["P2"]
        L.tube("belt-P2-n", (p2[0], p2[1], H - 0.03), (p2[0] + 0.3, p2[1] + 4.0, H - 0.03), 0.025, belt)
        p3 = posts["P3"]
        L.tube("belt-P3-n", (p3[0], p3[1], H - 0.12), (p3[0] - 0.2, p3[1] + 3.0, H - 0.12), 0.025, belt)
    # navy wall: info screen above a dark glazed niche, a palm in front; TV on the white part
    xw = WEST_IN + 0.02
    a, b = px("line", 273.5, 204, "x", xw), px("line", 302.5, 249, "x", xw)
    L.quad("info-screen", [(xw + 0.01, b[1], b[2]), (xw + 0.01, a[1], b[2]), (xw + 0.01, a[1], a[2]), (xw + 0.01, b[1], a[2])],
           screen_mat("scr-info", 0x35557e, 0x8aa6c4, 1.2, 0.6))
    L.box("info-screen-frame", WEST_IN, a[1] - 0.03, b[2] - 0.03, xw, b[1] + 0.03, a[2] + 0.03, L.mat("black-gloss", 0, 0))
    a, b = px("line", 265, 255, "x", xw), px("line", 328, 341, "x", xw)
    L.box("niche-frame", WEST_IN, a[1], FLOOR, xw + 0.04, b[1], a[2], L.mat("niche-frame", 0x202630, 0.4, 0.5))
    L.box("niche-glass", xw + 0.04, a[1] + 0.06, FLOOR + 0.06, xw + 0.05, b[1] - 0.06, a[2] - 0.06, L.mat("niche-dark", 0x06080c, 0.08))
    F.palm("palm-lane", WEST_IN + 0.45, (a[1] + b[1]) / 2 + 0.2, height=1.7, spread=0.5 if UNIFIED[0] else 1.0, fronds=12, seed=21,
           pot=L.mat("pot-white", 0xe8e4dc, 0.5), pot_h=0.5, pot_r=0.25, z0=FLOOR)
    a, b = px("line", 390, 221, "x", xw), px("line", 427, 262, "x", xw)
    L.quad("tv-lane", [(xw + 0.01, a[1] + 1.25, b[2]), (xw + 0.01, a[1], b[2]), (xw + 0.01, a[1], a[2]), (xw + 0.01, a[1] + 1.25, a[2])],
           screen_mat("scr-lane", 0x2a50c8, 0xb03ab8, 2.0, 0.8))
    # palm by the glass, the trailing plants and the dark bulkhead they hang along, the lamp, the garland
    x, y, _ = px("line", 57, 300, "y", FACADE + 2.0)
    if UNIFIED[0]:
        x, y = -12.7, FACADE + 1.0                      # clear of the queue snake's south row
    F.palm("palm-glass", x, y, height=2.3, spread=1.2, fronds=12, seed=22, pot_h=0.6, z0=FLOOR)
    g0, g1 = px("line", 120, 64, "z", CEIL - 0.1), px("line", 250, 64, "z", CEIL - 0.1)
    F.garland("garland", g0, g1, material=L.mat("garland", 0x9aa830, 0.5, emit=0xd8e060, strength=2.0))
    if UNIFIED[0]:
        return                                          # the portrait's foreground props stood in the queue
    hx, hy, _ = px("line", 68, 120, "z", FLOOR + 2.9)
    F.hanging("plants-lane", hx - 0.12, hy - 0.2, hx + 0.12, hy + 0.2, CEIL, length=2.3, strands=34, seed=24, leaf=0.075)
    C = CAMS["entrance_line"].C
    lx, ly, _ = px("line", 8, 180, "z", C[2] + 0.5)
    zt = CAMS["entrance_line"].height_at((lx, ly, 0), 8, 150)
    zb = CAMS["entrance_line"].height_at((lx, ly, 0), 8, 210)
    L.cylinder("lamp-shade", lx, ly, zb, zt, 0.24, L.mat("shade", 0xf4ece0, 0.7, emit=0xffe6c0, strength=1.5), r_top=0.12)
    # the counter corner the portrait is shot over (top 5 cm under the lens) and a closer white table
    # its oak top is a hair above the lens (the oak edge shows from v 280 to 320)
    cx, cy, _ = px("line", 62, 345, "z", C[2] - 0.1)
    L.box("lane-counter", cx, cy - 1.6, FLOOR, cx + 1.2, cy, C[2] - 0.04, L.mat("counter-white", 0, 0))
    L.box("lane-counter-top", cx - 0.02, cy - 1.6, C[2] - 0.04, cx + 1.2, cy + 0.02, C[2] + 0.02, L.mat("oak", 0, 0))
    zt = FLOOR + 0.75
    a, b, c = px("line", 0, 460, "z", zt), px("line", 190, 460, "z", zt), px("line", 330, 640, "z", zt)
    d = (a[0] + c[0] - b[0], a[1] + c[1] - b[1])
    far = (a[0] + (a[0] - b[0]) * 2, a[1] + (a[1] - b[1]) * 2)
    L.prism("lane-table", [(c[0], c[1]), (b[0], b[1]), far, (d[0] + (a[0] - b[0]) * 2, d[1] + (a[1] - b[1]) * 2)][::-1],
            FLOOR, zt, L.mat("counter-white", 0, 0))


def lights():
    if UNIFIED[0]:
        interior_lights()
        return
    # daylight: a bright sky through the glass; the sun is visible in the portrait (u 160, v 222, clear of the
    # corner pier and the 3 m band) and blooms there, but its light comes in steeper so the patches stay near the glass
    L.world_color(0xd4dcea, 10.0)
    d = CAMS["entrance_line"].ray(160, 222)
    h = math.hypot(d[0], d[1])
    steep = (d[0] / h * math.cos(math.radians(42)), d[1] / h * math.cos(math.radians(42)), math.sin(math.radians(42)))
    L.sun("sun", tuple(-c for c in steep), 2.0, color=(1.0, 0.9, 0.76), angle_deg=1.0)
    C = CAMS["entrance_line"].C
    L.sphere("sun-disc", tuple(C[i] + d[i] * 300 for i in range(3)), 4.0, L.emissive("sun-disc", 0xfff2dc, 8000.0))
    # skylight through the glazing, a soft fill pointing north from each bay's facade
    for name, x0, x1, power in (("east", 12.7, 22.6, 150), ("west", -13.45, -2.7, 450)):
        ob = L.area_light(f"glazing-fill-{name}", ((x0 + x1) / 2, FACADE + 0.3, FLOOR + 2.2), x1 - x0, power,
                          color=(0.95, 0.97, 1.0), rot=(math.pi / 2, 0, 0), size_y=4.0)
        hide_from_camera(ob)
    interior_lights()


def interior_lights():
    # blue LED wash on the ceiling (uplights hidden along the walls): the west bay is blue in the wide photo
    for i, (x, y) in enumerate([(-11, -57), (-11, -52), (-11, -47), (-6.5, -57), (-6.5, -52), (-6.5, -47), (-4.5, -42)]):
        ob = L.area_light(f"blue-wash{i}", (x, y, CEIL - 0.9), 3.2, 600, color=(0.2, 0.24, 1.0), rot=(math.pi, 0, 0))
        hide_from_camera(ob)
    # warm spots on the slats and counter, the facade panel and the west wall's box
    rails = [o for o in bpy.data.objects if o.name.startswith("spot") and o.type == "MESH"]
    targets = [(STAIR_W - 0.1, -50.4, FLOOR + 1.6), (STAIR_W - 0.1, -51.4, FLOOR + 1.4)]
    for k, (o, t) in enumerate(zip(rails, targets)):
        x, y = o.data.vertices[0].co.x, o.data.vertices[0].co.y
        L.spot(f"spot-light{k}", (x, y, CEIL - 0.3), t, 400, 40, color=(1.0, 0.9, 0.78))
    L.spot("spot-facade-panel", (-4.5, -55, CEIL - 0.1), (-3.5, FACADE + 0.2, FLOOR + 1.5), 500, 60, color=(1.0, 0.95, 0.88))
    L.spot("spot-west-wall", (-10.5, -55, CEIL - 0.1), (WEST_IN, -57.3, FLOOR + 2.5), 300, 50, color=(1.0, 0.92, 0.8))
    ob = L.area_light("fill-reception", (-6, -50, CEIL - 0.3), 6, 60, color=(0.78, 0.8, 1.0), size_y=8)
    hide_from_camera(ob)
    ob = L.area_light("fill-west", (-10, -54, CEIL - 0.3), 5, 60, color=(0.85, 0.88, 1.0), size_y=8)
    hide_from_camera(ob)


EXPOSURES = {"entrance_line_wide_angle_with_reception": -0.3, "entrance_line": -0.8}
GLARE = {"entrance_line": 0.8, "entrance_line_wide_angle_with_reception": 0.25}


PORTRAIT_PROPS = ("lane-counter", "lane-table", "lamp-shade", "plants-lane")
WIDE_PROPS = ("wall-box", "wall-shelf")                  # read off the west wall in the wide photo; the portrait
                                                        # sees that wall bare, so they only render for the wide one


def before_render(name):
    if UNIFIED[0]:
        return                                          # the whole venue's view settings are not ours
    # the portrait's foreground props sit within a metre or two of its lens and their depth is a guess; the wide
    # photo shows nothing there, so they only render for the portrait
    for ob in bpy.data.objects:
        if ob.name.startswith(PORTRAIT_PROPS):
            ob.hide_render = name != "entrance_line"
        if ob.name.startswith(WIDE_PROPS):
            ob.hide_render = name == "entrance_line"
    scene = bpy.context.scene
    scene.view_settings.exposure = EXPOSURES.get(name, 0.0)
    glare(scene, GLARE.get(name, 0.0))


def build(root, unified=False):
    """unified: one piece of the whole venue (no world, sun, exposure or glare, no facade skin or backdrop,
    nothing north of y -37.4); otherwise the photo-matched set for the two reference cameras"""
    root = Path(root)
    UNIFIED[0] = unified
    ROOT_DIR.append(root)
    cams(root)
    shell()
    plan_geometry(root)
    stair_cladding()
    if unified:
        closure()
        queue_west()
        downlights()
    else:
        outside()
    reception()
    west_bay()
    lights()
