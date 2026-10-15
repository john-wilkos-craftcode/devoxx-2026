"""Dressed Hollywood booths, confined to the original floor plates.

Local u runs along the graphic, v points into the stand. Reject entire stands
against conservatively expanded walk lanes before creating any geometry.
"""
import math

import bpy
from mathutils import Vector

LANES = (
    ((-6, -34), (0, -25), (0, 5), (5.9, 11), (5.9, 14.1)),
    ((5.9, 14.1), (8.8, 12.5), (11.4, 12.5)),
    ((5.9, 14.1), (-3.4, 12.5), (-6, 12.5)),
    ((9.1, 13.85), (8.7, 12.85)),
)
BRANDS = (
    ('JETBRAINS', 0x25123F), ('Kotlin', 0x853EE8),
    ('Google Cloud', 0xF4F5F7), ('ASML', 0x003CFF),
    ('BIT', 0xEC641C), ('Arcade Corner', 0xCF285C),
    ('OpenRewrite', 0x132D60), ('NORTHSTACK', 0x206A81),
    ('LUMEN', 0x080B10), ('ByteGarden', 0x00C99A),
    ('FluxWorks', 0xFF5900), ('VECTOR', 0x233AFF),
    ('CloudNest', 0x00B9D6), ('PATCHLAB', 0xF00091),
    ('OrbitDB', 0x6551A1), ('SignalForge', 0xB18A29),
    ('Nimble', 0x288A90), ('Kernel & Co', 0x404958),
    ('THREAD', 0x914A49), ('BlueCircuit', 0x236CB0),
    ('PrismOps', 0x9256AE), ('CEDAR', 0x52785A),
    ('DataHarbor', 0x306071), ('STACKWISE', 0x996C37),
    ('CopperCode', 0xAD6143), ('NovaMesh', 0x615B85),
    ('TIDAL', 0x25817B),
)


def replaces(e):
    """Only the hall's original booth plates, walls and 1 m counters."""
    b = e.get('bounds', {})
    if not b or e.get('floor', 0) != 0 or e.get('linkId'):
        return False
    if not (-23.5 <= b['x'] and b['x']+b['w'] <= 28.8
            and -37.4 <= b['y'] and b['y']+b['h'] <= 18.3):
        return False
    dims = (round(b['w'], 3), round(b['h'], 3))
    return ((e.get('material') == 'booth'
             and ((dims in ((3, 2), (4, 6)) and e.get('height') == .05)
                  or (dims in ((.1, 2), (.1, 6), (4, .1))
                      and e.get('height') == 2.5)))
            or (e.get('material') == 'desk' and e.get('height') == 1
                and dims in ((.6, 1.1), (.6, 2.4))))


def lane_overlap(b):
    """Segment/slab clipping against the footprint expanded by 1.3 m.

    Square expansion is slightly conservative at corners, never under-clear.
    """
    limits = ((b['x']-1.3, b['x']+b['w']+1.3),
              (b['y']-1.3, b['y']+b['h']+1.3))
    for line in LANES:
        for a, c in zip(line, line[1:]):
            lo, hi = 0., 1.
            for axis, (mn, mx) in enumerate(limits):
                delta = c[axis]-a[axis]
                if abs(delta) < 1e-9:
                    if not mn <= a[axis] <= mx:
                        hi = -1
                        break
                else:
                    t0, t1 = sorted(((mn-a[axis])/delta, (mx-a[axis])/delta))
                    lo, hi = max(lo, t0), min(hi, t1)
            if lo <= hi:
                return True
    return False


def build(g):
    B, M = g['B'], g['M']
    for key, color, metal in (('boothsWhite', 0xF2F2EE, 0),
                              ('boothsBlack', 0x101318, .5),
                              ('boothsAluminium', 0xBDC4CB, .85),
                              ('boothsWood', 0xCBA77A, 0)):
        M[key] = g['material'](key, color, rough=.45, metal=metal)
    plates = [e for e in g['venue']['decor']
              if replaces(e) and e.get('height') == .05]
    plates.sort(key=lambda e: (-e['bounds']['h'], e['bounds']['x'], e['bounds']['y']))
    # The booths under the coffer go (the photo's central aisle is open floor);
    # the row just east of it moves 1.3 m east so it lines that aisle.
    aisle = g['coffer']

    def blocked(b):
        return (b['x'] < aisle['x']+aisle['w'] and b['x']+b['w'] > aisle['x']
                and b['y'] < aisle['y']+aisle['h']+6 and b['y']+b['h'] > aisle['y'])

    def shifted(b):
        dx = 1.3 if abs(b['x']-9.6) < .25 or abs(b['x']-(9.6+3-.1)) < .25 else 0
        return dict(b, x=b['x']+dx)

    plates = [dict(e, bounds=shifted(e['bounds'])) for e in plates]
    walls = [shifted(e['bounds']) for e in g['venue']['obstacles']
             if replaces(e) and e.get('material') == 'booth'
             and e['bounds']['w'] == .1]
    for index, plate in enumerate(plates):
        b = plate['bounds']
        if blocked(b) or lane_overlap(b):
            continue
        g.setdefault('booths', []).append(b)
        wall = next(w for w in walls if abs(w['y']-b['y']) < .001
                    and b['x']-.001 <= w['x'] <= b['x']+b['w']
                    and abs(w['h']-b['h']) < .001)
        east = wall['x'] < b['x']+b['w']/2
        sign = 1 if east else -1
        origin = (b['x'] if east else b['x']+b['w'],
                  b['y'] if east else b['y']+b['h'])
        length, depth, big = b['h'], b['w'], b['h'] > 2
        name, color = BRANDS[index % len(BRANDS)]
        key = f'boothsBrand{index}'
        M[key] = g['material'](key, color, emission=color, strength=1.0)
        side = f'boothsSide{index}'
        M[side] = g['material'](side, color, emission=color, strength=.8)
        ink = f'boothsInk{index}'
        ink_color = (0x163ABF if name == 'Google Cloud' else
                     0x9DFF00 if name == 'LUMEN' else 0xFFFFFF)
        M[ink] = g['material'](ink, ink_color, emission=ink_color, strength=2)
        slide = f'boothsSlide{index}'
        M[slide] = g['material'](slide, 0xA6DFFF, emission=0xA6DFFF, strength=4)

        def point(u, v, z):
            return (origin[0]+sign*v, origin[1]+sign*u, z)

        def box(mat, u, v, w, d, z, h):
            p, q = point(u, v, z), point(u+w, v+d, z)
            B.box(mat, dict(x=min(p[0], q[0]), y=min(p[1], q[1]), w=d, h=w), z, z+h)

        def cylinder(mat, u, v, z, h, radius):
            x, y, _ = point(u, v, z)
            g['cylinder'](mat, x, y, z, z+h, radius, 24)

        def label(body, u, v, z, width, mat=None, reverse=False,
                  letter_height=None):
            mat = ink if mat is None else mat
            size = letter_height or min(.42, width / max(len(body)*.75, 1))
            ob = g['text_object'](body, size, point(u, v, z),
                                  (math.pi/2, 0, sign*math.pi/2 + (math.pi if reverse else 0)),
                                  M[mat], .001, 0)
            # Constrain actual font bounds as well as the initial estimate.
            g['scene'].view_layers[0].update()
            # Local x runs along the wall, local y is the letter height, local z the extrusion.
            if letter_height and ob.dimensions.y > 0:
                s = letter_height/ob.dimensions.y
                ob.scale = (ob.scale.x*s, ob.scale.y*s, ob.scale.z)
                g['scene'].view_layers[0].update()
            if ob.dimensions.x > width:
                # Preserve readable letter height; fit long brands horizontally.
                ob.scale.x *= width/ob.dimensions.x

        B.box('boothsWood' if big else key, b, .002, .05)
        box('boothsAluminium', 0, 0, length, .10, .05, 2.55)
        box(key, .035, .10, length-.07, .018, .085, 2.48)
        box(key, .035, -.018, length-.07, .018, .085, 2.48)
        if name in ('Kotlin', 'PATCHLAB'):
            # Continuous purple-to-magenta fabric gradient along the wall.
            nt = M[key].node_tree
            tex = nt.nodes.new('ShaderNodeTexCoord')
            sep = nt.nodes.new('ShaderNodeSeparateXYZ')
            ramp = nt.nodes.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].color = (.18, .025, .65, 1)
            ramp.color_ramp.elements[1].color = (1, .025, .23, 1)
            nt.links.new(tex.outputs['Generated'], sep.inputs[0])
            nt.links.new(sep.outputs['Y'], ramp.inputs[0])
            bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
            nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
            nt.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
        for face, reverse in ((.145, False), (-.045, True)):
            label(name, length/2, face, 2.28, length-.22, ink,
                  reverse=reverse, letter_height=.48 if big else .35)
            label('CREATE. CONNECT.', length/2, face, 1.94, length-.25,
                  ink, reverse=reverse, letter_height=.12)
            if name == 'LUMEN':
                box(ink, .06, face, length-.12, .008, .35, .045)
        if name == 'Google Cloud':
            for j, col in enumerate((0x4285F4, 0xEA4335, 0xFBBC04, 0x34A853)):
                accent = f'boothsGoogle{j}'
                M[accent] = g['material'](accent, col, emission=col, strength=2)
                for face in (.135, -.035):
                    box(accent, length/2-.7+j*.35, face, .30, .01, 1.78, .06)
        # 55-inch 16:9 display: 1.218 x .685 m plus bezel.
        box('boothsBlack', length/2-.635, .15, 1.27, .07, 1.13, .735)
        box(slide, length/2-.609, .222, 1.218, .008, 1.155, .685)
        label('BUILD / CONNECT', length/2, .235, 1.51, 1.05, 'boothsBlack')
        cw = 2.4 if big else .85
        box('boothsWhite', .12, depth-.80, cw, .60, .05, 1.05)
        box(key, .16, depth-.19, cw-.08, .012, .29, .53)
        label(name, .12+cw/2, depth-.17, .57, cw-.13,
              ink)
        for u in ((3.4, 4.8) if big else (1.40,)):
            v = 2.35 if big else 1.85
            cylinder('boothsBlack', u, v, .05, .04, .23)
            cylinder('boothsBlack', u, v, .09, 1.02, .035)
            cylinder('boothsWhite', u, v, 1.11, .04, .30)
            for sv in (v-.57, v+.57):
                cylinder('boothsBlack', u, sv, .05, .04, .20)
                cylinder('boothsAluminium', u, sv, .09, .69, .025)
                cylinder('boothsWood', u, sv, .78, .07, .21)
                cylinder('boothsAluminium', u, sv, .34, .025, .13)
        if big:
            for u in (0, length-.06):
                box('boothsAluminium', u, .10, .06, 1., .05, 2.55)
                for face in (u-.012, u+.06):
                    box(side, face, .12, .012, .96, .09, 2.45)
            box('boothsAluminium', .18, .82, length-.36, .05, 2.72, .06)
            for j, u in enumerate((.65, length/2, length-.65)):
                box('boothsBlack', u-.09, .75, .18, .20, 2.57, .14)
                data = bpy.data.lights.new(f'booths-{index}-spot-{j}', 'SPOT')
                data.energy, data.spot_size, data.spot_blend = 150, 1.3, .65
                data.shadow_soft_size = .08
                ob = bpy.data.objects.new(data.name, data)
                g['scene'].collection.objects.link(ob)
                ob.location = point(u, .83, 2.56)
                ob.rotation_euler = (Vector(point(u, .12, 1.55))-ob.location).to_track_quat('-Z', 'Y').to_euler()
        if big and index % 2 == 0:
            box('boothsBlack', length-1.05, depth-.65, .85, .40, .05, .05)
            box(key, length-1., depth-.48, .75, .025, .10, 1.85)
            label(name, length-.625, depth-.44, 1.65, .65)
