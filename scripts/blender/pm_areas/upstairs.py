"""Upstairs foyer: the floor-1 corridor between auditoriums 6 (west) and 7 (east), looking south at the screen rig
that hangs across it in front of the grand stair. Matched to upstairs_hall.jpg (empty, the master) and
upstairs_w_people.jpg (same axis, 6 m further back), and placed in the venue frame (data/venue/venue.json,
build_scene.py's: metres, +x east, +y north, floor 1 at z = FH = 6.2).

Built in a photo frame (origin on the floor under the master camera, +y = the camera's view = south, +x = its
right = west, z up, scaled 1/S) and moved into the venue frame by to_venue(): venue = (VX - S*x, VY - S*y, FH + S*z).

Plan first: the corridor wall faces (x -7.0 / 12.4), their height (3.2 m) and the door gaps of rooms 6 and 7
(y -45.9..-43.3) come from venue.json; the master camera was resected against them (24 mm lens from the EXIF,
fov 73.7 deg; rotation and horizon from the vanishing lines): it stands at (3.05, -21.44), 1.22 m above floor 1,
rms 4 px. Photo for the rest: each line running along the corridor fixes (z - h) / |x| from where it heads to
the vanishing point, the floor fixes x and y; that gives the sloped soffits, the girders, light boxes, red
portals (6 m frames round the 2.6 m doors), bins and table rows. The screen rig (black backdrop, screen, two
funnels, two black columns) stands at y -47.4, just past the portals; floor 1 ends at the stair void (y -49.25)
and the two-storey glass front (y -60) shows through the gaps under the screen. The second camera was resected
from points on the rig: (3.02, -15.41), 1.0 m above floor 1, rms 13 px of 2480; only it sees the two dark columns
at y -19.3 between the cameras (not in the plan).
"""
import math
from pathlib import Path

import bpy
import pm_lib as L

H_CAM = 1.15
Y_MEAS = 22.77                  # depth at which the end-plane features were first measured (x, z scale with depth)
Y_END = 24.43                   # the screen rig across the corridor, just past the portals (venue y -47.4)
K_END = Y_END / Y_MEAS
Y_VOID = 26.17                  # floor 1 stops: the grand stair's void (venue y -49.25)
Y_FACADE = 36.29                # the glass front of the building (venue y -60)
Y_NEAR = -14.0                  # the hall continues behind the cameras
XL, XR = -8.80, 9.45            # corridor wall faces from the plan (venue x 12.4 east, -7.0 west)
Z_WALL = 3.01                   # plan wall height 3.2 m
# beams (big girders under the soffit edge): inner face bottom/top, outer bottom, outer top
BEAM_L = dict(xi0=-3.63, xi1=-3.63, xo=-4.13, z0=5.24, z1=7.65)
BEAM_R = dict(xi0=4.35, xi1=4.35, xo=4.9, z0=5.24, z1=7.65)
Z_CEIL = 8.6
# local -> venue: venue = (VX - S*x, VY - S*y, FH + S*z), i.e. turned half round, scaled by S, moved
FH, S, VX, VY = 6.2, 1.222 / 1.15, 3.045, -21.438
UNIFIED = [False]
NORTH_Y = 65.7                   # unified: the corridor runs north to the plan's end (venue y), past the panorama at 28
# unified: every auditorium door off this corridor (venue y of the door centre, from venue.json's doorSide/doorMargin
# like build_scene.py; rooms 6/7 keep their photo-matched portals). West wall = this frame's XR, east = XL
DOORS = {"west": {1: 39.95, 2: 15.15, 3: 11.35, 4: -17.45, 5: -22.35},
         "east": {8: -22.35, 9: -4.55, 10: 11.35, 11: 22.55, 12: 27.45, 13: 50.75, 14: 55.65}}
STAIR_VOIDS = ((-7.15, -4.85), (10.25, 12.55))   # venue x of the side stair openings, y -1.32 .. 9.88


def loc_y(yv):
    return (VY - yv) / S


def loc_x(xv):
    return (VX - xv) / S


def E(x, z):
    """an end-plane feature measured at Y_MEAS, pushed back to Y_END along its sight line"""
    return x * K_END, H_CAM + (z - H_CAM) * K_END


VIEW_TRANSFORM = "Khronos PBR Neutral"   # keeps the LED blue saturated where AgX pales it to white
LOOK = "None"
EXPOSURE = 0.0


def tex(root, name):
    return Path(root) / "build" / "photomatch" / "upstairs" / "tex" / f"{name}.png"


def fabric():
    """the tensile funnels: stretched translucent fabric, navy at the pinch rising to a lit blue at the rim"""
    m = bpy.data.materials.new("up-funnel")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.2
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = L.srgb(0x0a0f2e)
    ramp.color_ramp.elements[1].color = L.srgb(0x4a62d8)
    ramp.color_ramp.elements[1].position = 0.9
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    # light through the cloth from the blue wash behind
    b.inputs["Subsurface Weight"].default_value = 0.0
    trans = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(ramp.outputs["Color"], trans.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.35
    out = nt.nodes["Material Output"]
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(trans.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = L.srgb(0x1a2a70)
    return m


def lathe(name, profile, cx, cy, mat, segs=40):
    """a surface of revolution about a vertical axis: profile [(radius, z), ...] from bottom to top"""
    verts, faces = [], []
    n = len(profile)
    for k in range(segs):
        a = 2 * math.pi * k / segs
        verts += [(cx + r * math.cos(a), cy + r * math.sin(a), z) for r, z in profile]
    for k in range(segs):
        for i in range(n - 1):
            a0, a1 = k * n + i, ((k + 1) % segs) * n + i
            faces.append((a0, a1, a1 + 1, a0 + 1))
    ob = L.mesh_obj(name, verts, faces, mat, smooth=True)
    return ob


def carpet(root):
    """the dark speckled carpet: ambientCG Carpet016's fibre detail, multiplied down to the photos' colour and
    flecked with lighter grey, box-mapped in world space at 0.5 m"""
    d = Path(root) / "data" / "textures" / "carpet"
    m = bpy.data.materials.new("up-carpet")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.05
    coord, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    col = nt.nodes.new("ShaderNodeTexImage")
    col.image = bpy.data.images.load(str(d / "color.jpg"), check_existing=True)
    nt.links.new(mp.outputs["Vector"], col.inputs["Vector"])
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    nt.links.new(col.outputs["Color"], tint.inputs["A"])
    tint.inputs["B"].default_value = L.srgb(0x48405a)
    # light flecks in the pile
    fleck = nt.nodes.new("ShaderNodeTexNoise")
    fleck.inputs["Scale"].default_value = 2600.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.6, 0.75
    nt.links.new(fleck.outputs["Fac"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = L.srgb(0x645a62)
    nt.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    nt.links.new(tint.outputs["Result"], mix.inputs["A"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = bpy.data.images.load(str(d / "normal.jpg"), check_existing=True)
    nrm.image.colorspace_settings.name = "Non-Color"
    nt.links.new(mp.outputs["Vector"], nrm.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nrm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = L.srgb(0x3a2a26)
    return m


def build(root, unified=False):
    global Y_NEAR
    UNIFIED[0] = unified
    before = set(bpy.data.objects)
    if unified:
        Y_NEAR = loc_y(NORTH_Y)
    M = {
        "carpet": carpet(root),
        "blue": L.mat("up-wall-blue", 0x00185c, 0.75),
        "white": L.mat("up-soffit", 0xeeeef0, 0.85),
        "beam": L.mat("up-beam", 0xa9aab0, 0.7),
        "black": L.mat("up-black", 0x07080e, 0.9),
        "dark": L.mat("up-dark", 0x141418, 0.8),
        "red": L.mat("up-red", 0xc8031a, 0.45),
        "steel": L.mat("up-steel", 0xb8bcc2, 0.25, metal=1.0),
        "rail": L.mat("up-rail", 0x1a1a1c, 0.4, metal=0.6),
        "lamp": L.mat("up-lamp", 0x151517, 0.35, metal=0.5),
        "cloth": L.mat("up-tablecloth", 0x1b2236, 0.9),
        "chair": L.mat("up-chair", 0x101318, 0.45, metal=0.4),
        "funnel": fabric(),
        "glass": L.emissive("up-window", 0x8fd8f0, 1.6),
        "led": L.emissive("up-led-blue", 0x1a30ff, 3.0),
        "underglow": L.mat("up-underside", 0x2a2c34, 0.7),
        "panel_l": L.image_mat("up-quote-l", tex(root, "quote-left"), strength=3.0, rough=0.4),
        "panel_r": L.image_mat("up-quote-r", tex(root, "quote-right"), strength=3.0, rough=0.4),
        "screen": L.image_mat("up-screen", tex(root, "screen"), strength=2.2, emit_only=True),
        "pend": L.emissive("up-pendant", 0xf4f6ff, 8.0),
        "spotlens": L.emissive("up-spot-lens", 0xfff2dc, 14.0),
        "poster": L.mat("up-poster", 0x8fa4c8, 0.6, emit=0x8fa4c8, strength=0.5),
    }
    if unified:
        floor_with_holes(M)
    else:
        L.box("floor", XL - 0.3, Y_NEAR, -0.1, XR + 0.3, Y_VOID, 0, M["carpet"])
    # beyond the void edge: the grand stair going down, floor 0, and the two-storey glass front in daylight
    zf0 = -FH / S
    L.box("void-edge", XL, Y_VOID - 0.05, -0.25, XR, Y_VOID, 0, M["dark"])
    if not unified:
        photo_backdrop(root, M, zf0)
    walls_and_portals(M)
    rest_of_build(root, M, unified)
    if unified:
        north_lights()
        cones(M)
        y = Y_NEAR                                     # the corridor's north end: a closed wall (background only)
        L.box("north-end", XL - 0.3, y - 0.3, 0, XR + 0.3, y, Z_CEIL, M["blue"])
        L.box("north-end-band", XL, y + 0.01, 2.2, XR, y + 0.03, 2.35, L.emissive("up-north-band", 0xfff0dc, 3.0))
    to_venue(None if not unified else set(bpy.data.objects) - before)


def photo_backdrop(root, M, zf0):
    """photo mode only: what the photos see past the void (the entrance and outside areas build it for real)"""
    L.mesh_obj("grand-stair", [(XL, Y_VOID, -0.25), (XR, Y_VOID, -0.25), (XR, Y_FACADE - 0.5, zf0 + 0.2), (XL, Y_FACADE - 0.5, zf0 + 0.2)],
               [(0, 1, 2, 3)], L.mat("up-stair", 0x2a2a30, 0.8))
    L.box("floor-0", XL - 3, Y_VOID, zf0 - 0.1, XR + 3, Y_FACADE, zf0, L.mat("up-floor0", 0x6a6a70, 0.6))
    # glass front: mullions every 2.45 m (plan), transoms, and the cool daylit street beyond
    mull = L.mat("up-mullion", 0x2c3038, 0.5, metal=0.6)
    xm_ = XL - 1
    while xm_ < XR + 1:
        L.box("mullion", xm_ - 0.05, Y_FACADE, zf0, xm_ + 0.05, Y_FACADE + 0.15, Z_WALL, mull)
        xm_ += 2.45 / S
    for zt_ in (zf0 + 0.4, zf0 + 2.6, -0.25, 0.42, 1.42, 2.3):
        L.box("transom", XL - 1, Y_FACADE, zt_ - 0.04, XR + 1, Y_FACADE + 0.15, zt_ + 0.04, mull)
    L.quad("exterior", [(XR + 30, Y_FACADE + 25, zf0 - 2), (XL - 30, Y_FACADE + 25, zf0 - 2), (XL - 30, Y_FACADE + 25, zf0 + 22),
                        (XR + 30, Y_FACADE + 25, zf0 + 22)], L.image_mat("up-exterior", tex(root, "exterior"), strength=1.6, emit_only=True))


def walls_and_portals(M):
    # ------------------------------------------------------------------ side walls, light boxes, portals
    if UNIFIED[0]:
        open_wall("wall-l", XL - 0.3, XL, [loc_y(y) for n, y in DOORS["east"].items() if n in walk_rooms()] + ([loc_y(-44.55)] if 7 in walk_rooms() else []), M)
        open_wall("wall-r", XR, XR + 0.3, [loc_y(y) for n, y in DOORS["west"].items() if n in walk_rooms()] + ([loc_y(-44.55)] if 6 in walk_rooms() else []), M)
    else:
        L.box("wall-l", XL - 0.3, Y_NEAR, 0, XL, Y_END, Z_WALL, M["blue"])
        L.box("wall-r", XR, Y_NEAR, 0, XR + 0.3, Y_END, Z_WALL, M["blue"])
    if UNIFIED[0]:
        for side, x, face, doors in (("r", XR, -1, DOORS["west"]), ("l", XL, 1, DOORS["east"])):
            for num, yv in doors.items():
                portal(M, f"{side}{num}", x, face, loc_y(yv), str(num), open_door=num in walk_rooms())
    # quote light boxes, set 4 cm proud of the wall
    for name, x, face, y0, y1, mat in (("quote-l", XL, 1, 12.38, 16.94, M["panel_l"]),
                                      ("quote-r", XR, -1, 11.98, 16.77, M["panel_r"])):
        xf = x + 0.05 * face
        L.box(f"{name}-box", x, y0 - 0.06, 0.41, xf, y1 + 0.06, 2.35, M["dark"])
        z0, z1 = 0.47, 2.29
        if face > 0:
            c = [(xf + 0.002, y1, z0), (xf + 0.002, y0, z0), (xf + 0.002, y0, z1), (xf + 0.002, y1, z1)]
        else:
            c = [(xf - 0.002, y0, z0), (xf - 0.002, y1, z0), (xf - 0.002, y1, z1), (xf - 0.002, y0, z1)]
        L.quad(name, c, mat)
        L.area_light(f"{name}-glow", (xf + 0.6 * face, (y0 + y1) / 2, 1.35), 1.0, 60,
                     color=(0.92, 0.95, 1.0), rot=(0, -math.pi / 2 * face, 0), size_y=3.5)
    # red auditorium portals: a red frame proud of the wall, a dark door recess, the room number
    # red auditorium portals (photo) round the door gaps (plan: venue y -45.9..-43.3 in both walls)
    gap0, gap1 = (VY + 43.3) / S, (VY + 45.9) / S
    for side, x, face, y0, y1, num in (("l", XL, 1, 18.75, 24.45, "7"), ("r", XR, -1, 18.85, 24.45, "6")):
        # the blue wall stops a metre before the portal: dark wall between
        L.box(f"wall-gap-{side}", x - 0.01 * face, 17.7, 0, x + 0.01 * face, y0, Z_WALL, M["dark"])
        xf = x + 0.18 * face
        L.area_light(f"portal-light-{side}", (x + 1.5 * face, (y0 + y1) / 2, 3.2), 1.0, 250, color=(1.0, 0.85, 0.75),
                     rot=(0, math.radians(-50) * face, 0), size_y=y1 - y0)
        if UNIFIED[0] and int(num) in walk_rooms():   # the walk to this room goes through: an open doorway
            L.box(f"portal-{side}", x, y0, 0, xf, gap0, 2.6, M["red"])
            L.box(f"portal-{side}", x, gap1, 0, xf, y1, 2.6, M["red"])
            L.box(f"portal-{side}-head", x, gap0, DOOR_H, xf, gap1, 2.6, M["red"])
        else:
            L.box(f"portal-{side}", x, y0, 0, xf, y1, 2.6, M["red"])
            L.box(f"portal-{side}-door", xf - 0.01 * face, gap0, 0, xf + 0.01 * face, gap1, 2.05, M["black"])
            L.box(f"portal-{side}-leaf", xf, gap0 + 0.08, 0.05, xf + 0.02 * face, gap1 - 0.08, 2.0, M["dark"])
        za, zb = (gap1, y1) if face > 0 else (y0, gap0)
        room_number(f"portal-{side}-num", num, xf, face, za, zb)


def rest_of_build(root, M, unified):
    # ------------------------------------------------------------------ soffits and beams
    for side, xw, b in (("l", XL, BEAM_L), ("r", XR, BEAM_R)):
        s = 1 if b["xo"] > 0 else -1
        # sloped white soffit from the wall top up to the beam's outer bottom edge
        a0, a1 = (xw, Z_WALL), (b["xo"], b["z0"])
        v = [(a0[0], Y_NEAR, a0[1]), (a1[0], Y_NEAR, a1[1]), (a1[0], Y_END, a1[1]), (a0[0], Y_END, a0[1])]
        L.mesh_obj(f"soffit-{side}", v, [(0, 1, 2, 3)], M["white"])
        # the girder: inner face leaning out a little, bottom, outer face up into the dark ceiling
        sec = [(b["xi0"], b["z0"]), (b["xo"], b["z0"]), (b["xo"], b["z1"]), (b["xi1"], b["z1"])]
        verts = [(x, Y_NEAR, z) for x, z in sec] + [(x, Y_END, z) for x, z in sec]
        n = len(sec)
        faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)] + [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        L.mesh_obj(f"beam-{side}", verts, faces, M["beam"])
        # dark cable channel and the blue LED strip along the girder's outer bottom edge
        L.box(f"channel-{side}", b["xo"] - 0.02 * s, Y_NEAR, b["z0"] - 0.12, b["xo"] + 0.14 * s, Y_END - 0.1, b["z0"], M["rail"])
        led = L.box(f"led-{side}", b["xo"] + 0.0 * s, Y_NEAR, b["z0"] - 0.14, b["xo"] + 0.12 * s, Y_END - 0.1, b["z0"] - 0.12, M["led"])
        led.visible_diffuse = led.visible_glossy = False
        # the girder's underside glows blue: LED tape behind a diffuser along its whole length
        zb = b["z0"] - 0.004
        glow = L.mesh_obj(f"beam-under-{side}", [(b["xi0"], Y_NEAR, zb), (b["xo"], Y_NEAR, zb), (b["xo"], Y_END, zb), (b["xi0"], Y_END, zb)],
                          [(0, 1, 2, 3)], M["underglow"])
        L.box(f"tray-{side}", b["xi0"] - 0.0 * s, Y_NEAR, b["z0"] - 0.1, b["xi0"] + 0.16 * s, Y_END - 0.05, b["z0"] - 0.005, M["rail"])
        # seen, but its light on the soffit is the wash light's job (a close emitter blows the soffit out to white)
        # the strip's light washing the soffit: a long area light just outside the girder, aimed outwards/up
        # hidden LED strip at the girder's outer bottom edge, aimed down the soffit (grazing it, tilted 12 deg in), so
        # the blue is strongest at the girder and fades out over a metre or two
        dx, dz = xw - b["xo"], Z_WALL - b["z0"]
        ang = math.atan2(dz, abs(dx)) + math.radians(12)          # below horizontal is negative
        vx, vz = math.copysign(math.cos(ang), dx), math.sin(ang)
        L.area_light(f"led-wash-{side}", (b["xo"] + 0.06 * s, (Y_NEAR + Y_END) / 2, b["z0"] - 0.16), 0.04, 450,
                     color=(0.0, 0.13, 1.0), rot=(0, math.atan2(-vx, -vz), 0), size_y=Y_END - Y_NEAR, spread=math.radians(110))
        # white light on the lower soffit and the wall tops: uplight bounce off the spots
        xm = b["xo"] + 0.92 * (xw - b["xo"])
        L.area_light(f"soffit-fill-{side}", (xm, (Y_NEAR + Y_END) / 2, 1.6), 2.4, 2000, color=(0.97, 0.97, 1.0),
                     rot=(math.pi, 0, 0), size_y=Y_END - Y_NEAR, spread=math.radians(32))
    # dark ceiling over the middle and above the soffits
    L.box("ceiling", -12, Y_NEAR, Z_CEIL, 12, Y_FACADE, Z_CEIL + 0.2, L.mat("up-ceiling", 0x10142e, 0.9, emit=0x1a2260, strength=0.012))

    # ------------------------------------------------------------------ the screen rig across the corridor
    # black backdrop wall to wall with gaps low down, through which the glass front shows past the stair void
    holes = [(-1.3, 1.74), (-3.35, -3.15), (-2.3, -2.1), (2.0, 2.35), (3.1, 3.35), (4.95, 5.35), (-7.6, -6.85)]
    holes = sorted((E(a, 0)[0], E(b, 0)[0]) for a, b in holes)
    zh0, zh1 = E(0, 0.2)[1], E(0, 1.5)[1]
    L.box("rig-top", XL, Y_END, zh1, XR, Y_END + 0.3, Z_CEIL, M["black"])
    L.box("rig-foot", XL, Y_END, 0, XR, Y_END + 0.3, max(zh0, 0.05), M["black"])
    x = XL
    for a, b in holes:
        L.box("rig-pier", x, Y_END, zh0, a, Y_END + 0.3, zh1, M["black"])
        x = b
    L.box("rig-pier", x, Y_END, zh0, XR, Y_END + 0.3, zh1, M["black"])
    x0c, z0c = E(-1.18, 3.24)
    x1c, z1c = E(1.74, 3.63)
    L.box("clerestory", x0c, Y_END - 0.02, z0c, x1c, Y_END + 0.02, z1c, M["glass"])
    for a, b in ((-4.08, -3.4), (4.2, 4.89)):
        L.box("end-column", E(a, 0)[0], Y_END - 0.7, 0, E(b, 0)[0], Y_END, E(0, 5.24)[1], M["black"])
    # white sheet-metal boxes where the girders meet the rig, a white pipe bending down out of each
    for a, b in ((-3.52, -3.02), (4.22, 4.72)):
        (xa, za), (xb, zb) = E(a, 5.22), E(b, 7.65)
        L.box("beam-end-box", xa, Y_END - 0.6, za, xb, Y_END, zb, L.mat("up-endbox", 0xc9cad0, 0.6))
        xp = xa - 0.12 if xa < 0 else xb + 0.12
        L.tube("beam-end-pipe", (xp, Y_END - 0.3, zb - 0.05), (xp, Y_END - 0.3, za - 0.17), 0.06, L.mat("up-endbox", 0xc9cad0, 0.6))
    # projection screen: roller case on top, white border round the picture
    (xa, za), (xb, zb) = E(-2.3, 6.62), E(3.18, 6.9)
    L.box("screen-case", xa, Y_END - 0.55, za, xb, Y_END - 0.3, zb, L.mat("up-frame", 0xb9bbc2, 0.5))
    (xa, za), (xb, zb) = E(-2.26, 3.91), E(3.14, 6.62)
    L.box("screen-frame", xa, Y_END - 0.45, za, xb, Y_END - 0.42, zb, L.mat("up-screen-border", 0xd8d9de, 0.7))
    (xa, za), (xb, zb) = E(-2.12, 4.0), E(3.0, 6.52)
    yq = Y_END - 0.455
    L.quad("screen", [(xa, yq, za), (xb, yq, za), (xb, yq, zb), (xa, yq, zb)], M["screen"])
    # the two fabric cones either side under the screen (the corridor's cones, form-found the same way: John 17/10):
    # set back between the columns and the backdrop, so the columns cover their outer edges as in the photo; six
    # corners at the rig's underside, the back ones tied to the backdrop's face; hoop and spike below, the spike's tip
    # clear above head height
    zt = E(0, 3.87)[1] - CONE_CLEAR / S
    sail = cone_fabric(lit=False)
    for k, (xc, r) in enumerate(((-1.93, 1.03), (2.59, 1.09))):
        xf, ya, rt = E(xc, 1.63)[0], Y_END - 0.35, r * K_END
        corners = []
        for j in range(6):
            th = math.radians(30 + 60 * j)
            x, y = xf + rt * math.cos(th), min(ya + rt * math.sin(th), Y_END - 0.05)
            corners.append((x, y, zt))         # (no wires: from the corridor they'd cross the lit screen)
        fabric_cone(f"rig-cone-{k}", xf, ya, corners, sail, tip=RIG_CONE_TIP, ring=RIG_CONE_RING, ring_r=0.3)
    # posters and a lit cabinet at the rig's ends
    (xa, za), (xb, zb) = E(-6.78, 0.21), E(-4.24, 2.26)
    L.box("poster-l-back", xa - 0.02, Y_END - 0.1, za - 0.02, xb + 0.02, Y_END - 0.06, zb + 0.02, M["dark"])
    L.quad("poster-l", [(xa, Y_END - 0.105, za), (xb, Y_END - 0.105, za), (xb, Y_END - 0.105, zb), (xa, Y_END - 0.105, zb)],
           L.image_mat("up-poster-l", tex(root, "poster-left"), strength=0.8))
    (xa, za), (xb, zb) = E(5.0, 0.3), E(6.4, 1.75)
    L.box("poster-r", xa, Y_END - 0.1, za, xb, Y_END - 0.05, zb, L.mat("up-poster-r", 0x4a3a8a, 0.6, emit=0x4a3a8a, strength=0.4))
    (xa, za), (xb, zb) = E(6.4, 0.0), E(7.5, 1.6)
    L.box("cabinet-r", xa, Y_END - 0.5, 0.0, xb, Y_END - 0.05, zb, L.mat("up-cabinet", 0x5d8ad0, 0.4, emit=0x6d9ae0, strength=0.6))
    # projector on a pole from the dark ceiling
    L.cylinder("projector-pole", 0.5, 17.5, 7.3, Z_CEIL, 0.04, M["rail"])
    L.box("projector", 0.15, 17.2, 7.0, 0.85, 17.9, 7.3, M["lamp"])

    # ------------------------------------------------------------------ the near gateway (only the second photo sees it)
    # two dark columns between the cameras with signage screens on their fronts, a bin beside the left one
    for x0, x1 in ((-3.0, -1.56), (1.82, 3.2)):
        L.box("gate-column", x0, -2.24, 0, x1, -1.79, Z_CEIL, L.mat("up-gate", 0x050508, 0.9))
        # on the side facing the aisle: a framed floor plan and a green exit sign above it
        xs, f = (x1 + 0.01, 1) if x0 < 0 else (x0 - 0.01, -1)
        L.box("floorplan-frame", xs, -2.200, 1.0, xs + 0.015 * f, -1.840, 1.38, L.mat("up-frame-white", 0xe8e8ec, 0.5))
        L.box("floorplan", xs + 0.016 * f, -2.170, 1.03, xs + 0.017 * f, -1.870, 1.35, L.mat("up-floorplan", 0xb8bcc4, 0.7))
        L.box("exit-sign", xs, -2.140, 1.44, xs + 0.03 * f, -1.940, 1.56, L.emissive("up-exit", 0x20c060, 2.0))
    L.quad("totem-cinema", [(-2.41, -2.295, 0.43), (-1.79, -2.295, 0.43), (-1.79, -2.295, 1.51), (-2.41, -2.295, 1.51)],
           L.image_mat("up-totem-cinema", tex(root, "totem-cinema"), strength=1.5, rough=0.3))
    L.box("totem-cinema-bezel", -2.45, -2.290, 0.39, -1.75, -2.270, 1.55, M["black"])
    L.quad("totem-livedooh", [(2.37, -2.295, 0.98), (3.05, -2.295, 0.98), (3.05, -2.295, 1.36), (2.37, -2.295, 1.36)],
           L.image_mat("up-totem-livedooh", tex(root, "totem-livedooh"), strength=1.5, rough=0.3))
    L.box("totem-livedooh-bezel", 2.34, -2.290, 0.95, 3.08, -2.270, 1.39, M["black"])
    L.cylinder("bin", -1.14, -2.44, 0.0, 0.86, 0.17, M["steel"], segs=24)
    L.cylinder("bin-lid", -1.14, -2.44, 0.86, 0.89, 0.175, M["rail"], segs=24)

    # ------------------------------------------------------------------ bins
    for x, y in ((-2.66, 15.34), (-2.23, 15.33), (2.74, 15.18), (3.17, 15.17)):
        L.cylinder("bin", x, y, 0.0, 0.86, 0.17, M["steel"], segs=24)
        L.cylinder("bin-lid", x, y, 0.86, 0.89, 0.175, M["rail"], segs=24)

    # ------------------------------------------------------------------ tables and folding chairs
    build_seating(M)

    # ------------------------------------------------------------------ track spots and linear pendants
    build_rails(M)

    # ------------------------------------------------------------------ light
    if not unified:                                   # the venue's own daylight world stays
        L.world_color(0x000000, 0.0)
    L.area_light("hall-fill", (0.35, 8, 7.0), 5, 120, color=(1.0, 0.92, 0.88), rot=(0, 0, 0), size_y=26)
    # blue uplight over the screen: the dark ceiling's navy glow
    L.area_light("ceiling-blue", (0.35, 17.0, 6.9), 3.0, 300, color=(0.15, 0.25, 1.0), rot=(math.pi, 0, 0), size_y=8)
    # warm downlight over the aisle and the tables (the photos' floor is warm, not blue)
    L.area_light("aisle-warm", (0.35, 6, 8.4), 5, 1300, color=(1.0, 0.86, 0.78), rot=(0, 0, 0), size_y=20, spread=math.radians(60))
    # blue light catching the funnels from the front, as the stage wash does in the photo
    L.area_light("funnel-wash", (0.4, Y_END - 4.0, 0.6), 3.0, 600, color=(0.05, 0.18, 1.0),
                 rot=(math.radians(110), 0, 0), size_y=1.0, spread=math.radians(28))
    L.area_light("near-warm", (0.35, -3.5, 5.0), 4, 650, color=(1.0, 0.82, 0.66), rot=(0, 0, 0), size_y=5, spread=math.radians(70))
    if not unified:                                   # the real glass front lets the venue's daylight in
        L.area_light("window-day", (0, Y_END + 1.5, 2.0), 4, 1500, color=(0.85, 0.95, 1.0), rot=(math.pi / 2, 0, 0))


def floor_with_holes(M):
    """unified: the corridor floor with the two side stair openings left open (stairs.py builds what's in them)"""
    y_open0, y_open1 = loc_y(9.88), loc_y(-1.32)          # local y grows southwards: north end first
    xs = sorted([XL - 0.3, XR + 0.3] + [loc_x(v) for xv in STAIR_VOIDS for v in xv])
    # strips across x between the openings' edges: full length where no opening, split around them where there is
    for xa, xb in zip(xs, xs[1:]):
        cx = (xa + xb) / 2
        in_void = any(min(loc_x(a), loc_x(b)) < cx < max(loc_x(a), loc_x(b)) for a, b in STAIR_VOIDS)
        if not in_void:
            L.box("floor", xa, Y_NEAR, -0.1, xb, Y_VOID, 0, M["carpet"])
        else:
            L.box("floor", xa, Y_NEAR, -0.1, xb, y_open0, 0, M["carpet"])
            L.box("floor", xa, y_open1, -0.1, xb, Y_VOID, 0, M["carpet"])


NUM_H = 1.65                     # the portals' room numbers: Big Shoulders Black, 1.65 m tall (Street View: ~60% of
NUM_Z = 1.48                     # the panel's height, bold condensed geometric figures), centred at 1.48 m


def room_number(name, num, xf, face, ya, yb):
    """a room number on a portal's face, centred in the stretch ya..yb (local y) beside the door"""
    font = Path(__file__).resolve().parents[1] / "fonts" / "BigShouldersDisplay-Black.ttf"
    t = L.text(name, num, 1.0, (xf + 0.004 * face, (ya + yb) / 2, NUM_Z / S), (math.pi / 2, 0, math.pi / 2 * face),
               L.mat("up-num", 0xffffff, 0.5), extrude=0.004, font=font, align="CENTER")
    t.data.align_y = "CENTER"
    bpy.context.view_layer.update()
    k = (NUM_H / S) / max(1e-6, t.dimensions.y)              # upright text: local y is the letter height
    k = min(k, 0.92 * abs(yb - ya) / max(1e-6, t.dimensions.x))   # and it must fit beside the door
    t.scale = (k, k, 1.0)
    return t


def walk_rooms():
    """the room whose doorway is open: only the room walk's own (venue.ROOM); every other portal keeps its closed door
    (cinema doors are shut, and only that auditorium is loaded: auditoriums.py)"""
    import pm_areas.venue as V
    return (V.ROOM,) if V.ROOM else ()
DOOR_W, DOOR_H = 2.6 / S, 2.25 / S             # the walks' doorways: open, the auditorium beyond (auditoriums.py)


def open_wall(name, xa, xb, door_ys, M):
    """a corridor wall with open doorways (DOOR_W x DOOR_H) at the given local y centres"""
    ys = sorted(door_ys)
    y = Y_NEAR
    for yc in ys:
        L.box(name, xa, y, 0, xb, yc - DOOR_W / 2, Z_WALL, M["blue"])
        L.box(f"{name}-lintel", xa, yc - DOOR_W / 2, DOOR_H, xb, yc + DOOR_W / 2, Z_WALL, M["blue"])
        y = yc + DOOR_W / 2
    L.box(name, xa, y, 0, xb, Y_END, Z_WALL, M["blue"])


def portal(M, tag, x, face, yc, num, half=2.85, gap=2.6 / S, open_door=False):
    """a red portal proud of the wall round a door (as rooms 6/7 in the photos), door recess, leaf, number, light"""
    y0, y1 = yc - half, yc + half
    xf = x + 0.18 * face
    L.area_light(f"portal-light-{tag}", (x + 1.5 * face, yc, 3.2), 1.0, 250, color=(1.0, 0.85, 0.75),
                 rot=(0, math.radians(-50) * face, 0), size_y=y1 - y0)
    g0, g1 = yc - gap / 2, yc + gap / 2
    if open_door:                                 # a doorway through the portal's frame: the walk goes in here
        L.box(f"portal-{tag}", x, y0, 0, xf, g0, 2.6, M["red"])
        L.box(f"portal-{tag}", x, g1, 0, xf, y1, 2.6, M["red"])
        L.box(f"portal-{tag}-head", x, g0, DOOR_H, xf, g1, 2.6, M["red"])
    else:
        L.box(f"portal-{tag}", x, y0, 0, xf, y1, 2.6, M["red"])
        L.box(f"portal-{tag}-door", xf - 0.01 * face, g0, 0, xf + 0.01 * face, g1, 2.05, M["black"])
        L.box(f"portal-{tag}-leaf", xf, g0 + 0.08, 0.05, xf + 0.02 * face, g1 - 0.08, 2.0, M["dark"])
    # the number in the stretch beyond the door (Street View: door on one side, the number on the other)
    za, zb = (g1, y1) if face > 0 else (y0, g0)
    room_number(f"portal-{tag}-num", num, xf, face, za, zb)


def north_lights():
    """unified: the photos' warm aisle light repeated up the corridor north of the photo-matched stretch"""
    y = -8.0
    while y > Y_NEAR + 4:
        L.area_light(f"aisle-warm-n{int(-y)}", (0.35, y, 8.4), 5, 1300, color=(1.0, 0.86, 0.78), rot=(0, 0, 0), size_y=12,
                     spread=math.radians(60))
        y -= 13.0


# unified: the corridor's columns north of the 2026 gate columns (y -19.3), measured from the Street View panorama's
# feet (the wide and zoomed views, 16/10): two rows, under the girders (west ~ -1.7, east ~ 7.1), not a regular grid.
# The panorama was moved 1.2 m west on 16/10 (data/photomatch/cal/streetview_upstairs.json, venue_solve) so that the
# rows carry the girders as the photos show; that also balances the two corridor walls' bases in h164/h334 (both
# ~50 px low: the camera height or the horizon bias is still a little off). The pair at y 30.75 stands right beside the
# panorama, outside the wide views: fitted to the close-up's two faces and to the east one's faces and foot in
# sv_202006_h334; the west one at y -12.3 is col 4's partner, seen in h80.
COLUMNS = [(-1.7, 12.1), (-1.6, 4.3), (7.1, 12.1), (7.2, 6.5), (7.7, -12.3), (-0.9, 38.2), (6.6, 38.2), (-0.7, 52.0),
           (6.7, 52.0), (-0.15, 30.75), (6.5, 30.75), (-1.6, -12.3)]
# the cones hang only on some columns: these pairs carry the girders bare in the photos (h80: the near pair at 12.1;
# h262 and the close-up: 38.2 and 52.0); cones at 4.3/6.5 (h80's two big ones), -12.3 (h80's next pair) and beside the
# panorama (30.75). Further south, past the 2026 gate, the 2026 master photo rules (h80 shows more cones there in 2020).
PLAIN = {(-1.7, 12.1), (7.1, 12.1), (-0.9, 38.2), (6.6, 38.2), (-0.7, 52.0), (6.7, 52.0)}
COL_W = 0.8                      # Street View: the columns read 0.75-0.85 m wide (h262, h334, the close-up)
CORRIDOR_MID = 2.7               # venue x halfway between the corridor walls: the cones hang on this side of a column
# the tensile cones (Street View close-up sv_closeup_cloth_cone_detail_h216 and the corridor view h80; metres above
# floor 1): white fabric hanging beside its column on the corridor side, its axis just clear of the column's face. A
# spike points down to 1.45 m; a hoop at 2.95 m; above it the fabric is form-found (cone_form.py, force density): six
# corners CONE_POINT_R out, pulled up to CONE_TOP or to whatever is lower overhead (a girder's underside, the soffit),
# each on a short wire, with cables in the free edges between them, so the flanks curve like stretched fabric and the
# edges scallop between sharp points. Fitted by projecting the solved net over both photos (both views: the canopy's
# top near the girders' underside, the deep scallops, the long throat); the close-up's own cone is irregular (lower
# lobes on the girder beside it), which the same template gives by itself where the overhead drops.
CONE_TIP, CONE_RING, CONE_RING_R = 1.45, 2.95, 0.36
CONE_GAP = 0.12                  # axis to the column's face, beyond the column's half width
CONE_N, CONE_POINT_R, CONE_TOP, CONE_TURN = 6, 3.0, 7.0, 30.0   # corners: count, reach, height, first heading (deg)
CONE_Q_HOOP, CONE_Q_CABLE = 0.4, 10.0   # force densities (meridians 1): rings (trumpet), free-edge cables (scallops)
CONE_CLEAR = 0.04                # metres kept below anything overhead
CONE_GUARD = 0.22                # metres: overhead taken as the lowest within this x distance, wider than the mesh
                                 # spacing, so no face between two vertices cuts a girder's edge (and every vertex is
                                 # clamped under it: whatever the column's position, the fabric never pierces anything)
CONE_SEAMS = 9                   # seams across the flare (white welds; the close-up shows about nine)
RIG_CONE_TIP, RIG_CONE_RING = 1.3, 2.4    # metres: the screen rig's two cones hang lower, under the rig at ~4.3 m
CONE_FACE_Z = 6.2                # metres: corners tied to a girder's face (the close-up's lobe on the face at ~6 m)
CONE_UPLIGHT = 6000.0             # W, the cyan spot inside each cone washing the ceiling round it
CONE_CYAN = (0.0, 0.3, 0.4)      # the glow's colour at its strongest (linear; AgX pales anything brighter, 17/10 A/B)
CONE_GLOW = 1.3                  # emission strength of the cyan light inside (the close-up's throat is saturated)
CONE_WHITE = (0.62, 0.66, 0.68)  # the fabric where the light inside doesn't reach


def overhead(x):
    """local frame: the height (local units) of the underside of whatever is overhead at local x (extruded along y):
    the dark ceiling between the girders, a girder's underside, or the sloped soffit from the girder down to a wall"""
    if BEAM_L["xi0"] < x < BEAM_R["xi0"]:
        return Z_CEIL
    for b, xw in ((BEAM_L, XL), (BEAM_R, XR)):
        lo, hi = sorted((b["xi0"], b["xo"]))
        if lo <= x <= hi:
            return b["z0"]
        if (x - b["xo"]) * (xw - b["xo"]) > 0:
            return b["z0"] + min(1.0, (x - b["xo"]) / (xw - b["xo"])) * (Z_WALL - b["z0"])
    return Z_CEIL


def overhead_safe(x):
    """the lowest overhead within CONE_GUARD of x, less the clearance (local units)"""
    g = CONE_GUARD / S
    return min(overhead(x + g * k / 4) for k in range(-4, 5)) - CONE_CLEAR / S


def cone_mesh(name, cx, cy, mat, wire_mat):
    """a tensile funnel with its axis at local (cx, cy): spike, hoop, and the flare form-found between the hoop and
    CONE_N corners (cone_form.solve), every vertex then clamped under the structure; a wire from each corner up to
    whatever is overhead"""
    z_ring = CONE_RING / S
    # corners: a cone hanging between the girders ties the corners that would land past a girder to the girder's face
    # (the close-up: a lobe on the face at 6 m), so every fixed node is on the corridor side of both faces and the
    # solved fabric, inside their hull, can't reach into a girder; a cone hanging under a girder keeps all its
    # corners below the girder's underside
    lo, hi = BEAM_L["xi0"], BEAM_R["xi0"]
    m, clear = 0.05 / S, CONE_CLEAR / S
    between = lo < cx < hi
    under = min(BEAM_L["z0"], BEAM_R["z0"]) - clear
    corners, tied = [], set()
    for k in range(CONE_N):
        th = math.radians(CONE_TURN + 360 * k / CONE_N)
        x, y = cx + CONE_POINT_R / S * math.cos(th), cy + CONE_POINT_R / S * math.sin(th)
        if between and not lo < x < hi:
            x, z = min(max(x, lo + m), hi - m), CONE_FACE_Z / S
            tied.add(k)
        else:
            z = min(CONE_TOP / S, overhead_safe(x)) if between else min(CONE_TOP / S, overhead_safe(x), under)
        corners.append((x, y, z))
    ob, n_clamped = fabric_cone(name, cx, cy, corners, mat, lambda x: overhead(x) - clear)
    print(f"CONE {name}: {'between the girders' if between else 'under a girder'}, corners at "
          f"{', '.join(f'{c[2] * S:.1f}' for c in corners)} m, {n_clamped} vertices clamped", flush=True)
    # the light inside: an uplight washing the dark ceiling cyan round the canopy (the photos), no shadows
    li = L.spot(f"{name}-uplight", (cx, cy, z_ring + 0.3 / S), (cx, cy, z_ring + 5), CONE_UPLIGHT, angle_deg=120, blend=0.6,
                color=(0.2, 0.85, 1.0), radius=0.3)
    li.data.use_shadow = False
    for k, (x, y, z) in enumerate(corners):       # the hanging wires
        top = overhead(x)
        if k not in tied and top - z > 0.05:          # (a corner tied to a girder's face needs none)
            L.tube(f"{name}-wire{k}", (x, y, z), (x, y, top), 0.006 / S, wire_mat, segs=4)
    return ob


def fabric_cone(name, cx, cy, corners, mat, cap=None, tip=CONE_TIP, ring=CONE_RING, ring_r=CONE_RING_R):
    """the fabric itself (local frame; heights in metres above floor 1 for tip and ring): a spike from the tip up to
    the hoop, the flare form-found from the hoop to the corners (cone_form.solve), every vertex held under cap(x).
    Returns the object and how many vertices the cap moved."""
    import numpy as np
    from pm_areas import cone_form
    nr, nt, ns = 168, 30, 8                       # around, flare rows, spike rows
    ring_r, z_ring = ring_r / S, ring / S
    G = cone_form.solve((cx, cy), z_ring, ring_r, corners, nr=nr, nt=nt, q_hoop=CONE_Q_HOOP, q_cable=CONE_Q_CABLE)
    n_clamped = 0
    if cap is not None:
        lim = np.vectorize(cap)(G[..., 0])
        n_clamped = int((G[..., 2] > lim).sum())
        G[..., 2] = np.minimum(G[..., 2], lim)
    verts, uvs, faces = [(cx, cy, tip / S)], [(0.5, 0.0)], []
    for i in range(1, ns + 1):                    # spike: tip vertex, then rings up to just under the hoop
        u = i / ns
        r, z = ring_r * u, (tip + (ring - tip) * u) / S
        for j in range(nr):
            th = 2 * math.pi * j / nr
            verts.append((cx + r * math.cos(th), cy + r * math.sin(th), z))
            uvs.append((j / nr, 0.3 * u))
    for i in range(1, nt + 1):                    # flare: row 0 is the hoop (the spike's last ring)
        for j in range(nr):
            verts.append(tuple(G[i, j]))
            uvs.append((j / nr, 0.3 + 0.7 * i / nt))   # v by row: the seams follow the fabric's rings
    for j in range(nr):
        faces.append((0, 1 + (j + 1) % nr, 1 + j))
    for i in range(ns + nt - 1):
        a0 = 1 + i * nr
        for j in range(nr):
            a, b = a0 + j, a0 + (j + 1) % nr
            faces.append((a, b, b + nr, a + nr))
    ob = L.mesh_obj(name, verts, faces, mat, uvs=uvs)
    for poly in ob.data.polygons:
        poly.use_smooth = True
    return ob, n_clamped


def cones(M):
    """unified: the dark columns up to whatever is overhead, most with a tensile fabric cone on the corridor side"""
    dark = L.mat("up-gate", 0x050508, 0.9)
    sail = cone_fabric()
    wire = L.mat("up-cone-wire", 0x101012, 0.5, metal=0.5)
    for k, (xv, yv) in enumerate(COLUMNS):
        x, y, hw = loc_x(xv), loc_y(yv), COL_W / 2 / S
        top = min(overhead(x + d * hw) for d in (-1, 0, 1))
        L.box(f"column-{k}", x - hw, y - hw, 0, x + hw, y + hw, top, dark)
        if (xv, yv) in PLAIN:
            continue
        side = 1 if xv < CORRIDOR_MID else -1                     # venue x towards the corridor's middle
        ax = loc_x(xv + side * (COL_W / 2 + CONE_GAP))
        cone_mesh(f"cone-{k}", ax, y, sail, wire)


def cone_fabric(lit=True):
    """white tensile fabric lit cyan from inside (Street View close-up): saturated cyan in the throat above the hoop,
    fading to plain white towards the points and down the spike; white seams across the flare. lit=False: the plain
    white fabric with its seams, no light inside (the screen rig's cones, under the stage's blue wash)"""
    import bpy as _b
    glow_k = CONE_GLOW if lit else 0.0
    m = _b.data.materials.new("up-cone-fabric" if lit else "up-cone-fabric-unlit")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.7
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.15     # matte fabric: no grey sheen over the cyan
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = 0.0

    def ramp(stops):
        r = nt.nodes.new("ShaderNodeValToRGB")
        els = r.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
        els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
        for pos, col in stops[1:-1]:
            els.new(pos).color = (*col, 1)
        nt.links.new(sep.outputs["Y"], r.inputs["Fac"])
        return r

    def math_node(op, a, b=None, c=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    # uv: v = 0 at the spike's tip, 0.3 at the hoop, 1 at the highest point (the flare's v goes by height)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    v = sep.outputs["Y"]
    # the fabric's own colour: white on the spike and the arms, dimmed where the light inside dominates
    base = ramp([(0.0, CONE_WHITE), (0.24, (0.3, 0.42, 0.45)), (0.33, (0.0, 0.02, 0.03)), (0.6, (0.0, 0.03, 0.04)),
                 (0.85, CONE_WHITE), (1.0, CONE_WHITE)] if lit else [(0.0, CONE_WHITE), (1.0, CONE_WHITE)])
    cy = CONE_CYAN
    glow = ramp([(0.0, (0.0, 0.0, 0.0)), (0.22, tuple(c * 0.3 for c in cy)), (0.33, cy), (0.6, tuple(c * 0.9 for c in cy)),
                 (0.78, (0.0, 0.04, 0.06)), (1.0, (0.0, 0.0, 0.0))])
    # seams: narrow bands across the flare (the fabric's welds): white, the light behind them blocked
    fr = math_node("FRACT", math_node("MULTIPLY_ADD", v, CONE_SEAMS / 0.7, -0.3 * CONE_SEAMS / 0.7 + 0.03))
    seam = math_node("MULTIPLY", math_node("LESS_THAN", fr, 0.08), math_node("GREATER_THAN", v, 0.28))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    ins = {i.identifier: i for i in mix.inputs}
    nt.links.new(math_node("MULTIPLY", seam, 0.8), ins["Factor_Float"])      # pale welds across the glow
    nt.links.new(base.outputs["Color"], ins["A_Color"])
    ins["B_Color"].default_value = (*CONE_WHITE, 1)
    nt.links.new(next(o for o in mix.outputs if o.identifier == "Result_Color"), b.inputs["Base Color"])
    nt.links.new(glow.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(math_node("MULTIPLY_ADD", seam, -glow_k * 0.6, glow_k), b.inputs["Emission Strength"])
    return m


def to_venue(objs=None):
    """everything was built in the photo frame; place it in the venue frame (build_scene.py's), floor 1 at FH.
    objs: only these (unified: the other areas are already in the venue frame)"""
    from mathutils import Matrix
    M = Matrix.Translation((VX, VY, FH)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Scale(S, 4)
    bpy.context.view_layer.update()              # objects placed by location/rotation: bring matrix_world up to date
    obs = list(bpy.context.scene.objects) if objs is None else [o for o in objs if o.users_collection]
    for ob in obs:
        if ob.type == "LIGHT":
            ob.visible_camera = False                # a lamp's own disc reads as a white ring
    for ob in obs:
        if ob.parent is None:
            ob.matrix_world = M @ ob.matrix_world


def build_seating(M):
    """long table rows down both sides, folding chairs on both long sides, backs to the aisle and to the wall"""
    rows = [(-4.2, -1, 0.0, 15.2), (5.0, 1, 0.0, 15.0)]          # aisle edge x, outward sign, y from, y to
    if UNIFIED[0]:
        # John (16/10): the rows stand about half as far from the walls as the photo match put them (3.8 -> 1.9 m from
        # the wall to the outer chairs), and start just past the doors of rooms 5 and 8 (venue y -24.2), not across them
        rows = [(-6.02, -1, 2.6, 15.2), (6.75, 1, 2.6, 15.0)]
    chair = make_chair(M)
    for xa, s, y0, y1 in rows:
        xb = xa + 0.76 * s
        L.box("table-top", xa, y0, 0.72, xb, y1, 0.75, M["cloth"])
        # cloth skirt on the aisle side
        L.box("table-skirt", xa, y0, 0.35, xa + 0.01 * s, y1, 0.75, M["cloth"])
        L.box("table-edge", xa - 0.005 * s, y0, 0.73, xa + 0.02 * s, y1, 0.76, L.mat("up-table-edge", 0xc8ccd8, 0.35))
        for yl in (y0 + 0.1, y1 - 0.1):
            L.box("table-leg", xa + 0.1 * s, yl - 0.02, 0, xa + 0.13 * s, yl + 0.02, 0.72, M["chair"])
        n = int((y1 - y0) / 0.55)
        for i in range(n):
            y = y0 + 0.3 + i * 0.55
            # aisle side: chair faces the table (outwards), back to the aisle
            L.copy_at(chair, (xa - 0.2 * s, y, 0), rot_z=-math.pi / 2 * s)
            L.copy_at(chair, (xb + 0.2 * s, y, 0), rot_z=math.pi / 2 * s)
    chair.hide_render = True
    chair.hide_viewport = True


def make_chair(M):
    """a black metal folding chair, seat 0.45 m, facing +y at the origin (rotated into place by copies)"""
    parts = []
    w, d = 0.42, 0.42
    parts.append(L.box("c-seat", -w / 2, -d / 2, 0.43, w / 2, d / 2, 0.47, M["chair"]))
    parts.append(L.box("c-back", -w / 2, -d / 2 - 0.05, 0.62, w / 2, -d / 2 - 0.02, 0.86, M["chair"]))
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.01)
        parts.append(L.tube("c-leg-f", (x, d / 2, 0), (x, -d / 2 - 0.03, 0.88), 0.011, M["chair"], segs=8))
        parts.append(L.tube("c-leg-b", (x, -d / 2 - 0.02, 0), (x, d / 2 - 0.05, 0.45), 0.011, M["chair"], segs=8))
    ob = L.join("chair", parts)
    return ob


def build_rails(M):
    """a track rail along each soffit, hung on wires just outside the girder, with clusters of four black spots
    aimed back towards the cameras and down at the tables; short white linear pendants near the walls"""
    rails = (("l", -4.37, 4.3, XL, BEAM_L), ("r", 5.11, 4.32, XR, BEAM_R))
    for side, xr, zr, xw, b in rails:
        s = 1 if xr > 0 else -1

        def soffit_z(x):
            return b["z0"] + (x - b["xo"]) / (xw - b["xo"]) * (Z_WALL - b["z0"])
        L.box(f"rail-{side}", xr - 0.03, Y_NEAR, zr - 0.03, xr + 0.03, Y_END - 1.0, zr + 0.03, M["rail"])
        # panel seams across the soffit, and a loose cable along it
        seam = L.mat("up-seam", 0xc4c6cc, 0.6)
        for ys in [Y_NEAR + 1.2 + 2.4 * k for k in range(int((Y_END - Y_NEAR) / 2.4))]:
            a = (b["xo"] + 0.05 * s, ys, soffit_z(b["xo"] + 0.05 * s) - 0.012)
            c = (xw - 0.05 * s, ys, soffit_z(xw - 0.05 * s) - 0.012)
            L.extrude_section("seam", [(-0.012, -0.004), (0.012, -0.004), (0.012, 0.004), (-0.012, 0.004)], a, c, seam)
        xc_ = xr + 0.9 * s
        pts = [(xc_, y, soffit_z(xc_) - 0.08 - 0.25 * math.sin(math.pi * ((y - Y_NEAR) % 6.0) / 6.0)) for y in
               [Y_NEAR + 0.5 * k for k in range(int((Y_END - 1 - Y_NEAR) / 0.5))]]
        for p0, p1 in zip(pts, pts[1:]):
            L.tube("cable", p0, p1, 0.008, M["rail"], segs=5)
        for yw in range(-12, 22, 3):
            L.tube("wire", (xr, yw, zr), (xr, yw, soffit_z(xr)), 0.005, M["rail"], segs=6)
        for yc in (-3.0, 3.5, 10.0, 16.5):
            for j in range(4):
                y = yc - 1.35 + j * 0.9
                # can hangs on a yoke below the rail, tilted to face -y and down
                L.box("yoke", xr - 0.01, y - 0.01, zr - 0.18, xr + 0.01, y + 0.01, zr, M["rail"])
                a = (xr - 0.15 * s * (j % 2), y, zr - 0.25)
                tip = (a[0] - 0.06 * s, a[1] - 0.28, a[2] - 0.16)
                L.tube("spot-can", a, tip, 0.09, M["lamp"], segs=14)
                L.tube("spot-back", a, (2 * a[0] - tip[0], 2 * a[1] - tip[1], 2 * a[2] - tip[2]), 0.07, M["lamp"], segs=12)
                L.mesh_obj("spot-lens", *disc(tip, (tip[0] - a[0], tip[1] - a[1], tip[2] - a[2]), 0.035), M["spotlens"])
            L.spot(f"spot-{side}", (xr, yc, zr - 0.4), (xr - 1.0 * s, yc - 5.0, 0.0), 1500, angle_deg=50, blend=0.5,
                   color=(1.0, 0.86, 0.7), radius=0.15)
        # short linear pendants near the walls
        xp = (7.22 if s < 0 else 7.6) * s
        for y0 in (5.8, 13.6):
            L.box(f"pendant-{side}", xp - 0.035, y0, 2.92, xp + 0.035, y0 + 3.8, 2.98, M["pend"])
            for yw in (y0 + 0.3, y0 + 3.5):
                L.tube("pendant-wire", (xp, yw, 2.98), (xp, yw, soffit_z(xp)), 0.003, M["rail"], segs=5)


def disc(center, normal, r, n=16):
    """vertices and face of a flat disc"""
    import mathutils
    nv = mathutils.Vector(normal).normalized()
    u = nv.orthogonal().normalized()
    w = nv.cross(u)
    c = mathutils.Vector(center) + nv * 0.002
    verts = [tuple(c + (u * math.cos(2 * math.pi * k / n) + w * math.sin(2 * math.pi * k / n)) * r) for k in range(n)]
    return verts, [tuple(range(n))]

