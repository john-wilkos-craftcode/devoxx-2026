"""Hollywood room (the exhibition floor, plan room "hall"), in the venue frame of data/venue/venue.json (metres,
+x east, +y north, z up, hall floor z = 0). Matched to three photos taken from the top of the hall steps:
inside_hollywood_w_booths_and_people.jpg (master), inside_hollywood.jpg and inside_hollywood_w_ing_orange_guys.jpg.

Structure from the plan: columns (less two the photos show aren't there, see NOT_THERE), walls, stairwells, the
threshold landing and the hall steps, the booth footprints. From the photos: the ceiling heights, the coffer and its
cove, the white lowered ceiling over the middle zone (x -10.46..9.13) and the dark ducted ceiling of the side zones,
and the dressing. The middle aisle (x -6.0..4.7) runs from the steps between two booth islands (a spine with cross
walls, booths on both sides), past the stairwells, to the main schedule screen on the curtained north wall.

build(root, unified=False): unified=True builds only floor 0 from y -37.4 north, closed and lightproof, and leaves the
world and view settings alone (for the one scene that joins all areas).
"""
import math
import random
from pathlib import Path

import bpy

import pm_lib as L

# The photos were measured in the master camera's own frame ("photo frame": coffer front edge at y = 0, its centre
# line at x = 0, scale from 0.7 m columns and people's heads). PHOTO_TO_VENUE scales that frame about the master
# camera so its two central columns land on the plan's (-3.8 / 2.65, row y = -20.75) and the photographers stand on
# the hall steps: across and up x1.086 (the plan's 6.45 m column spacing), along the view x0.977 (the 24 mm lens,
# 73.7 deg, instead of the 68 deg first assumed). The cameras' focal lengths are scaled with it, so pixels don't move.
# x' = -0.575 + 1.086 x, y' = -28.23 + 0.977 y, z' = 1.086 z.
SX, SY, SZ = 1.086, 0.977, 1.086
X0, Y0 = -0.575, -28.23
# Plan error: Ghost Light fills the column grid evenly, but the photos show no columns at (-3.8, -27.28) and
# (2.65, -27.28): that bay is spanned (the coffer sits in it). Those two are left out.
NOT_THERE = {(-3.8, -27.28), (2.65, -27.28)}


def V(x, y, z=0.0):
    """photo frame -> venue"""
    return (X0 + SX * x, Y0 + SY * y, SZ * z)


PHOTO_TO_VENUE = None                # set in build(): a Matrix for the dressing built in the photo frame
# heights from the photos, in venue metres above the hall floor
LOW = SZ * 3.0                       # lowered ceiling underside
SLAB_TOP = SZ * 3.21
POCKET_TOP = SZ * 3.42
HIGH = SZ * 3.46                     # entrance (landing + reception) ceiling and the coffer's top
CX = X0                              # coffer centre line, midway between the plan's columns x = -3.8 and 2.65
OPEN_HW, POCKET_HW = SX * 2.56, SX * 2.78
COF_Y0, OPEN_Y1, POCKET_Y1 = Y0, Y0 + SY * 4.72, Y0 + SY * 5.17
HALL = dict(x0=-23.5, x1=28.8, y0=-37.4, y1=18.3)
RECEPTION_Y0, RECEPTION_Z = -60.4, 1.2
ROOT = None
FONT = None
LED = 0xa7acff                       # the cove LEDs: cool white with a blue-violet cast in the photos


def tex_mat(name, folder, scale, tint, rough=0.9, mottle=0.0, tiles=0.0):
    """CC0 texture (data/textures/<folder>) box-mapped in world space, recoloured to tint"""
    if name in L.MATS:
        return L.MATS[name]
    d = ROOT / "data" / "textures" / folder
    if not (d / "color.jpg").exists():
        return L.mat(name, tint, rough)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale,) * 3
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])

    def img(file, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(d / file), check_existing=True)
        t.image.colorspace_settings.name = cs
        t.projection, t.projection_blend = "BOX", 0.2
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t
    col = img("color.jpg", "sRGB")
    # keep the texture's light and dark, take the colour from the photo
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col.outputs["Color"], bw.inputs["Color"])
    gain = nt.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = 2.0
    nt.links.new(bw.outputs["Val"], gain.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = L.srgb(tint)
    nt.links.new(gain.outputs["Value"], mix.inputs["B"])
    out = mix.outputs["Result"]
    if mottle:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.6
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = 1 - mottle, 1 + mottle
        nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
        m2 = nt.nodes.new("ShaderNodeMix")
        m2.data_type, m2.blend_type = "RGBA", "MULTIPLY"
        m2.inputs["Factor"].default_value = 1.0
        nt.links.new(out, m2.inputs["A"])
        nt.links.new(ramp.outputs["Result"], m2.inputs["B"])
        out = m2.outputs["Result"]
    if tiles:
        # carpet tiles: each tile a shade lighter or darker, as laid from different batches
        cell = nt.nodes.new("ShaderNodeVectorMath")
        cell.operation = "SCALE"
        cell.inputs["Scale"].default_value = 1 / tiles
        nt.links.new(coord.outputs["Object"], cell.inputs[0])
        flo = nt.nodes.new("ShaderNodeVectorMath")
        flo.operation = "FLOOR"
        nt.links.new(cell.outputs["Vector"], flo.inputs[0])
        rnd = nt.nodes.new("ShaderNodeTexWhiteNoise")
        nt.links.new(flo.outputs["Vector"], rnd.inputs["Vector"])
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.9, 1.1
        nt.links.new(rnd.outputs["Value"], rr.inputs["Value"])
        m3 = nt.nodes.new("ShaderNodeMix")
        m3.data_type, m3.blend_type = "RGBA", "MULTIPLY"
        m3.inputs["Factor"].default_value = 1.0
        nt.links.new(out, m3.inputs["A"])
        nt.links.new(rr.outputs["Result"], m3.inputs["B"])
        out = m3.outputs["Result"]
    nt.links.new(out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if (d / "normal.jpg").exists():
        nm = img("normal.jpg", "Non-Color")
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.6
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = L.srgb(tint)
    L.MATS[name] = m
    return m


def label(body, size, x, y, z, mat, face="-y", align="CENTER", extrude=0.004):
    """flat text on a wall: face -y (towards the entrance), -x or +x"""
    rot = {"-y": (math.pi / 2, 0, 0), "-x": (math.pi / 2, 0, -math.pi / 2), "+x": (math.pi / 2, 0, math.pi / 2)}[face]
    off = {"-y": (0, -0.006, 0), "-x": (-0.006, 0, 0), "+x": (0.006, 0, 0)}[face]
    return L.text(f"txt-{body[:12]}", body, size, (x + off[0], y + off[1], z), rot, mat, extrude=extrude, font=FONT,
                  align=align)


# ---------------------------------------------------------------------------------- the plan (venue frame)
CENTRE_X0, CENTRE_X1 = -10.46, 9.13      # the white-ceilinged middle zone, between the column lines (= the landing)
NORTH_Y = 18.15                          # inner face of the north wall: the middle zone runs up to it
SCREEN_X = 2.4                           # the schedule screen, centred between the stairwells
TOP = 5.45                               # the black structural ceiling over everything (side zones are open to it)
WALL_TOP = TOP + 0.05
STAIR_W = (-7.45, -4.55)                 # stairwell glass boxes (plan walls), from y -1.32 north
STAIR_E = (9.95, 12.85)
# The two booth blocks either side of the middle aisle (John's sketch over the plan): each merges the plan's island
# with its inner row into one double-sided block, a spine with cross walls, 4 booths of ~5 m on each side.
BLOCK_L = (-13.9, -10.5, -6.0)           # outer edge, spine, aisle edge
BLOCK_R = (12.6, 9.0, 4.7)
BLOCK_Y = (-24.7, -19.7, -14.7, -9.6, -4.5)   # south end, three cross walls, north end
SCREEN_KEEP_OUT = 4.0                    # unified: the screen module owns everything this close to the screen


def plan():
    import json
    v = json.loads((ROOT / "data" / "venue" / "venue.json").read_text())["venue"]
    obs = [o for o in v["obstacles"] if o["floor"] == 0 and not o.get("hidden")]
    hall = lambda b: HALL["x0"] - 0.5 <= b["x"] + b["w"] / 2 <= HALL["x1"] + 0.5 and \
        HALL["y0"] - 0.6 <= b["y"] + b["h"] / 2 <= HALL["y1"] + 0.5   # noqa: E731
    cols = [o["bounds"] for o in obs if round(o["bounds"]["w"], 2) == 0.7 and round(o["bounds"]["h"], 2) == 0.7
            and hall(o["bounds"]) and (round(o["bounds"]["x"] + 0.35, 2), round(o["bounds"]["y"] + 0.35, 2)) not in NOT_THERE]
    stair_walls = [o["bounds"] for o in obs if o.get("height") == 5.4 and round(o["bounds"]["w"], 2) != 0.7
                   and hall(o["bounds"])]
    walls = [o for o in obs if o.get("height") == 3.2 and hall(o["bounds"]) and not o.get("linkId")]
    steps = [o for o in obs if o.get("linkId") == "hall-steps"]
    stands = [o for o in obs if o.get("material") in ("booth", "desk") and hall(o["bounds"])]
    return cols, stair_walls, walls, steps, stands


def bx(name, b, z0, z1, mat, bevel=0.0):
    return L.box(name, b["x"], b["y"], z0, b["x"] + b["w"], b["y"] + b["h"], z1, mat, bevel=bevel)


def in_centre(x, y):
    return CENTRE_X0 < x < CENTRE_X1 and HALL["y0"] < y < NORTH_Y


def architecture(unified):
    white = L.mat("ceiling-white", 0xe4e4e8, 0.85)
    col_white = L.mat("column-white", 0xededee, 0.55)
    dark = L.mat("ceiling-dark", 0x262b40, 0.9)
    black = L.mat("ceiling-black", 0x07080d, 0.95)
    carpet = tex_mat("carpet", "carpet", 0.5, 0x8c8986, 0.95, mottle=0.06, tiles=0.5)
    cove = L.mat("cove-wall", 0xf2f2f6, 0.85)
    wall = L.mat("wall-white", 0xe2e2e3, 0.8)
    glass = L.mat("frosted-glass", 0x8fb5b0, 0.35, transmission=0.6)
    cols, stair_walls, walls, steps, _ = plan()
    hx0, hx1, hy0, hy1 = HALL["x0"], HALL["x1"], HALL["y0"], HALL["y1"]

    # floor: the hall minus its two voids in the north-east corner (plan "hall" voids)
    L.box("floor", hx0, hy0, -0.1, 22.17, hy1, 0, carpet)
    L.box("floor-e1", 22.17, hy0, -0.1, 24.57, -8.0, 0, carpet)
    L.box("floor-e2", 24.57, hy0, -0.1, hx1, -22.2, 0, carpet)
    # the threshold landing (1.2 m, plan "threshold") and the hall steps down from it (plan "hall-steps")
    L.box("landing", -10.46, hy0, 0, 9.13, -34.4, RECEPTION_Z, carpet)
    for i, o in enumerate(steps):
        bx(f"step-{i}", o["bounds"], 0, o["height"], carpet)
    # walls: the plan's, raised to the structural ceiling; the opening onto the reception gets a lintel
    for i, o in enumerate(walls):
        bx(f"wall-{i}", o["bounds"], 0, WALL_TOP, wall)
    L.box("lintel", -10.46, hy0 - 0.3, HIGH, 9.13, hy0, WALL_TOP, black)
    # the black structural ceiling over the whole hall: the side zones are open up to it
    L.box("ceiling-top", hx0 - 0.3, hy0 - 0.3, TOP, hx1 + 0.3, hy1 + 0.3, TOP + 0.1, black)
    # the middle zone: dark entrance ceiling over the landing and the steps, then the white lowered ceiling with the
    # coffer opening, from the coffer's front edge to the curtain line
    c0, c1 = CENTRE_X0, CENTRE_X1
    L.box("ceiling-entrance", c0, hy0, HIGH, c1, COF_Y0, HIGH + 0.1, dark)
    L.box("slab-l", c0, COF_Y0, LOW, CX - OPEN_HW, NORTH_Y, SLAB_TOP, white)
    L.box("slab-r", CX + OPEN_HW, COF_Y0, LOW, c1, NORTH_Y, SLAB_TOP, white)
    L.box("slab-b", CX - OPEN_HW, OPEN_Y1, LOW, CX + OPEN_HW, NORTH_Y, SLAB_TOP, white)
    fascia = L.mat("fascia", 0xd8d8dc, 0.85)
    L.box("fill-l", c0, COF_Y0, SLAB_TOP, CX - POCKET_HW, NORTH_Y, HIGH, fascia)
    L.box("fill-r", CX + POCKET_HW, COF_Y0, SLAB_TOP, c1, NORTH_Y, HIGH, fascia)
    L.box("fill-b", CX - POCKET_HW, POCKET_Y1, SLAB_TOP, CX + POCKET_HW, NORTH_Y, HIGH, cove)
    L.box("pocket-front", CX - POCKET_HW, COF_Y0, SLAB_TOP, CX + POCKET_HW, COF_Y0 + 0.09, HIGH,
          L.mat("band", 0xf4f5ff, 0.6, emit=0xc4c8ff, strength=2.2))
    L.box("pocket-ceiling", CX - POCKET_HW, COF_Y0, POCKET_TOP, CX + POCKET_HW, POCKET_Y1, HIGH, cove)
    # bulkheads from the middle zone's ceilings up to the structural ceiling: its edges as seen from the side zones
    L.box("bulk-w", c0 - 0.1, hy0, LOW, c0, NORTH_Y + 0.1, TOP, black)
    L.box("bulk-e", c1, hy0, LOW, c1 + 0.1, NORTH_Y + 0.1, TOP, black)
    L.box("bulk-n", c0 - 0.1, NORTH_Y, LOW, c1 + 0.1, NORTH_Y + 0.1, TOP, L.mat("bulk-white", 0xdcdcde, 0.85))
    led = L.emissive("cove-led", LED, 60.0)
    t = 0.03
    L.box("led-l", CX - POCKET_HW + 0.02, COF_Y0 + 0.1, SLAB_TOP, CX - OPEN_HW - 0.02, POCKET_Y1 - 0.05, SLAB_TOP + t, led)
    L.box("led-r", CX + OPEN_HW + 0.02, COF_Y0 + 0.1, SLAB_TOP, CX + POCKET_HW - 0.02, POCKET_Y1 - 0.05, SLAB_TOP + t, led)
    L.box("led-b", CX - POCKET_HW + 0.05, OPEN_Y1 + 0.02, SLAB_TOP, CX + POCKET_HW - 0.05, POCKET_Y1 - 0.02, SLAB_TOP + t, led)
    L.box("led-f", CX - POCKET_HW + 0.05, COF_Y0 + 0.1, POCKET_TOP - 0.03, CX + POCKET_HW - 0.05, COF_Y0 + 0.16,
          POCKET_TOP - 0.01, led)
    mid = (COF_Y0 + OPEN_Y1) / 2
    for side in (-1, 1):
        L.area_light(f"cove-{side}", (CX + side * (OPEN_HW + 0.1), mid, SLAB_TOP + 0.05), 0.15, 300,
                     color=(0.82, 0.83, 1.0), size_y=OPEN_Y1 - COF_Y0, rot=(0, side * math.radians(-70), 0))
    L.area_light("cove-back", (CX, OPEN_Y1 + 0.1, SLAB_TOP + 0.05), 2 * OPEN_HW, 280, color=(0.82, 0.83, 1.0),
                 size_y=0.15, rot=(math.radians(70), 0, 0))

    # columns: white to the lowered ceiling in the middle zone; in the side zones white to 3.3 m, black above
    spk = L.mat("speaker", 0xcfc9bd, 0.6)
    skirting = L.mat("skirting", 0xdedede, 0.5)
    for b in cols:
        cx, cy = b["x"] + 0.35, b["y"] + 0.35
        z0 = RECEPTION_Z if cy < hy0 + 0.5 and -10.5 < cx < 9.2 else 0.0
        if in_centre(cx, cy) or (cy < hy0 + 0.5 and c0 - 0.1 < cx < c1 + 0.1):
            bx(f"col-{cx:.1f}-{cy:.1f}", b, z0, LOW if cy > COF_Y0 else HIGH, col_white, bevel=0.01)
        else:
            bx(f"col-{cx:.1f}-{cy:.1f}", b, z0, 3.3, col_white, bevel=0.01)
            bx(f"col-top-{cx:.1f}-{cy:.1f}", b, 3.3, TOP, black)
        L.box(f"col-base-{cx:.1f}-{cy:.1f}", b["x"] - 0.01, b["y"] - 0.01, z0, b["x"] + 0.71, b["y"] + 0.71, z0 + 0.08,
              skirting)
        if abs(cx - CX) < 4 and COF_Y0 < cy < NORTH_Y:
            sx = cx - 0.22 if cx < CX else cx + 0.22
            L.box(f"spk-{cx:.1f}-{cy:.1f}", sx - 0.15, b["y"] - 0.22, 2.8, sx + 0.15, b["y"] - 0.02, 3.28, spk,
                  bevel=0.015)
    # the side stairs up to floor 1, boxed in teal frosted glass up to the structural ceiling
    for i, b in enumerate(stair_walls):
        bx(f"stairwall-{i}", b, 0, TOP, glass)
    for i, (x0, x1) in enumerate((STAIR_W, STAIR_E)):
        L.box(f"stair-front-{i}", x0, -1.32 - 0.3, 0, x1, -1.32, TOP, glass)
    # beige curtains along the whole north wall
    curtain(hx0 + 0.3, 21.9, NORTH_Y - 0.15, 4.1)
    if not unified:
        schedule_screen()
        # behind the photo cameras: a closed, dark reception so the renders have something behind them
        rec = L.mat("reception-floor", 0x3a3c44, 0.6)
        L.box("reception-floor", -13.6, RECEPTION_Y0, 0, 22.7, hy0, RECEPTION_Z, rec)
        L.box("reception-ceiling", -13.6, RECEPTION_Y0, HIGH, 22.7, hy0, HIGH + 0.1, dark)
        L.box("reception-wall", -13.6, RECEPTION_Y0 - 0.2, 0, 22.7, RECEPTION_Y0, HIGH, wall)


def schedule_screen():
    """the main schedule screen on the north wall (photo renders only: in the unified scene a separate module hangs the
    real screen assembly here, face at y 17.83, centred x 2.4, centre z 1.7)"""
    # the main schedule screen on the north wall: 16:10, 3.6 x 2.25 m, bottom 1.4 m, face at y 17.9
    sx0, sw, sh = SCREEN_X, 3.6, 2.25
    zb = 1.4
    L.box("schedule-bezel", sx0 - sw / 2 - 0.03, 17.95, zb - 0.03, sx0 + sw / 2 + 0.03, NORTH_Y - 0.2,
          zb + sh + 0.03, L.mat("bezel", 0x0a0a0c, 0.3))
    L.box("schedule-screen", sx0 - sw / 2, 17.9, zb, sx0 + sw / 2, 17.95, zb + sh,
          L.emissive("schedule-blue", 0x0d2a6e, 3.0))


# ---------------------------------------------------------------------------------- ceilings (venue frame)
def fixtures():
    panel = L.emissive("panel-light", 0xfff8f0, 18.0)
    rim = L.mat("panel-rim", 0xd0d0d4, 0.4, metal=0.3)
    down = L.emissive("downlight", 0xfff6ea, 40.0)
    cols = plan()[0]
    centres = [(b["x"] + 0.35, b["y"] + 0.35) for b in cols]
    for j, y in enumerate([COF_Y0 + 1.0 + 2.6 * k for k in range(20)]):
        off = 0.0 if j % 2 == 0 else 1.6
        for x in [CX - 22.4 + off + 3.2 * k for k in range(16)]:
            if not (CENTRE_X0 + 0.9 < x < CENTRE_X1 - 0.9 and y < NORTH_Y - 0.5):
                continue
            if any(a - 0.9 < x < b + 0.9 and -2.0 < y < 14.6 for a, b in (STAIR_W, STAIR_E)):
                continue
            if abs(x - CX) < POCKET_HW + 0.8 and y < POCKET_Y1 + 0.5:
                continue
            if any(abs(x - cx) < 1.0 and abs(y - cy) < 0.7 for cx, cy in centres):
                continue
            L.box(f"lin-rim-{j}-{x:.1f}", x - 0.84, y - 0.11, LOW - 0.01, x + 0.84, y + 0.11, LOW + 0.02, rim)
            L.box(f"lin-{j}-{x:.1f}", x - 0.8, y - 0.075, LOW - 0.012, x + 0.8, y + 0.075, LOW - 0.008, panel)
            L.area_light(f"linL-{j}-{x:.1f}", (x, y, LOW - 0.03), 1.55, 85, color=(1.0, 0.97, 0.93), size_y=0.13)
            dx, dy = x + 1.6, y + 1.3
            if not (abs(dx - CX) < POCKET_HW + 0.3 and dy < POCKET_Y1 + 0.3) and dx < CENTRE_X1 - 0.3 and dy < NORTH_Y - 0.3:
                L.cylinder(f"dl-{j}-{x:.1f}", dx, dy, LOW - 0.012, LOW - 0.002, 0.09, down, segs=16)


def side_ceilings():
    """the side zones: black structural ceiling with silver spiral ducts at ~4.5 m and aluminium pendants (as the
    side-aisle photos show); helpers from hollywood_side"""
    from pm_areas import hollywood_side as HS
    metal = HS.spiral_duct("duct")
    alu = L.mat("alu-shade", 0xb9bcc0, 0.35, metal=1.0)
    bulb = L.emissive("pendant-bulb", 0xfff1dc, 30.0)
    hanger = L.mat("cord", 0x111111, 0.5)
    zones = [(HALL["x0"] + 0.5, CENTRE_X0 - 0.5, HALL["y0"] + 0.5, HALL["y1"] - 0.6),
             (CENTRE_X1 + 0.5, 22.0, HALL["y0"] + 0.5, HALL["y1"] - 0.6)]
    # the east bays beyond x 22 (south of the plan's voids) are lit by a plain fill
    L.area_light("east-bay-fill", (25.0, -29.5, 4.2), 6.0, 900, color=(1.0, 0.96, 0.9), size_y=14.0)
    L.area_light("east-bay-fill2", (23.3, -15.0, 4.2), 2.0, 300, color=(1.0, 0.96, 0.9), size_y=13.0)
    k = 0
    for x0, x1, y0, y1 in zones:
        # long runs along y, cross runs every ~8 m
        if x1 - x0 < 15:
            for x in (x0 + (x1 - x0) * 0.3, x0 + (x1 - x0) * 0.75):
                HS.duct(f"duct-y{k}", (x, y0, 4.5), (x, y1, 4.5), 0.56, metal)
                k += 1
            for y in [y0 + 4 + 8 * i for i in range(int((y1 - y0 - 4) / 8) + 1)]:
                HS.duct(f"duct-x{k}", (x0, y, 4.75), (x1, y, 4.75), 0.4, metal)
                k += 1
        else:
            for y in (y0 + (y1 - y0) * 0.35, y0 + (y1 - y0) * 0.75):
                HS.duct(f"duct-x{k}", (x0, y, 4.5), (x1, y, 4.5), 0.56, metal)
                k += 1
        for i, y in enumerate([y0 + 3 + 6 * j for j in range(int((y1 - y0 - 3) / 6) + 1)]):
            for x in [x0 + 3 + 6.5 * j for j in range(max(1, int((x1 - x0 - 3) / 6.5) + 1))]:
                HS.pendant(f"pend-{k}-{i}-{x:.0f}", x, y, 3.6, 0.5, 0.42, alu, bulb, light_power=260)
                L.cylinder(f"pend-hang-{k}-{i}-{x:.0f}", x, y, 4.82, TOP, 0.006, hanger, segs=6)
        L.area_light(f"side-fill-{k}", ((x0 + x1) / 2, (y0 + y1) / 2, 4.2), x1 - x0, 60 * (x1 - x0) * (y1 - y0) / 40,
                     color=(1.0, 0.96, 0.9), size_y=y1 - y0)


def curtain(x0, x1, y, top, pleat=0.32, amp=0.06):
    n = int((x1 - x0) / (pleat / 4))
    verts, faces = [], []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        dy = amp * math.sin(2 * math.pi * (x - x0) / pleat)
        verts += [(x, y + dy, 0.0), (x, y + dy, top)]
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 2, a + 3, a + 1))
    L.mesh_obj(f"curtain-{x0:.0f}", verts, faces, tex_mat("curtain", "curtain", 0.6, 0xb7aa96, 0.9), smooth=True)



# ---------------------------------------------------------------------------------- booths (venue frame)
BRAND = {  # aisle-facing booths (from John): name, print colour, ink colour
    "Google Cloud": (0xf4f5f7, 0x4285f4), "Belfius": (0xc30045, 0xffffff), "Docker": (0x1d63ed, 0xffffff),
    "Java": (0xf4f5f7, 0xe76f00), "Red Hat": (0xee0000, 0xffffff), "Nimble": (0x288a90, 0xffffff),
}
GENERIC = [("NORTHSTACK", 0x206A81), ("LUMEN", 0x1b1e26), ("ByteGarden", 0x00a07a), ("FluxWorks", 0xd8501a),
           ("VECTOR", 0x233AFF), ("CloudNest", 0x1595b0), ("PATCHLAB", 0xc4007a), ("OrbitDB", 0x6551A1),
           ("SignalForge", 0x9a7424), ("THREAD", 0x914A49), ("BlueCircuit", 0x236CB0), ("PrismOps", 0x8a4fa6),
           ("CEDAR", 0x52785A), ("DataHarbor", 0x306071), ("STACKWISE", 0x996C37), ("TIDAL", 0x25817B)]


def tv(name, x, y, zc, w, face):
    """a wall TV: face '-x' / '+x' / '-y'"""
    h = w * 9 / 16
    scr = L.emissive("tv-content", 0x3a62c8, 2.2)
    bez = L.mat("bezel", 0x0a0a0c, 0.3)
    if face in ("-x", "+x"):
        s = -1 if face == "-x" else 1
        L.box(name, x, y - w / 2, zc - h / 2, x + s * 0.05, y + w / 2, zc + h / 2, bez)
        L.box(name + "-scr", x + s * 0.05, y - w / 2 + 0.02, zc - h / 2 + 0.02, x + s * 0.055, y + w / 2 - 0.02,
              zc + h / 2 - 0.02, scr)
    else:
        L.box(name, x - w / 2, y - 0.05, zc - h / 2, x + w / 2, y, zc + h / 2, bez)
        L.box(name + "-scr", x - w / 2 + 0.02, y - 0.055, zc - h / 2 + 0.02, x + w / 2 - 0.02, y - 0.05, zc + h / 2 - 0.02, scr)


def stand_face(name, x, y0, y1, face, colour, ink, logo):
    """a booth's back wall graphic on the spine: a printed colour panel, a white header with the logo, a TV"""
    s = -1 if face == "-x" else 1
    prt = L.mat(f"print-{name}", colour, 0.55, emit=colour, strength=0.12)
    L.box(f"{name}-panel", x, y0 + 0.05, 0.0, x + s * 0.02, y1 - 0.05, 2.5, prt)
    L.box(f"{name}-head", x + s * 0.02, y0 + 0.05, 2.05, x + s * 0.03, y1 - 0.05, 2.5, L.mat("head-white", 0xf2f3f5, 0.5))
    label(logo, 0.24, x + s * 0.035, (y0 + y1) / 2, 2.15, L.mat(f"ink-{name}", ink if ink != 0xffffff else colour, 0.5),
          face=face)
    tv(f"{name}-tv", x + s * 0.03, (y0 + y1) / 2, 1.45, 1.4, face)


def counter(name, x0, y0, x1, y1, colour):
    L.box(name, x0, y0, 0, x1, y1, 0.98, L.mat(f"counter-{colour:06x}", colour, 0.5))
    L.box(name + "-top", x0 - 0.03, y0 - 0.03, 0.98, x1 + 0.03, y1 + 0.03, 1.02, L.mat("stand-white", 0xf0f1f3, 0.6))


def islands():
    """the two booth blocks: a spine with cross walls through both sides, 4 booths per side. The first booth on the
    aisle side is JetBrains (left) / ING (right), built from the photos in photo_booths(); the rest are colour
    panels with the brand, a TV and a counter."""
    wall = L.mat("shell-white", 0xeeeff1, 0.6)
    gi = 0
    aisle = {"L": ["JETBRAINS", "Google Cloud", "Belfius", "Docker"], "R": ["ING", "Java", None, "Red Hat"]}
    ys = BLOCK_Y
    for side, (x_out, x_sp, x_ai) in (("L", BLOCK_L), ("R", BLOCK_R)):
        s_ai = 1 if x_ai > x_sp else -1                  # direction from the spine to the aisle
        aisle_face, out_face = ("+x", "-x") if s_ai > 0 else ("-x", "+x")
        L.box(f"spine-{side}", x_sp - 0.05, ys[1], 0, x_sp + 0.05, ys[-1], 2.5, wall)
        x0, x1 = sorted((x_out, x_ai))
        for y in ys[1:]:
            L.box(f"cross-{side}-{y}", x0, y - 0.05, 0, x1, y + 0.05, 2.5, wall)
        for i in range(4):
            b0, b1 = ys[i], ys[i + 1]
            if i > 0:
                name = aisle[side][i]
                if name:
                    colour, ink = BRAND[name]
                else:
                    name, colour = GENERIC[gi % len(GENERIC)]
                    ink = 0xffffff
                    gi += 1
                stand_face(f"{side}{i}a", x_sp + s_ai * 0.05, b0, b1, aisle_face, colour, ink, name)
                c0_ = x_ai - 0.75 if s_ai > 0 else x_ai + 0.15
                counter(f"{side}{i}a-counter", c0_, b0 + 1.4, c0_ + 0.6, b0 + 3.4, colour if colour != 0xf4f5f7 else 0xd8dade)
                # the name on a fascia board over the booth's open aisle side
                L.box(f"fascia-{side}{i}", min(x_ai, x_ai - s_ai * 0.08), b0, 2.5, max(x_ai, x_ai - s_ai * 0.08), b1, 2.9, wall)
                label(name, 0.22, x_ai + s_ai * 0.004, (b0 + b1) / 2, 2.6,
                      L.mat(f"ink-{name}-top", ink if ink != 0xffffff else colour, 0.5), face=aisle_face)
            # the side-aisle booth behind it (booth 1's outer half is behind the photo booth's wall: a plain shell)
            gname, gcol = GENERIC[gi % len(GENERIC)]
            gi += 1
            stand_face(f"{side}{i}o", x_sp - s_ai * 0.05, b0, b1, out_face, gcol, 0xffffff, gname)
            c0_ = x_out + 0.15 if s_ai > 0 else x_out - 0.75
            counter(f"{side}{i}o-counter", c0_, b0 + 1.4, c0_ + 0.6, b0 + 3.4, gcol)


def outer_rows():
    """the plan's outer rows of 3 x 2 m shell stands (back wall + side walls + fascia), facing the side aisles"""
    stands = plan()[4]
    white = L.mat("shell-white", 0xeeeff1, 0.6)
    k = 0
    for o in stands:
        b = o["bounds"]
        cx = b["x"] + b["w"] / 2
        if BLOCK_L[0] - 0.3 <= cx <= BLOCK_L[2] + 0.3 or BLOCK_R[2] - 0.3 <= cx <= BLOCK_R[0] + 0.3:
            continue          # the plan's islands and inner rows: merged into the booth blocks (islands())
        if 9.0 < cx < 12.6 and b["y"] < -20.5:
            continue          # ING's Wear-it wall and counter stand there (photo)
        if b["x"] > 19:
            continue          # the plan's east bar counter: not in the photos
        name, col = GENERIC[(k + 5) % len(GENERIC)]
        k += 1
        if o["material"] == "desk":
            counter(f"row-desk-{k}", b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"], col)
            continue
        desks = [d["bounds"] for d in stands if d["material"] == "desk" and abs(d["bounds"]["y"] - b["y"]) < 2.5]
        near = min(desks, key=lambda d: abs(d["x"] - b["x"]), default=None)
        sgn = 1 if near is None or near["x"] > b["x"] else -1
        x0, x1 = sorted((b["x"] + (b["w"] if sgn > 0 else 0), b["x"] + sgn * 2.4))
        face = "+x" if sgn > 0 else "-x"
        bx(f"row-wall-{k}", b, 0, 2.5, white)
        stand_face(f"row{k}", b["x"] + (b["w"] if sgn > 0 else 0), b["y"], b["y"] + b["h"], face, col, 0xffffff, name)
        for yy in (b["y"], b["y"] + b["h"] - 0.05):
            L.box(f"row-side-{k}-{yy:.1f}", x0, yy, 0, x1, yy + 0.05, 2.5, white)
        L.box(f"row-fascia-{k}", x0 if sgn > 0 else x0, b["y"], 2.2, x1, b["y"] + b["h"], 2.5,
              L.mat(f"print-row{k}", col, 0.55))


def far_hall():
    """north of the islands, up to the north wall: a few simple booths and high-table zones either side of the walk
    (from x -0.6 at y -4.5 to about (2.0, 9.0), looking at the screen): kept sparse, as John remembers it: islands in
    the side zones outside the stairwells, a few high tables by the side walls, nothing between the stairwells"""
    wall = L.mat("shell-white", 0xeeeff1, 0.6)
    k = 0

    def block(x0, x1, y0, y1, face):
        # a two-sided island: spine along y, cross walls every 3 m, branded backwalls on the faced side(s)
        nonlocal k
        xs = (x0 + x1) / 2
        L.box(f"far-spine-{k}", xs - 0.05, y0, 0, xs + 0.05, y1, 2.5, wall)
        y = y0
        while y < y1 + 0.01:
            L.box(f"far-cross-{k}-{y:.1f}", x0, y - 0.05, 0, x1, y + 0.05, 2.5, wall)
            y += 3.0
        y = y0
        while y + 3.0 < y1 + 0.01:
            for f in face:
                name, col = GENERIC[(k + 3) % len(GENERIC)]
                k += 1
                stand_face(f"far{k}", xs + (0.05 if f == "+x" else -0.05), y, y + 3.0, f, col, 0xffffff, name)
                ex = x1 if f == "+x" else x0
                counter(f"far{k}-counter", ex - 0.65 if f == "+x" else ex + 0.05, y + 0.9, ex - 0.05 if f == "+x" else ex + 0.65,
                        y + 2.1, col)
            y += 3.0
    block(-16.0, -12.0, -0.5, 11.5, ("-x", "+x"))  # west side zone
    block(15.2, 19.6, -0.5, 11.5, ("-x", "+x"))    # east side zone
    for i, (x, y) in enumerate(((-21.0, 2.0), (-21.2, 6.0), (-21.0, 14.5), (20.8, 13.0), (20.9, 15.6))):
        high_table(f"far-table-{i}", x, y, s=0.6, h=1.1)


def open_floor():
    """between the steps and the islands: fridges and catering (inside_hollywood)"""
    # measured in inside_hollywood: backs against the central columns (row -20.75)
    fridge_v("fridge-coke", -4.0, -21.8, "coke", 0.9)
    fridge_v("fridge-water", 2.82, -21.8, "water", 1.38)


def fridge_v(name, x, y, kind, w):
    fridge(name, x, y, kind, w)


# ---------------------------------------------------------------------------------- dressing (photo frame)
def entrance():
    black = L.mat("track-black", 0x0c0c0e, 0.4, metal=0.4)
    cloud = L.mat("cloud", 0x0b0d17, 0.95, bump=0.6, bump_scale=40)
    L.box("cloud-l", -5.6, -2.7, 3.11, -3.0, -0.1, 3.3, cloud)
    L.box("cloud-r", 2.93, -2.7, 3.11, 5.6, -0.1, 3.3, cloud)
    lens = L.emissive("spot-lens", 0xfff3e0, 400.0)
    top = HIGH / SZ
    for y in (-2.45, -4.2):
        L.box(f"track-{y}", -8, y - 0.02, top - 0.05, 8, y + 0.02, top, black)
        for x in (-6.1, -4.3, -2.6, -0.77, 1.29, 3.0, 4.8, 6.5):
            L.cylinder(f"spot-{x}-{y}", x, y, top - 0.25, top - 0.06, 0.045, black, segs=12)
    for x in (-0.77, 1.29):
        L.sphere(f"spot-on-{x}", (x, -2.45, top - 0.27), 0.035, lens)
        L.spot(f"spotlight-{x}", (x, -2.45, top - 0.3), (x * 1.5, 12.0, 0.8), 120, angle_deg=40, blend=0.8, color=(1, 0.95, 0.88))
    # spot heads on the black clouds at the top corners
    for x in (-5.0, -4.2, -3.4, 3.5, 4.3, 5.1):
        L.cylinder(f"cloud-spot-{x}", x, -1.0, 2.86, 3.11, 0.045, black, segs=12)


# ---------------------------------------------------------------------------------- hanging plants
def hanging_plant(name, x0, y0, x1, y1, z, rng, strands=46, reach=0.85):
    """trailing pothos from a hidden trough: leaf cards strung down vines"""
    leaf_a = L.mat("leaf-a", 0x24401f, 0.55, bump=0.2, bump_scale=30)
    leaf_b = L.mat("leaf-b", 0x3b5c2a, 0.5, bump=0.2, bump_scale=30)
    verts, faces, mats = [], [], []
    for s in range(strands):
        t = rng.random()
        px, py = x0 + (x1 - x0) * t + rng.gauss(0, 0.06), y0 + (y1 - y0) * t + rng.gauss(0, 0.06)
        length = reach * (0.35 + 0.65 * rng.random())
        n = int(length / 0.07)
        sway = rng.uniform(-0.08, 0.08)
        for k in range(n):
            f = k / max(n - 1, 1)
            cx, cy, cz = px + sway * f + rng.gauss(0, 0.02), py + sway * f * 0.5 + rng.gauss(0, 0.02), z - 0.04 - f * length
            size = rng.uniform(0.09, 0.16) * (1.2 - 0.4 * f)
            ang = rng.uniform(0, 2 * math.pi)
            tilt = rng.uniform(-0.9, 0.9)
            ux, uy = math.cos(ang) * size, math.sin(ang) * size
            i = len(verts)
            verts += [(cx, cy, cz), (cx + ux * 0.5 - uy * 0.35, cy + uy * 0.5 + ux * 0.35, cz - size * 0.3 + tilt * 0.05),
                      (cx + ux, cy + uy, cz - size * 0.6), (cx + ux * 0.5 + uy * 0.35, cy + uy * 0.5 - ux * 0.35,
                                                            cz - size * 0.3 - tilt * 0.05)]
            faces.append((i, i + 1, i + 2, i + 3))
            mats.append(0 if rng.random() < 0.6 else 1)
    ob = L.mesh_obj(name, verts, faces)
    ob.data.materials.append(leaf_a)
    ob.data.materials.append(leaf_b)
    for p, m in zip(ob.data.polygons, mats):
        p.material_index = m
    trough = L.mat("trough", 0x2a2a2a, 0.7)
    L.box(name + "-trough", min(x0, x1) - 0.12, min(y0, y1) - 0.12, z - 0.06, max(x0, x1) + 0.12, max(y0, y1) + 0.12,
          z + 0.1, trough)
    return ob


def plants():
    rng = random.Random(11)
    hanging_plant("plant-1", -2.25, 0.5, -2.25, 2.0, 3.28, rng, strands=90, reach=0.95)
    hanging_plant("plant-4", 2.4, 1.5, 2.4, 3.0, 3.28, rng, strands=90, reach=0.95)
    hanging_plant("plant-2", -2.0, 4.45, -0.6, 4.45, 3.1, rng, strands=80)
    hanging_plant("plant-3", 0.8, 4.45, 2.2, 4.45, 3.1, rng, strands=80)
    hanging_plant("plant-5", -1.6, 9.6, -0.2, 9.6, 2.98, rng, strands=34, reach=0.7)
    hanging_plant("plant-6", 0.9, 9.6, 2.3, 9.6, 2.98, rng, strands=34, reach=0.7)


def fridge(name, x, y, kind, w=0.62):
    d, h = 0.65, 2.0
    if kind == "coke":
        body, head = L.mat("coke-red", 0xc4121c, 0.4), L.mat("coke-red", 0xc4121c, 0.4)
    else:
        body, head = L.mat("fridge-white", 0xe8eaec, 0.35), L.mat("fridge-white", 0xe8eaec, 0.35)
    L.box(name, x - w / 2, y, 0, x + w / 2, y + d, h, body, bevel=0.01)
    L.box(name + "-glass", x - w / 2 + 0.05, y - 0.005, 0.15, x + w / 2 - 0.05, y + 0.01, h - 0.3,
          L.mat("fridge-glass-lit", 0xdfeaf5, 0.2, emit=0xe6f0ff, strength=2.5))
    if kind == "coke":
        label("Coca-Cola", 0.12, x, y, h - 0.24, L.emissive("white-text", 0xffffff, 3.0))


def high_table(name, x, y, s=0.56, h=1.08):
    blk = L.mat("table-black", 0x111111, 0.35, metal=0.5)
    t = 0.02
    for dx in (-s / 2, s / 2 - t):
        for dy in (-s / 2, s / 2 - t):
            L.box(f"{name}-leg{dx:.2f}{dy:.2f}", x + dx, y + dy, 0, x + dx + t, y + dy + t, h, blk)
    for z in (0.0, h - t):
        L.box(f"{name}-fx{z}", x - s / 2, y - s / 2, z, x + s / 2, y - s / 2 + t, z + t, blk)
        L.box(f"{name}-bx{z}", x - s / 2, y + s / 2 - t, z, x + s / 2, y + s / 2, z + t, blk)
        L.box(f"{name}-lx{z}", x - s / 2, y - s / 2, z, x - s / 2 + t, y + s / 2, z + t, blk)
        L.box(f"{name}-rx{z}", x + s / 2 - t, y - s / 2, z, x + s / 2, y + s / 2, z + t, blk)
    L.box(f"{name}-top", x - s / 2, y - s / 2, h, x + s / 2, y + s / 2, h + 0.012, L.mat("table-top", 0x1a1a1c, 0.2))



# ---------------------------------------------------------------------------------- dressing from the photos (photo frame)
def furniture():
    for i, (x, y) in enumerate(((-0.83, 0.5), (0.95, 0.5), (2.8, 0.5), (-3.35, 0.5), (-5.2, 2.6), (5.0, 1.0),
                                 (-1.2, 6.2), (0.9, 7.0))):
        high_table(f"table-{i}", x, y)
    steel = L.mat("steel", 0xb8bcc0, 0.3, metal=0.9)
    L.box("trolley-top", 2.5, 3.6, 0.85, 3.45, 4.1, 0.88, steel)
    L.box("trolley-mid", 2.5, 3.6, 0.45, 3.45, 4.1, 0.48, steel)
    L.box("trolley-packs", 2.55, 3.65, 0.88, 3.4, 4.05, 1.12, L.mat("water-packs", 0xd9e6f0, 0.25))
    for i, (x, y) in enumerate(((6.0, 6.0), (6.9, 5.45))):
        L.cylinder(f"stool-leg-{i}", x, y, 0, 0.72, 0.02, steel, segs=8)
        L.cylinder(f"stool-seat-{i}", x, y, 0.72, 0.78, 0.18, L.mat("stool-blue", 0x2350b8, 0.5), segs=20)


def booth_wall(name, x0, x1, y, h, mat, depth=0.08):
    return L.box(name, x0, y, 0, x1, y + depth, h, mat)


def screen(name, cx, y, cz, w, color=0x3a64c8, strength=2.0):
    hh = w * 9 / 16 / 2
    L.box(name + "-bezel", cx - w / 2 - 0.02, y - 0.04, cz - hh - 0.02, cx + w / 2 + 0.02, y, cz + hh + 0.02,
          L.mat("bezel", 0x0a0a0c, 0.3))
    L.box(name, cx - w / 2, y - 0.045, cz - hh, cx + w / 2, y - 0.04, cz + hh,
          L.mat(f"scr-{name}", color, 0.2, emit=color, strength=strength))


def photo_booths():
    """the two island heads as the photos show them: JetBrains / Kotlin (left) and ING's concrete TV wall, orange
    IT tower, 'Wear it to get it' wall and red counter (right); positions from the master photo (the TV wall is
    triangulated with orange_guys)"""
    white_txt = L.emissive("white-text", 0xffffff, 3.0)
    y = 7.15
    jb = L.mat("jetbrains-black", 0x17121f, 0.6)
    booth_wall("jb", -8.6, -6.45, y, 2.25, jb)
    L.box("jb-purple", -8.6, y - 0.005, 0.0, -6.45, y, 0.55, L.mat("kotlin-purple", 0x6a2ad6, 0.5, emit=0x6a2ad6,
                                                                       strength=0.4))
    label("JETBRAINS", 0.13, -8.35, y, 1.92, white_txt, align="LEFT")
    label("Kotlin", 0.3, -8.35, y, 1.45, white_txt, align="LEFT")
    kot = L.mat("kotlin-pink", 0xc5249f, 0.5, emit=0xc5249f, strength=0.6)
    booth_wall("kotlin", -6.45, -5.1, y - 0.15, 2.32, kot)
    screen("kotlin-scr", -5.77, y - 0.15, 1.35, 1.05, color=0xf0f0f4, strength=1.6)
    y = 6.79
    gwhite = L.mat("google-white", 0xf4f5f7, 0.6)
    orange = L.mat("orange", 0xff6a13, 0.5, emit=0xff6a13, strength=0.5)
    L.box("orange-pillar", 4.6, y - 0.25, 0, 4.78, y + 0.05, 2.27, orange)
    concrete = tex_mat("concrete", "concrete", 1.2, 0x9b958e, 0.85)
    booth_wall("concrete", 4.78, 7.55, y, 2.27, concrete)
    screen("tv", 5.97, y, 1.635, 1.21, color=0x2d56c4, strength=2.5)
    L.box("orange-bar", 4.9, y - 0.03, 2.12, 5.7, y, 2.14, L.emissive("orange-led", 0xff8a3c, 8.0))
    L.box("drape", 7.55, y - 0.2, 0, 7.95, y, 2.3, L.mat("drape", 0x7d8086, 0.95, bump=0.3, bump_scale=8))
    booth_wall("it-tower", 7.95, 9.55, y - 0.6, 2.6, orange, depth=0.6)
    label("IT", 0.5, 8.9, y - 0.6, 1.6, L.mat("it-purple", 0x7b3fe4, 0.5))
    booth_wall("wear-it", 9.9, 11.9, y, 2.4, gwhite)
    label("Wear it to get it", 0.17, 10.9, y, 1.6, L.mat("wear-blue", 0x1f4fbf, 0.5))
    label("ING", 0.3, 6.2, y, 2.3, L.mat("ing-orange", 0xff6200, 0.5))
    L.box("counter-red", 8.3, 4.6, 0, 11.6, 5.3, 0.95, L.mat("counter-red", 0xd31f3a, 0.5))
    L.box("counter-top", 8.25, 4.55, 0.95, 11.65, 5.35, 0.99, gwhite)
    L.box("podium", 8.3, 3.9, 0, 8.9, 4.5, 1.0, L.mat("counter-red", 0xd31f3a, 0.5))
    L.box("platform", 3.2, 2.8, 0, 5.3, 4.3, 0.4, gwhite)


def lights(unified):
    if not unified:
        # the photos are exposed for the crowd: a soft lift over the floor (photo renders only)
        L.area_light("lift", (0, 8, 2.9), 20, 700, color=(0.95, 0.95, 1.0), size_y=18)
    # blue LED wash on the dark entrance ceiling and the ING booth's red uplight (both in the photos)
    L.area_light("entrance-blue", (0, -3.5, 2.9), 12, 700, color=(0.25, 0.35, 1.0), size_y=3, rot=(math.pi, 0, 0))
    L.area_light("it-red", (9.2, 5.6, 2.75), 2.5, 350, color=(1.0, 0.22, 0.12), size_y=0.6, rot=(math.radians(150), 0, 0))


UNIFIED = False


def build(root, unified=False):
    """unified=True: only what this module owns (floor 0 from y -37.4 north: landing, hall steps, hall, its walls
    and ceilings), closed and lightproof, no world / view / per-photo settings."""
    global ROOT, FONT, UNIFIED
    from mathutils import Matrix
    ROOT = Path(root)
    FONT = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"
    UNIFIED = unified
    architecture(unified)
    fixtures()
    side_ceilings()
    islands()
    outer_rows()
    open_floor()
    far_hall()
    before = set(bpy.context.scene.objects)
    entrance()
    plants()
    furniture()
    photo_booths()
    lights(unified)
    M = Matrix(((SX, 0, 0, X0), (0, SY, 0, Y0), (0, 0, SZ, 0), (0, 0, 0, 1)))   # PHOTO_TO_VENUE
    bpy.context.view_layer.update()          # matrix_world must include the rotations set by the helpers
    for ob in set(bpy.context.scene.objects) - before:
        ob.matrix_world = M @ ob.matrix_world
    if not unified:
        L.world_color(0x000000, 0.0)


EXPOSURE = -0.4
# each photo was exposed and white-balanced on its own: match the camera, not the room (photo renders only)
GRADE = {"inside_hollywood_w_booths_and_people": (-0.7, 5200), "inside_hollywood": (0.0, 6200),
         "inside_hollywood_w_ing_orange_guys": (-0.3, 7400)}


def before_render(name):
    if UNIFIED or name not in GRADE:
        return
    vs = bpy.context.scene.view_settings
    exp, temp = GRADE[name]
    vs.exposure = exp
    if hasattr(vs, "use_white_balance"):
        vs.use_white_balance = True
        vs.white_balance_temperature = temp
