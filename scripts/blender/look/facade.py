"""Street-facing envelope; the walk-through opening remains at x=-6, y=-60.4."""
import math
import random

import bpy
from mathutils import Matrix, Vector
from bpy.app.handlers import persistent


def build(g):
    B, M = g['B'], g['M']
    specs = [
        ('facadeMetal', 0xB9BDC2, .32, .35),
        ('facadeRib', 0xAFB4BA, .38, .35),
        ('facadeFrame', 0xF2F3F2, .32, .15),
        ('facadeSilver', 0xBFC5CC, .28, .75),
        ('facadeBlue', 0x1D3FD0, .34, .3),
        ('facadeWindow', 0x9BAAB5, .13, .48),
        ('facadeGlass', 0xE7F0F4, .08, 0),
        ('facadeParapet', 0xD5D7D9, .45, .15),
        ('facadePavers', 0xBA8C89, .87, 0),
        ('facadeJoint', 0x967D7B, .95, 0),
        ('facadeRoad', 0x7A7B7E, .94, 0),
        ('facadeMarking', 0xF5F5EF, .8, 0),
        ('facadeVerge', 0x5D7A3A, .95, 0),
        ('facadeBrick', 0x995C50, .9, 0),
        ('facadeDistantWall', 0xC8CACC, .9, 0),
        ('facadeDistantBand', 0x494C50, .85, 0),
        ('facadeBin', 0x191B1D, .65, .2),
    ]
    for key, color, rough, metal in specs:
        M[key] = g['material'](key, color, rough, metal,
                              noise_bump=.025 if key == 'facadeRoad' else
                              (.12 if key in ('facadePavers', 'facadeVerge') else 0))
    bsdf = M['facadeGlass'].node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Transmission Weight'].default_value = 1
    bsdf.inputs['IOR'].default_value = 1.45

    def box(key, x, y, w, d, z, h):
        B.box(key, dict(x=x, y=y, w=w, h=d), z, z+h)

    def star(key, x, y, z, radius, tilt=0):
        verts = [(x, y, z)]
        for i in range(10):
            a = math.pi/2 + i*math.pi/5 + tilt
            r = radius if i % 2 == 0 else radius*.4
            verts.append((x + math.cos(a)*r, y, z + math.sin(a)*r))
        B.mesh(key, verts, [(0, i+1, (i+1) % 10+1) for i in range(10)])

    def text(body, size, loc, mat='facadeBlue'):
        ob = g['text_object'](body, size, loc, (math.pi/2, 0, 0), M[mat], .012, 0)
        ob.data.align_x = 'LEFT'
        ob.data.font = g['WORD_FONT_EARLY']
        return ob

    y = -60.55
    # Cut real openings in the lower skin; glazing must not sit over solid metal.
    for start, width in [(-34, 20.4), (1.6, 44.4)]:
        windows = [(float(x), 3.3) for x in range(math.ceil(start+1), math.floor(start+width-3.3), 4)]
        solid = []
        cursor = start
        for x, w in windows:
            solid.append((cursor, x-cursor))
            cursor = x+w
            box('facadeGlass', x, y, w, .025, 1.6, 1.65)
            for z in (1.6, 2.14, 2.7, 3.2):
                box('facadeFrame', x, y-.09, w, .12, z, .055)
            for dx in (0, 1.65, w-.055):
                box('facadeFrame', x+dx, y-.09, .055, .12, 1.6, 1.65)
        solid.append((cursor, start+width-cursor))
        box('facadeMetal', start, y, width, .3, 1.2, .4)
        box('facadeMetal', start, y, width, .3, 3.25, 3.05)
        for x, w in solid:
            box('facadeMetal', x, y, w, .3, 1.6, 1.65)
        for i in range(29):
            z = 1.24+i*.18
            for x, w in (solid if 1.6 <= z < 3.25 else [(start, width)]):
                box('facadeRib', x, y-.025, w, .035, z, .018)
    box('facadeMetal', -34, y, 80, .3, 6.3, .48)
    box('facadeWindow', -34, y, 80, .08, 6.78, 3.4)
    for z in (6.78, 7.6, 8.45, 9.3, 10.15):
        box('facadeSilver', -34, y-.06, 80, .12, z, .065)
    for x in range(-34, 47, 3):
        box('facadeSilver', x, y-.06, .05, .12, 6.78, 3.42)
    box('facadeParapet', -34, y-.08, 80, .4, 10.2, 1.65)

    # A threshold under the door bays, from the pavers to the reception floor (z 1.2)
    box('facadeFrame', -13.6, y-.3, 15.2, .5, 1.13, .07)
    # Closed double doors in the outer bays; centre leaves slide aside for the route.
    for index, (a, b) in enumerate([(-13.6, -8.6), (-8.6, -3.5), (-3.5, 1.6)]):
        box('facadeGlass', a, y, b-a, .025, 4.15, 2.15)
        for x in (a, b-.10):
            box('facadeFrame', x, y-.16, .1, .24, 1.2, 5.1)
        box('facadeFrame', a, y-.16, b-a, .24, 4.1, .1)
        leaves = [(a+.1, 1.0), (b-1.1, 1.0)] if index == 1 else [(a+.1, (b-a-.2)/2), ((a+b)/2, (b-a-.2)/2)]
        for x, w in leaves:
            box('facadeGlass', x, y-.1, w, .025, 1.2, 2.9)
            for dx in (0, w-.055):
                box('facadeFrame', x+dx, y-.2, .055, .14, 1.2, 2.9)
            for z in (1.2, 4.045):
                box('facadeFrame', x, y-.2, w, .14, z, .055)
            box('facadeSilver', x+.08, y-.29, w-.16, .065, 2.35, .045)
        lamp = bpy.data.lights.new(f'facade-lobby-{index}', 'AREA')
        lamp.energy, lamp.color, lamp.shape, lamp.size = 180, (1., .73, .45), 'DISK', 2.5
        ob = bpy.data.objects.new(lamp.name, lamp)
        g['scene'].collection.objects.link(ob)
        ob.location = ((a+b)/2, -58.6, 4.05)

    # One painted-metal wordmark only. Explicit alignment fixes its relation to the K/star.
    for ob in list(g['scene'].objects):
        if ob.type == 'FONT' and ob.data.body.strip().upper() in ('KINEPOLIS', 'KINEPOLIS EVENT CENTER') and ob.location.y < -60:
            bpy.data.objects.remove(ob, do_unlink=True)
    sign = text('KINEPOLIS EVENT CENTER', 1.35, (-18, y-.34, 5.5))
    sign.name = 'facade-single-blue-wordmark'
    sign.data.shear, sign.data.extrude, sign.data.offset = .2, .035, .025
    bpy.context.view_layer.update()
    # upright text: its letter height is along its own y (z is the extrusion); scale evenly to 1.1 m letters
    s = 1.1/max(sign.dimensions.y, .01)
    sign.scale = (s, s, 1)
    star('facadeSilver', -18.45, y-.4, 7.25, 1.32, math.radians(18))

    # Forecourt datum stays near the existing route floor (z=1.2).
    box('facadeRoad', -100, -150, 230, 85.85, 1.12, .045)
    box('facadePavers', -34, -64.15, 80, 3.6, 1.17, .07)
    box('facadeParapet', -34, -64.3, 80, .15, 1.16, .08)
    for row in range(6):
        yy = -64.15+row*.6
        box('facadeJoint', -34, yy, 80, .012, 1.24, .007)
        for i in range(134):
            xx = -34+i*.6+(row % 2)*.3
            if xx < 46:
                box('facadeJoint', xx, yy, .012, .6, 1.24, .007)
    box('facadeMarking', -90, -64.65, 184, .25, 1.169, .009)
    for x in range(-90, 94, 8):
        box('facadeMarking', x, -71.9, 3, .14, 1.169, .009)
    # Rounded steel posts, 14 cm diameter, 90 cm overall above the pavement.
    for i in range(32):
        x = -32.5+i*2.5
        if abs(x+6) < 1.35:
            continue
        g['cylinder']('facadeSilver', x, -63.95, 1.24, 2.07, .07, 24)
        verts, faces = [], []
        for ring in range(7):
            angle = ring*math.pi/12
            for j in range(24):
                az = j*math.tau/24
                verts.append((x+.07*math.cos(angle)*math.cos(az), -63.95+.07*math.cos(angle)*math.sin(az), 2.07+.07*math.sin(angle)))
        for ring in range(6):
            for j in range(24):
                faces.append((ring*24+j, ring*24+(j+1)%24, (ring+1)*24+(j+1)%24, (ring+1)*24+j))
        B.mesh('facadeSilver', verts, faces)
    for x in (-15, 3):
        g['cylinder']('facadeFrame', x, -63.85, 1.24, 10.24, .06, 24)
        # Horizontal round top arm, spanning the narrow banner.
        verts = [(xx, -63.85+.025*math.cos(j*math.tau/12), 10.16+.025*math.sin(j*math.tau/12)) for xx in (x, x+.75) for j in range(12)]
        B.mesh('facadeFrame', verts, [(j, (j+1)%12, (j+1)%12+12, j+12) for j in range(12)])
        box('facadeFrame', x+.1, -63.85, .6, .018, 6.14, 4)
        star('facadeBlue', x+.4, -63.88, 9.78, .22)
        t = text('KINEPOLIS', .35, (x+.55, -63.89, 6.45))
        # Rotate in the banner plane: baseline runs from bottom to top.
        t.rotation_euler = (math.pi/2, -math.pi/2, 0)
        bpy.context.view_layer.update()
        s = 2.9/max(t.dimensions.x, .01)       # the word runs 2.9 m up the banner
        t.scale = (s, s, 1)
    g['cylinder']('facadeBin', 2.5, -61.35, 1.24, 2.14, .24, 24)
    g['cylinder']('facadeSilver', 2.5, -61.35, 2.14, 2.18, .26, 24)

    # Opposite verge, brick footpath and parking; no exterior planter boxes.
    box('facadeVerge', -34, -82.8, 128, 3.5, 1.17, .07)
    for kerb_y in (-79.3, -82.95):
        box('facadeParapet', -34, kerb_y, 128, .15, 1.165, .15)
    box('facadeBrick', -34, -85.15, 128, 2.2, 1.17, .07)
    for x in range(-34, 46):
        box('facadeJoint', x, -85, .015, 2.2, 1.24, .007)
    for j in range(7):
        box('facadeJoint', -34, -85+j*.3, 80, .012, 1.24, .007)
    for x in range(-32, 46, 3):
        box('facadeMarking', x, -92, .10, 5, 1.169, .009)
    tree_parts = g['model_parts']('tree_small_02')
    rng = random.Random(26)
    for i, x in enumerate(range(-30, 94, 6)):
        parts = list(tree_parts.values())
        if not parts:
            continue
        # Preserve source transforms, normalize aggregate bounds, and instance shared meshes.
        points = [ob.matrix_world @ Vector(p) for ob in parts for p in ob.bound_box]
        low = Vector(tuple(min(p[k] for p in points) for k in range(3)))
        high = Vector(tuple(max(p[k] for p in points) for k in range(3)))
        scale = rng.uniform(6, 8)/max(high.z-low.z, .01)
        origin = Vector(((low.x+high.x)/2, (low.y+high.y)/2, low.z))
        transform = Matrix.Translation((x, -81.1, 1.24)) @ Matrix.Rotation(rng.uniform(0, math.tau), 4, 'Z') @ Matrix.Scale(scale, 4) @ Matrix.Translation(-origin)
        for source in parts:
            ob = source.copy()
            ob.name = f'facade-broadleaf-{i}-{source.name}'
            ob.parent = None
            ob.matrix_world = transform @ source.matrix_world
            g['scene'].collection.objects.link(ob)
    # Keep the existing external stair in place.
    for i in range(24):
        box('facadeMetal', 36, -67.8+i*.29, 3, .29, 1.2, .19*(i+1))
        if i % 3 == 0:
            for x in (36, 39):
                g['cylinder']('facadeSilver', x, -67.65+i*.29, 1.2+.19*(i+1), 2.25+.19*(i+1), .035)
    # Cross-road frontage, 120 m along the road from the reference camera.
    box('facadeDistantWall', 94, -100, 15, 40, 1.165, 12)
    box('facadeDistantBand', 93.96, -100, 15.08, 40, 10.665, 2.5)
    distant_sign = text('DECATHLON', 1.7, (93.9, -70, 11.1), 'facadeMarking')
    distant_sign.rotation_euler.z = -math.pi/2


@persistent
def _exterior_exposure(scene, *args):
    if '_facade_saved_exposure' in scene:
        scene.view_settings.exposure = scene['_facade_saved_exposure']
        del scene['_facade_saved_exposure']
    if scene.camera and scene.camera.matrix_world.translation.y < -60.55:
        scene['_facade_saved_exposure'] = scene.view_settings.exposure
        scene.view_settings.exposure += .7


@persistent
def _restore_exposure(scene, *args):
    if '_facade_saved_exposure' in scene:
        scene.view_settings.exposure = scene['_facade_saved_exposure']
        del scene['_facade_saved_exposure']


def daylight(g):
    scene = g['scene']
    world = scene.world
    world.use_nodes = True
    nt = world.node_tree
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(g['ROOT'] / 'data/textures/hdri/kloofendal_48d_partly_cloudy_puresky_2k.exr'), check_existing=True)
    coords = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    # Shared azimuth provides a reproducible daylight orientation for render review.
    azimuth, elevation = math.radians(215), math.radians(50)
    mapping.inputs['Rotation'].default_value[2] = azimuth
    nt.links.new(coords.outputs['Generated'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], nt.nodes['Background'].inputs['Color'])
    nt.nodes['Background'].inputs['Strength'].default_value = .8
    lamp = bpy.data.lights.new('facade-midday-sun', 'SUN')
    lamp.energy, lamp.angle = 2., math.radians(1.5)
    ob = bpy.data.objects.new(lamp.name, lamp)
    scene.collection.objects.link(ob)
    toward_sun = Vector((math.cos(elevation)*math.cos(azimuth), math.cos(elevation)*math.sin(azimuth), math.sin(elevation)))
    ob.rotation_euler = (-toward_sun).to_track_quat('-Z', 'Y').to_euler()
    for handlers, callback in ((bpy.app.handlers.render_pre, _exterior_exposure),
                               (bpy.app.handlers.render_post, _restore_exposure),
                               (bpy.app.handlers.render_cancel, _restore_exposure)):
        for old in list(handlers):
            if old.__module__ == __name__ and old.__name__ == callback.__name__:
                handlers.remove(old)
        handlers.append(callback)


def reference_settings(g, name):
    if name == 'facade':
        g['scene'].render.use_compositing = False
