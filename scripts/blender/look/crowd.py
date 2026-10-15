"""Instanced Rocketbox crowd. Deterministic placement; all motion repeats in 600 frames."""
import math
import random
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PERIOD = 600
TAU = 2 * math.pi
LANES = (
    ((-6, -64.4), (-6, -34), (0, -25), (0, 5), (5.9, 11), (5.9, 14.1)),
    ((5.9, 14.1), (8.8, 12.5), (11.4, 12.5), (11.4, -1.5)),
    ((5.9, 14.1), (-3.4, 12.5), (-6, 12.5), (-6, -1.5)),
    ((9.1, 13.85), (8.7, 12.85)),
    ((5.9, 11.08), (8.5, 12.65), (9.1, 13.85)),   # the phone intro's last stretch
)


def distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def inbox(p, b, pad=0):
    return b['x']-pad <= p[0] <= b['x']+b['w']+pad and b['y']-pad <= p[1] <= b['y']+b['h']+pad


def pose_matrix(pb):
    rest = pb.bone.matrix_local
    return (pose_matrix(pb.parent) @ pb.parent.bone.matrix_local.inverted() @ rest @ pb.matrix_basis
            if pb.parent else rest @ pb.matrix_basis)


def curves(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return []
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    result = []
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(obj.animation_data.action_slot)
            if bag:
                result.extend(bag.fcurves)
    return result


def build(g):
    started = time.perf_counter()
    rng = random.Random(20261014)
    venue = g['venue']
    sources = bpy.data.collections.new('Crowd sources (hidden)')
    crowd = bpy.data.collections.new('Crowd')
    bpy.context.scene.collection.children.link(sources)
    bpy.context.scene.collection.children.link(crowd)
    sources.hide_render = True
    sources.hide_viewport = True
    root = Path(g['ROOT']) / 'data/models/rocketbox'
    templates = []
    processed = set()

    def texture(path, image=None):
        image = image or bpy.data.images.load(str(path), check_existing=True)
        image.filepath = str(path)
        image.reload()
        if max(image.size) > 1024:
            ratio = 1024/max(image.size)
            image.scale(max(1, round(image.size[0]*ratio)), max(1, round(image.size[1]*ratio)))
        image.pack()
        return image

    # Each FBX is imported once. Materials and mesh datablocks remain shared.
    for path in sorted(root.glob('*/*.fbx')):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
        imported = list(set(bpy.data.objects)-before)
        rig = next(o for o in imported if o.type == 'ARMATURE')
        meshes = [o for o in imported if o.type == 'MESH']
        pngs = {p.stem.lower(): p for p in (path.parent/'Textures').glob('*.png')}
        for ob in imported:
            ob.animation_data_clear()
            for collection in list(ob.users_collection):
                collection.objects.unlink(ob)
            sources.objects.link(ob)
            if ob.type == 'MESH':
                for mod in list(ob.modifiers):
                    if mod.type == 'SUBSURF':
                        ob.modifiers.remove(mod)
                for slot in ob.material_slots:
                    mat = slot.material
                    if not mat or mat in processed or not mat.use_nodes:
                        continue
                    processed.add(mat)
                    nodes, links = mat.node_tree.nodes, mat.node_tree.links
                    shader = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
                    for node in list(nodes):
                        if node.type != 'TEX_IMAGE' or not node.image:
                            continue
                        stem = Path(node.image.filepath.replace('\\', '/')).stem.lower()
                        if stem in pngs:
                            node.image = texture(pngs[stem], node.image)
                            node.image.colorspace_settings.name = ('Non-Color' if 'normal' in stem or 'opacity' in stem else 'sRGB')
                        else:
                            for output in node.outputs:
                                for link in list(output.links):
                                    links.remove(link)
                            node.image = None
                            continue
                        if shader and 'body_color' in stem:
                            info = nodes.new('ShaderNodeObjectInfo')
                            hue = nodes.new('ShaderNodeHueSaturation')
                            remap = nodes.new('ShaderNodeMapRange')
                            remap.inputs['To Min'].default_value = .47
                            remap.inputs['To Max'].default_value = .53
                            links.new(info.outputs['Random'], remap.inputs['Value'])
                            links.new(remap.outputs['Result'], hue.inputs['Hue'])
                            links.new(node.outputs['Color'], hue.inputs['Color'])
                            crew = nodes.new('ShaderNodeMath')
                            crew.operation = 'LESS_THAN'
                            crew.inputs[1].default_value = .10
                            links.new(info.outputs['Random'], crew.inputs[0])
                            mix = nodes.new('ShaderNodeMixRGB')
                            mix.blend_type = 'COLOR'
                            mix.inputs[2].default_value = (1, .20, .025, 1)
                            links.new(crew.outputs[0], mix.inputs[0])
                            links.new(hue.outputs[0], mix.inputs[1])
                            links.new(mix.outputs[0], shader.inputs['Base Color'])
                        if shader and 'opacity_color' in stem:
                            alpha_path = next((p for k, p in pngs.items() if 'opacity_color' in k), None)
                            if alpha_path:
                                alpha = nodes.new('ShaderNodeTexImage')
                                alpha.image = texture(alpha_path)
                                alpha.image.colorspace_settings.name = 'Non-Color'
                                links.new(alpha.outputs['Color'], shader.inputs['Alpha'])
                                if hasattr(mat, 'surface_render_method'):
                                    mat.surface_render_method = 'DITHERED'
                                elif hasattr(mat, 'blend_method'):
                                    mat.blend_method = 'BLEND'
        templates.append((rig, meshes))

    if not templates:
        raise FileNotFoundError(f'No Rocketbox FBX files in {root}')

    stairs = [e['bounds'] for e in venue['links'] if 'rake' not in e.get('id', '')]
    blocks = {0: [], 1: []}
    for e in venue['obstacles'] + venue['decor']:
        if e.get('hidden') or 'bounds' not in e or e.get('linkId'):
            continue
        if e.get('material') in ('floorBelow', 'carpet', 'floor', 'ceiling'):
            continue
        if 'booths' in g and not e.get('floor', 0) and e.get('material') in ('booth', 'desk'):
            continue  # the dressed booths moved; their footprints follow below
        if e.get('height', 0) > .15 or e.get('material') == 'booth':
            if e.get('base', 0) < 1.9:
                blocks.setdefault(e.get('floor', 0), []).append(e['bounds'])
    blocks[0] += g.get('booths', [])
    blocks[1] += g.get('foyer_blocks', [])
    upstairs = [r for r in venue['rooms'] if r['floor'] == 1 and r['kind'] in ('foyer', 'corridor', 'landing')]
    occupied, loops = [], []
    stills = [dict(x=3.5, y=13, w=4.8, h=5.3), dict(x=8.3, y=13.3, w=2.7, h=3.2)]

    def valid(p, floor, bounds, extra=0):
        radius = .55 + extra
        if not inbox(p, bounds, -radius):
            return False
        if any(distance(p, a, b) <= .8+radius for line in LANES for a, b in zip(line, line[1:])):
            return False
        if any(inbox(p, b, radius) for b in stairs + blocks[floor] + stills):
            return False
        if floor == 1:
            if any(abs(p[0]-lane) <= 1.2+radius for lane in (-2, 7)):
                return False
            room = next((r for r in upstairs if inbox(p, r['bounds'], -radius)), None)
            if room is None or any(inbox(p, b, radius) for r in upstairs for b in r.get('voids', [])):
                return False
            for r in upstairs:
                b = r['bounds']
                if r['kind'] == 'corridor' and distance(p, (b['x']+b['w']/2, b['y']), (b['x']+b['w']/2, b['y']+b['h'])) <= .8+radius:
                    return False
            for d in g['doors'].values():
                for x, y in ((d['totem']['x'], d['totem']['y']), (d['wall_x'], d['yc'])):
                    approach = dict(x=min(x, x+d['face']*3), y=y-1.25, w=3, h=2.5)
                    if inbox(p, approach, radius):
                        return False
        return True

    hall = g['hall']
    # Circular ellipses are polygonised at <10 cm; extra clearance bounds
    # every intervening chord using the distance function's Lipschitz bound.
    for attempt in range(1800):
        if len(loops) == 5:
            break
        cx, cy = rng.uniform(-19, 24), rng.uniform(-31, 12)
        radius = rng.uniform(3.0, 4.3)
        count = math.ceil(TAU*radius/.09)
        loop = [(cx+radius*math.cos(TAU*k/count), cy+radius*math.sin(TAU*k/count)) for k in range(count)]
        if all(valid(p, 0, hall, .10) for p in loop) and all(math.hypot(cx-x, cy-y) > radius+r+1.3 for x, y, r, _ in loops):
            loops.append((cx, cy, radius, loop))

    white = g['material']('crowdBadge', 0xF7F6F1, rough=.7)
    black = g['material']('crowdStrap', 0x171B23, rough=.85)
    packmat = g['material']('crowdBackpack', 0x29313C, rough=.9)
    accessory_meshes = {}

    def accessory(rig, canonical, bone, name, pos, size, mat, cylinder=False, tilt=0):
        if bone is None:
            return
        key = (name, cylinder)
        if key not in accessory_meshes:
            if cylinder:
                bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.5, depth=1)
            else:
                bpy.ops.mesh.primitive_cube_add(size=1)
            src = bpy.context.object
            mesh = src.data
            mesh.materials.append(mat)
            bpy.data.objects.remove(src, do_unlink=True)
            accessory_meshes[key] = mesh
        ob = bpy.data.objects.new(name, accessory_meshes[key])
        crowd.objects.link(ob)
        ob.parent, ob.parent_type, ob.parent_bone = rig, 'BONE', bone.name
        parent = pose_matrix(bone) @ Matrix.Translation((0, bone.length, 0))
        ob.matrix_basis = parent.inverted() @ canonical.inverted() @ Matrix.Translation(pos) @ Matrix.Rotation(tilt, 4, 'Y') @ Matrix.Diagonal((*size, 1))
        if name == 'backpack':
            bevel = ob.modifiers.new('Rounded pack', 'BEVEL')
            bevel.width, bevel.segments = .10, 2

    total = walkers = failures = 0

    def person(x, y, z, yaw, walking=None):
        nonlocal total, walkers, failures
        src, meshes = templates[total % len(templates)]
        rig = src.copy()
        rig.animation_data_clear()
        crowd.objects.link(rig)
        rig.name = f'crowd-{total:03d}'
        anchor = bpy.data.objects.new(f'crowd-position-{total:03d}', None)
        crowd.objects.link(anchor)
        anchor.location = (x, y, z)
        anchor.rotation_euler.z = yaw
        scale = rng.uniform(.96, 1.04)
        anchor.scale = (scale,)*3
        rig.parent = anchor
        rig.matrix_parent_inverse = Matrix.Identity(4)
        # The floor anchor retains the imported pelvis-origin offset (0.895 m).
        # Discarding that offset would put the pelvis at floor level.
        canonical = src.matrix_world.copy()
        rig.matrix_basis = canonical
        for mesh in meshes:
            ob = mesh.copy()
            ob.animation_data_clear()
            crowd.objects.link(ob)
            ob.parent = rig
            ob.parent_type = mesh.parent_type
            ob.parent_bone = mesh.parent_bone
            ob.matrix_parent_inverse = mesh.matrix_parent_inverse.copy()
            ob.matrix_basis = mesh.matrix_basis.copy()
            for mod in ob.modifiers:
                if mod.type == 'ARMATURE':
                    mod.object = rig
        for pb in rig.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
            pb.rotation_mode = 'QUATERNION'
        bpy.context.view_layer.update()
        def bone(suffix):
            return next((b for b in rig.pose.bones if b.name.endswith(suffix)), None)
        def swing_bone(suffix, angle, axis):
            pb = bone(suffix)
            if pb is None:
                return
            h = pb.head.copy()
            pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-h) @ pb.matrix
            bpy.context.view_layer.update()

        def reset_pose():
            for pb in rig.pose.bones:
                pb.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()

        def healthy():
            bpy.context.view_layer.update()
            head, pelvis = bone('Head'), bone('Pelvis')
            return (head is not None and pelvis is not None
                    and 1.25 <= (rig.matrix_world @ head.head).z-z <= 1.95
                    and .7 <= (rig.matrix_world @ pelvis.head).z-z <= 1.1)

        def arms_down():
            valid = True
            for side in ('L', 'R'):
                upper, elbow = bone(side+' UpperArm'), bone(side+' Forearm')
                if upper is None or elbow is None:
                    valid = False
                    continue
                original = upper.matrix_basis.copy()
                lowered = False
                for sign in (1, -1):
                    upper.matrix_basis = original.copy()
                    bpy.context.view_layer.update()
                    swing_bone(side+' UpperArm', sign*math.radians(40), 'X')
                    shoulder_pos, elbow_pos = canonical @ upper.head, canonical @ elbow.head
                    if shoulder_pos.z-elbow_pos.z > .85*(elbow_pos-shoulder_pos).length and abs(elbow_pos.x) < abs(shoulder_pos.x)+.1:
                        lowered = True
                        break
                if not lowered:
                    upper.matrix_basis = original
                    bpy.context.view_layer.update()
                    valid = False
            return valid

        def simple_pose():
            reset_pose()
            ok = arms_down()
            for side in ('L', 'R'):
                swing_bone(side+' Forearm', -math.radians(10), 'Y')
            ok = ok and healthy()
            if not ok:
                reset_pose()
            return ok

        pose_ok = arms_down()
        variant = total % 5
        for side in ('L', 'R'):
            bend = 55 if variant in (0, 1) and side == 'R' and walking is None else 10
            swing_bone(side+' Forearm', -math.radians(bend), 'Y')
        for suffix, amount in (('Spine', .04), ('Neck', .12), ('Head', .22)):
            swing_bone(suffix, rng.uniform(-amount, amount), 'Z')
        simplified = not pose_ok or not healthy()
        fell_back = simplified and not simple_pose()
        base_pose = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
        spine = bone('Spine2') or bone('Spine1') or bone('Spine')
        if rng.random() < .70:
            accessory(rig, canonical, spine, 'badge', (0, .20, 1.25), (.09, .012, .12), white)
            for sign in (-1, 1):
                accessory(rig, canonical, spine, 'lanyard', (sign*.065, .17, 1.43), (.012, .009, .30), black, tilt=sign*.30)
        if rng.random() < .35:
            accessory(rig, canonical, spine, 'backpack', (0, -.20, 1.26), (.30, .15, .42), packmat)
        if variant in (0, 1) and walking is None and not simplified:
            hand = bone('R Hand')
            if hand:
                hp = canonical @ pose_matrix(hand) @ Vector((0, hand.length*.5, 0))
                accessory(rig, canonical, hand, 'cup' if variant == 1 else 'phone', hp,
                          (.075, .075, .10) if variant == 1 else (.065, .012, .13),
                          white if variant == 1 else black, cylinder=variant == 1)
        if walking is not None:
            walkers += 1
            loop, phase = walking
            count = len(loop)
            previous = None
            for k in range(count+1):
                a = loop[(k+phase) % count]
                b = loop[(k+phase+1) % count]
                angle = math.atan2(b[0]-a[0], -(b[1]-a[1]))
                if previous is not None:
                    angle = previous + (angle-previous+math.pi) % TAU-math.pi
                previous = angle
                anchor.location = (*a, z)
                anchor.rotation_euler.z = angle
                anchor.keyframe_insert('location', frame=1+PERIOD*k/count)
                anchor.keyframe_insert('rotation_euler', frame=1+PERIOD*k/count)
            # Twenty strides per lap; two extreme poses and a closing key.
            for frame, swing in ((1, 1), (16, -1), (31, 1)):
                for pb in rig.pose.bones:
                    pb.matrix_basis = base_pose[pb.name].copy()
                bpy.context.view_layer.update()
                for side, sign in (('L', 1), ('R', -1)):
                    if not fell_back:
                        a = swing*sign
                        swing_bone(side+' Thigh', math.radians(22)*a, 'Y')
                        swing_bone(side+' Calf', math.radians(25)*max(0, a), 'Y')
                        swing_bone(side+' UpperArm', -math.radians(15)*a, 'Y')
                if not healthy():
                    rig.animation_data_clear()
                    fell_back = not simple_pose()
                    break
                for side in ('L', 'R'):
                    for suffix in ('Thigh', 'Calf', 'UpperArm', 'Forearm'):
                        pb = bone(side+' '+suffix)
                        if pb:
                            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if fell_back:
                rig.animation_data_clear()
                reset_pose()
            for ob in (anchor, rig):
                for fc in curves(ob):
                    for key in fc.keyframe_points:
                        key.interpolation = 'LINEAR'
                    cycle = fc.modifiers.new('CYCLES')
                    if ob == anchor and fc.data_path == 'rotation_euler' and fc.array_index == 2:
                        cycle.mode_before = cycle.mode_after = 'REPEAT_OFFSET'
        failures += int(fell_back)
        total += 1
        occupied.append((x, y, z))

    for _, _, _, loop in loops:
        for phase in range(4):
            person(*loop[phase*len(loop)//4], 0, 0, (loop, phase*len(loop)//4))

    def free(p, z):
        return all(abs(z-zz) > 2 or math.hypot(p[0]-x, p[1]-y) >= .82 for x, y, zz in occupied) and (z > 2 or all(abs(math.hypot(p[0]-x, p[1]-y)-r) > 1.25 for x, y, r, _ in loops))

    # First place booth visitors just outside the original plate bounds.
    hall_start = total
    for b in g.get('booths') or [e['bounds'] for e in venue['decor']
                                 if not e.get('floor', 0) and e.get('material') == 'booth' and e.get('height') == .05]:
        for sign in (-1, 1):
            p = (b['x']+b['w']/2+sign*(b['w']/2+.85), b['y']+b['h']/2)
            if valid(p, 0, hall) and free(p, 0):
                person(*p, 0, sign*math.pi/2)
                break

    def fill(bounds, z, target, floor, groups=True, anchors=None):
        initial = total
        for _ in range(3500):
            if total-initial >= target:
                break
            cx = rng.uniform(bounds['x'], bounds['x']+bounds['w'])
            cy = rng.uniform(bounds['y'], bounds['y']+bounds['h'])
            if anchors and rng.random() < .85:
                ax, ay = rng.choice(anchors)
                cx, cy = ax+rng.uniform(-.3, .3), ay+rng.uniform(-1.8, 1.8)
            n = min(rng.randint(2, 3 if floor == 1 else 5) if groups else 1, target-(total-initial))
            radius = .95/(2*math.sin(math.pi/n)) if n > 1 else 0
            phase = rng.uniform(0, TAU)
            candidates = [(cx+radius*math.cos(phase+TAU*k/n), cy+radius*math.sin(phase+TAU*k/n)) for k in range(n)]
            if all(valid(p, floor, bounds) and free(p, z) for p in candidates):
                for p in candidates:
                    person(*p, z, math.atan2(cx-p[0], p[1]-cy) if n > 1 else rng.uniform(-math.pi, math.pi))
    fill(dict(x=1.3, y=-26.4, w=9.2, h=20.4), 0, min(80, max(0, 190-total)), 0)
    fill(hall, 0, max(0, 190-total), 0)
    reception_start = total
    for x in (-11, -9):
        for k in range(20):
            p = (x+rng.uniform(-.12, .12), -58.0+k*.86)
            bounds = dict(x=-13.6, y=-60.4, w=36.3, h=23)
            if valid(p, 0, bounds) and free(p, 1.2):
                person(*p, 1.2, 0 if x == -11 else math.pi)
    for y in (-47, -46.1, -44.6, -43.7, -42.2):
        p = (-2.2, y)
        if valid(p, 0, bounds) and free(p, 1.2):
            person(*p, 1.2, math.pi/2)
    fill(dict(x=-13.6, y=-60.4, w=5.6, h=23), 1.2, max(0, 40-(total-reception_start)), 0, False)
    fill(dict(x=-13.6, y=-64, w=36.3, h=3), 1.24, 8, 0, False)
    upper_start = total
    near = dict(g['corridor'], y=-50, h=45)
    anchors = [(x, y) for x, y in g.get('foyer_social', []) if -49 < y < -6]
    fill(near, g['FH'], 35, 1, anchors=anchors)
    near_count = total-upper_start
    # Fill the remaining ten outside the walking-camera stretch.
    for room in reversed(upstairs):
        b = room['bounds']
        for lo, hi in ((b['y'], min(-50, b['y']+b['h'])),
                       (max(-5, b['y']), b['y']+b['h'])):
            if hi-lo > 1.1:
                fill(dict(b, y=lo, h=hi-lo), g['FH'], max(0, 45-(total-upper_start)), 1)
    print(f'CHECK upstairs: {near_count}/35 near camera, {total-upper_start}/45 total')
    bpy.context.scene.frame_set(1)
    # Freeze everyone who stands still into a plain mesh: a render evaluates the scene several times per frame
    # for motion blur, and 270 deforming rigs cost far more than their triangles.
    graph = bpy.context.evaluated_depsgraph_get()
    frozen = 0
    for rig in [o for o in crowd.objects if o.type == 'ARMATURE']:
        if rig.animation_data and rig.animation_data.action:
            continue
        for ob in rig.children:
            mods = [m for m in ob.modifiers if m.type == 'ARMATURE']
            if ob.type != 'MESH' or not mods:
                continue
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
            for m in mods:
                ob.modifiers.remove(m)
            ob.data = me
        frozen += 1
    print(f'CHECK crowd: {total} people, {walkers} walkers, {failures} poses fell back to rest, {frozen} frozen')
