"""Reception finishes and furniture; metres, floor z=1.2, north limit y=-37.4.

The x=-6 walk lane is clear for 2.4 m. All new furnishings stay outside it;
ceiling underside is 3.2 m above the floor. Facade and hall are owned elsewhere.
"""
import math
import random

import bpy
from mathutils import Vector


def white_structure(e):
    """Reception columns and east-side walls, without changing adjacent rooms."""
    b = e['bounds']
    return (e.get('floor', 0) == 0 and not e.get('hidden')
            and not e.get('linkId') and not e.get('exterior')
            and e.get('height', 0) >= 3
            and -13.6 <= b['x'] + b['w']/2 <= 22.7
            and -60.4 < b['y'] + b['h']/2 < -37.4
            and ((b['w'] < 1.2 and b['h'] < 1.2) or b['x'] >= -1.5))


def replaces(e):
    """Replace desks, exterior headers and locally refinished structure."""
    b = e['bounds']
    contained = (e.get('floor', 0) == 0 and b['x'] >= -13.6
                 and b['x'] + b['w'] <= 22.7 + 1e-6 and b['y'] >= -60.4
                 and b['y'] + b['h'] <= -37.4 + 1e-6)
    return white_structure(e) or (contained and (
        e.get('material') == 'desk' or e.get('exterior', False)))


def build(g):
    B, M = g['B'], g['M']
    room = next(r for r in g['rooms'] if r['id'] == 'reception')
    floor = room.get('elevation', 0) + room['floor'] * g['FH']
    ceiling = floor + 3.2
    for key, color, rough, metal in (
        ('receptionWhite', 0xF3F1ED, .38, 0),
        ('receptionWood', 0xC7A67A, .55, 0),
        ('receptionCeiling', 0x4A5578, .98, 0),
        ('receptionBlack', 0x11151B, .24, .75),
        ('receptionBelt', 0x1D3FD0, .9, 0),
        ('receptionWall', 0xE6E6E3, .92, 0),
    ):
        M[key] = g['material'](key, color, rough, metal,
                              noise_bump=.65 if key == 'receptionCeiling' else 0)
    M['receptionCarpet'] = g['textured']('receptionCarpet', 'carpet', .6,
                                       tint=0x303A48, normal=1.0, tiles=.5)
    M['receptionGlow'] = g['material']('receptionGlow', 0xF3F7FF,
                                     emission=0xF3F7FF, strength=4)
    M['receptionBlueEdge'] = g['material']('receptionBlueEdge', 0xB8C8FF,
                                         emission=0xB8C8FF, strength=1.2)
    M['receptionSlide'] = g['material']('receptionSlide', 0x233FBA,
                                      emission=0x334EDB, strength=.8)
    M['receptionPurple'] = g['material']('receptionPurple', 0x7848C5,
                                       emission=0x7848C5, strength=.6)

    def box(key, x, y, w, d, z, h):
        B.box(key, dict(x=x, y=y, w=w, h=d), z, z+h)

    def rounded(key, x, y, w, d, z, h, radius):
        # Real rounded footprint, not just a shader bevel.
        ring = []
        for cx, cy, start in ((x+w-radius, y+d-radius, 0),
                              (x+radius, y+d-radius, 90),
                              (x+radius, y+radius, 180),
                              (x+w-radius, y+radius, 270)):
            for i in range(7):
                a = math.radians(start+i*15)
                ring.append((cx+radius*math.cos(a), cy+radius*math.sin(a)))
        n = len(ring)
        B.mesh(key, [(a, b, c) for c in (z, z+h) for a, b in ring],
               [tuple(reversed(range(n))), tuple(range(n, 2*n))]
               + [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)])

    def light(name, loc, target, power, color, size=1, spot=False):
        data = bpy.data.lights.new(name, 'SPOT' if spot else 'AREA')
        data.energy, data.color = power, color
        if spot:
            data.spot_size, data.spot_blend, data.shadow_soft_size = .95, .65, .08
        else:
            data.shape, data.size = 'DISK', size
        ob = bpy.data.objects.new(name, data)
        g['scene'].collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(target)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

    # Thin finish above the existing structural slab; keep the staircase void open.
    stair = next(l['bounds'] for l in g['venue']['links'] if l['id'] == 'grand-stair')
    for cell in g['subtract_rects'](room['bounds'], [stair]):
        B.box('receptionCarpet', cell, floor+.001, floor+.008)
        B.box('receptionCeiling', cell, ceiling, ceiling+.12)

    for element in g['venue']['obstacles']:
        if white_structure(element):
            B.box('receptionWall', element['bounds'], floor, ceiling)

    # Upward-facing wash, 30 cm below the sprayed-plaster ceiling.
    for x in (-10, -1, 8, 18):
        for y in (-55, -42):
            light(f'reception-ceiling-wash-{x}-{y}', (x, y, ceiling-.30),
                  (x, y, ceiling), 400, (.32, .38, 1), 3)

    # West-facing counters north of the grand stair, east of the protected lane.
    for y in (-47.6, -45.2, -42.8):
        rounded('receptionWhite', -3.9, y, 1.05, 2.34, floor+.06, .94, .15)
        rounded('receptionWood', -3.94, y-.025, 1.13, 2.39, floor+1, .05, .17)
        for dy in (.55, 1.75):
            yy = y+dy
            rounded('receptionBlack', -3.55, yy-.12, .28, .24, floor+1.05, .025, .03)
            box('receptionBlack', -3.44, yy-.025, .035, .05, floor+1.075, .16)
            box('receptionBlack', -3.47, yy-.16, .045, .32, floor+1.22, .23)
            box('receptionSlide', -3.473, yy-.145, .003, .29, floor+1.235, .20)

    box('receptionWall', -1.45, -48, .14, 8.3, floor, 3.2)
    for i in range(56):
        box('receptionWood', -1.51, -47.95+i*.145, .06, .065, floor+.08, 3.04)
    box('receptionBlack', -1.63, -44.7, .1, 1.46, floor+1.65, .85)
    box('receptionSlide', -1.638, -44.67, .008, 1.4, floor+1.68, .79)
    box('receptionPurple', -1.648, -43.7, .008, .43, floor+1.68, .79)
    # Text local x follows -y and its normal faces -x toward the queue.
    g['text_object']('DEVOXX', .19, (-1.66, -43.43, floor+2.12),
                     (math.pi/2, 0, -math.pi/2), M['receptionGlow'], .001, 0)
    g['text_object']('WELCOME / CHECK IN', .055, (-1.66, -43.43, floor+1.94),
                     (math.pi/2, 0, -math.pi/2), M['receptionGlow'], .001, 0)

    # Three parallel runs connected alternately form a serpentine queue west of x=-7.2.
    posts = [(x, y) for x in (-12, -10, -8) for y in (-55.8, -52.8, -49.8, -46.8)]
    for x, y in posts:
        g['cylinder']('receptionBlack', x, y, floor+.008, floor+.055, .16, 24)
        g['cylinder']('receptionBlack', x, y, floor+.055, floor+.95, .027, 16)
        g['cylinder']('receptionBlack', x, y, floor+.87, floor+.95, .055, 16)
    for x in (-12, -10, -8):
        box('receptionBelt', x-.018, -55.8, .036, 9, floor+.84, .075)
    for x, y in ((-12, -46.8), (-10, -55.8)):
        box('receptionBelt', x, y-.018, 2, .036, floor+.84, .075)

    # Pendant drum: 2.5 m diameter, 25 cm white band and a luminous diffuser.
    cx, cy, z = -3.2, -44.1, floor+2.75
    g['cylinder']('receptionWhite', cx, cy, z, z+.25, 1.25, 96)
    g['cylinder']('receptionGlow', cx, cy, z-.008, z-.002, 1.23, 96)
    verts = [(cx+r*math.cos(i*math.tau/96), cy+r*math.sin(i*math.tau/96), z-.009)
             for r in (1.23, 1.25) for i in range(96)]
    for i in range(96):
        j = (i+1) % 96
        B.mesh('receptionBlueEdge', [verts[k] for k in (i, j, 96+j, 96+i)], [(0, 1, 2, 3)])
    g['cylinder']('receptionBlack', cx, cy, z+.25, ceiling, .006, 8)
    light('reception-ring', (cx, cy, z-.02), (cx, cy, floor), 1200, (.96, .98, 1), 2.3)
    for x in (-10.5, -3.2, 16):
        box('receptionWhite', x-.035, -57, .07, 17, ceiling-.035, .035)
        for y in (-55, -50, -45, -41):
            g['cylinder']('receptionWhite', x, y, ceiling-.08, ceiling, .075, 16)
            light(f'reception-spot-{x}-{y}', (x, y, ceiling-.09),
                  (x, y, floor), 600, (1, .84, .67) if x == -3.2 else (.85, .93, 1), spot=True)

    # Instance the same Poly Haven tree meshes as the hall, in cylindrical white pots.
    for index, (x, y) in enumerate(((-11.4, -58.2), (19.5, -58.2), (.8, -40.6))):
        g['cylinder']('receptionWhite', x, y, floor+.008, floor+.68, .38, 48)
        g['cylinder']('soil', x, y, floor+.68, floor+.685, .34, 32)
        sources = [g['pachira'].get(k) for k in ('leaves_d', 'bark_d')]
        sources = [src for src in sources if src is not None]
        # Bound every crown to 1.2 m horizontally and 2.35 m above the soil.
        points = [Vector(c) for src in sources for c in src.bound_box]
        scale = min(1., 1.2/max([abs(p.x) for p in points]+[abs(p.y) for p in points]+[.01]),
                    2.35/max([p.z for p in points]+[.01]))
        for src in sources:
            ob = src.copy()
            ob.name = f'reception-palm-{index}-{src.name}'
            ob.location, ob.scale = (x, y, floor+.685), (scale,)*3
            ob.rotation_euler = (0, 0, index*.8)
            g['scene'].collection.objects.link(ob)

    # Hall greenery is inline, not a helper: reuse its folded-leaf construction/material.
    box('receptionWood', -2, -47.6, .48, 7.2, floor+2.88, .05)
    rng = random.Random(2026)
    for i in range(75):
        x, y, zz = -2+rng.uniform(0, .3), -47.5+rng.uniform(0, 6.9), floor+2.94
        for j in range(rng.randint(7, 22)):
            zz -= .025
            c = Vector((x+rng.uniform(-.025, .025), y+rng.uniform(-.03, .03), zz))
            u = Vector((-.025, .035 if j % 2 else -.035, -.045))
            v = Vector((.012, .026, .012))
            B.mesh('foliage', [c, c+u*.35+v, c+u, c+u*.35-v], [(0, 1, 2), (0, 2, 3)])
