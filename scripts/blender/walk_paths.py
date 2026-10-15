"""Shared gimbal path builder, route registry and scene integration (Blender Python).

Spatial curves are sampled by arc length; a curvature/stair limited speed envelope
is integrated in time. Rotations use unwrapped angles and compatible XYZ Eulers.
Every segment has its own camera. Boundary samples encode a moving straight joint.
"""
from dataclasses import dataclass
import json
import math
import numpy as np
import bpy
from mathutils import Vector

FPS = 30
SETTLE = 24
JOINT_SPEED = 2.0
HALL_FRAME = 1000
# The crowd's motion repeats every CROWD_PERIOD frames, so any clip that settles on the hall still ends on
# HALL_FRAME + k * CROWD_PERIOD and the still (rendered at HALL_FRAME) matches its last frame exactly.
CROWD_PERIOD = 600
# Pace: a quick gimbal glide. Cruise, sideways and along-the-path accelerations, and the turn rate the
# heading may reach (rad/s; the view's yaw limiter in build_path is a little tighter). Turns stay within what a person's
# head does walking round a corner: up to 135 deg/s (4.5 deg/frame), eased in and out (0.6 deg/frame²).
YAW_RATE, YAW_ACCEL = 4.45, .59
CRUISE, LATERAL, ALONG, TURN = 6.5, 4.4, 3.5, 2.2
SPEED_SMOOTH = 41       # frames: the speed profile is low-passed, so no lurch where it starts or stops braking


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t*t*t*(10 + t*(-15 + 6*t))


def camera_pose(camera):
    bpy.context.view_layer.update()
    q = camera.matrix_world.to_quaternion()
    d = q @ Vector((0, 0, -1))
    return dict(location=np.array(camera.matrix_world.translation),
                yaw=math.atan2(d.y, d.x), pitch=math.atan2(d.z, math.hypot(d.x, d.y)),
                lens=camera.data.lens, shift_x=camera.data.shift_x, shift_y=camera.data.shift_y)


def rounded_path(points):
    """Cubic corner fillets stay in the waypoint convex hull (no Catmull overshoot)."""
    p = np.asarray(points, dtype=float)
    p = p[np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-6]]
    dense = [p[0]]

    def line(a, b):
        count = max(2, math.ceil(np.linalg.norm(b-a)/.025))
        dense.extend(a+(b-a)*t for t in np.linspace(0, 1, count)[1:])

    for i in range(1, len(p)-1):
        a, v, b = p[i-1:i+2]
        cut = min(np.linalg.norm(v-a)*.42, np.linalg.norm(b-v)*.42, 2.5)
        u, w = (v-a)/np.linalg.norm(v-a), (b-v)/np.linalg.norm(b-v)
        enter, leave = v-u*cut, v+w*cut
        line(dense[-1], enter)
        # Cubic with tangent-aligned handles; zero-length/straight corners remain harmless.
        c1, c2 = enter+u*cut*.65, leave-w*cut*.65
        count = max(8, math.ceil(2*cut/.025))
        for t in np.linspace(0, 1, count)[1:]:
            dense.append((1-t)**3*enter+3*(1-t)**2*t*c1+3*(1-t)*t*t*c2+t**3*leave)
    line(dense[-1], p[-1])
    dense = np.array(dense)
    distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    keep = np.r_[True, np.diff(distances)>1e-8]
    distances, dense = distances[keep], dense[keep]
    arc = np.linspace(0, distances[-1], max(2, math.ceil(distances[-1]/.025)+1))
    return arc, np.array([np.interp(arc, distances, dense[:, k]) for k in range(3)]).T


def fitted_height(link, x, y, fh=6.2):
    """Least-squares line through tread centres/nosings, C1 clamped at flight ends.

    The half-riser offset is the mean of the real tread heights, keeping clearance
    1.56..1.74 m for 18 cm risers instead of jumping at each tread.
    """
    b = link['bounds']
    coordinate, start, length = (x, b['x'], b['w']) if link['axis']=='x' else (y, b['y'], b['h'])
    u = (coordinate-start)/length
    if not link['ascending']:
        u = 1-u
    rise = round(link['rise']/link['riser'])*link['riser']
    # Smooth slope changes over a half tread, outside the flight as well as inside it.
    width = link['riser']/rise/2
    def soft_positive(t):
        if t < -width: return 0.
        if t > width: return t
        return (t+width)**2/(4*width)
    fraction = soft_positive(u)-soft_positive(u-1)
    offset_weight = float(smooth((u*length+.4)/.4))*float(smooth(((1-u)*length+.4)/.4))
    top_correction = (fh-rise)*float(smooth((u-1)*length/.8+.5)) if link['id'].startswith('stair-') else 0.
    return link['from']*fh+link['base']+rise*fraction+link['riser']/2*offset_weight+top_correction


PIVOT_LEFT = math.radians(45)   # a pivot turns on the spot until the view is this close to the way to go


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def pivot(pose, to_yaw):
    """Turn on the spot from pose's yaw to to_yaw, eased (quintic) within the yaw rate and acceleration limits."""
    delta = wrap(to_yaw-pose['yaw'])
    rate, accel = math.radians(YAW_RATE)*.95, math.radians(YAW_ACCEL)*.9
    n = max(2, math.ceil(max(1.875*abs(delta)/rate, math.sqrt(5.78*abs(delta)/accel))))
    return [dict(pose, yaw=pose['yaw']+delta*float(smooth(i/n))) for i in range(n+1)]


def build_path(points, start, end, **kw):
    """Waypoints -> poses. A clip that starts on a still facing well away from the way it goes first turns on the
    spot (as a person does), then walks off finishing the turn; one that ends on a still facing away from the way it
    arrives finishes with the same turn. Moving joints are left alone."""
    pts = [np.asarray(q, dtype=float) for q in points]
    head = lambda a, b: math.atan2(b[1]-a[1], b[0]-a[0])
    before = after = []
    if not kw.get('moving_start'):
        go = head(pts[0], next(q for q in pts[1:] if np.linalg.norm(q[:2]-pts[0][:2]) > .3))
        off = wrap(go-start['yaw'])
        if abs(off) > math.radians(60):
            before = pivot(start, start['yaw']+off-math.copysign(PIVOT_LEFT, off))
            start = dict(before[-1])
    if not kw.get('moving_end'):
        come = head(next(q for q in pts[-2::-1] if np.linalg.norm(q[:2]-pts[-1][:2]) > .3), pts[-1])
        off = wrap(end['yaw']-come)
        if abs(off) > math.radians(60):
            arrive = dict(end, yaw=end['yaw']-off+math.copysign(PIVOT_LEFT, off))
            after = pivot(arrive, end['yaw'])
            end = arrive
    poses = _walk(points, start, end, **kw)
    if before:
        poses = before[:-1]+poses
    if after:
        poses = poses+after[1:]
    return poses


def _walk(points, start, end, *, floor=None, stairs=(), moving_start=False,
          moving_end=False, target_seconds=None, floor_smooth=2.5):
    """Waypoints -> poses. Endpoint optics are interpolated, never reset at a split.

    Safety limits take precedence over target duration; audits report any overrun.
    A moving boundary has constant 2 m/s for four samples on a straight stretch.
    """
    arc, xyz = rounded_path(points)
    if floor:
        xyz[:, 2] = [floor(*p) + 1.65 for p in xyz]
        if floor_smooth:   # a measured floor: steps and kerbs become a gentle ramp
            n = max(3, int(floor_smooth/.025)) | 1
            kernel = np.hanning(n+2)[1:-1]; kernel /= kernel.sum()
            xyz[:, 2] = np.convolve(np.pad(xyz[:, 2], (n//2, n//2), mode='edge'), kernel, mode='valid')
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
    tangent = np.gradient(xyz, axis=0)
    tangent /= np.maximum(1e-9, np.linalg.norm(tangent, axis=1))[:, None]
    # bends on the floor plan slow the walk; the change of slope at a stair's ends doesn't
    flat = np.gradient(xyz[:, :2], axis=0)
    flat /= np.maximum(1e-9, np.linalg.norm(flat, axis=1))[:, None]
    curvature = np.linalg.norm(np.gradient(flat, axis=0), axis=1) / np.maximum(1e-6, np.gradient(arc))
    cap = np.minimum(CRUISE, np.sqrt(LATERAL/np.maximum(curvature, .001)))
    cap = np.minimum(cap, TURN/np.maximum(curvature, .001))
    for b in stairs:
        on = ((xyz[:, 0] > b['x']-.2) & (xyz[:, 0] < b['x']+b['w']+.2) &
              (xyz[:, 1] > b['y']-.4) & (xyz[:, 1] < b['y']+b['h']+.4))
        cap[on] = np.minimum(cap[on], 2.65)
    # Ease in/out spatially; allow time for the view to depart from the still.
    if moving_start:
        cap[arc < .8] = np.minimum(cap[arc < .8], JOINT_SPEED)
    else:
        cap = np.minimum(cap, np.sqrt(2*2.2*np.maximum(arc, 0)))
    if moving_end:
        cap[arc[-1]-arc < .8] = np.minimum(cap[arc[-1]-arc < .8], JOINT_SPEED)
    else:
        cap = np.minimum(cap, np.sqrt(2*2.2*np.maximum(arc[-1]-arc, 0)))
    # Forward/backward acceleration bounds anticipate sharp turns and stair approaches.
    for _ in range(2):
        for i in range(1, len(cap)):
            cap[i] = min(cap[i], math.sqrt(cap[i-1]**2+2*ALONG*(arc[i]-arc[i-1])))
        for i in range(len(cap)-2, -1, -1):
            cap[i] = min(cap[i], math.sqrt(cap[i+1]**2+2*ALONG*(arc[i+1]-arc[i])))
    time = np.r_[0., np.cumsum(2*np.diff(arc)/np.maximum(.01, cap[:-1]+cap[1:]))]
    duration = max(time[-1], target_seconds or 0)
    frames = math.ceil(duration*FPS)
    times = np.linspace(0, time[-1], frames+1)
    # Integrate the piecewise-linear velocity envelope exactly: linear interpolation
    # of distance created artificial speed jumps at low-speed sampling boundaries.
    indices=np.clip(np.searchsorted(time,times,side='right')-1,0,len(time)-2)
    dt=times-time[indices]; spans=time[indices+1]-time[indices]
    distance=arc[indices]+cap[indices]*dt+.5*(cap[indices+1]-cap[indices])/spans*dt*dt
    distance[-1]=arc[-1]
    # Low-pass the speed (bang-bang braking reads as a lurch), keeping the total length and the ends: a moving
    # end keeps its joint speed, a resting end its zero.
    speed = np.diff(distance)
    if len(speed) > SPEED_SMOOTH:
        kernel = np.hanning(SPEED_SMOOTH+2)[1:-1]; kernel /= kernel.sum()
        h = SPEED_SMOOTH//2
        soft = np.convolve(np.pad(speed, (h, h), mode='edge'), kernel, mode='valid')
        edge = np.minimum(1., np.minimum(np.arange(len(speed)), np.arange(len(speed))[::-1])/h)
        soft = speed*(1-edge)+soft*edge
        soft *= arc[-1]/soft.sum()
        distance = np.r_[0., np.cumsum(soft)]
        distance[-1] = arc[-1]
    positions = np.array([np.interp(distance, arc, xyz[:, k]) for k in range(3)]).T
    # Preserve exact boundary velocity despite rounding duration to whole frames.
    for edge, moving, sign in [(0, moving_start, 1), (-1, moving_end, -1)]:
        if not moving: continue
        direction = tangent[edge] * sign
        endpoint = positions[edge].copy()
        for i in range(min(18, len(positions)//3)):
            idx = i if edge == 0 else len(positions)-1-i
            straight = endpoint+direction*JOINT_SPEED*i/FPS
            blend = float(smooth((i-3)/14))
            positions[idx] = straight*(1-blend)+positions[idx]*blend
    # Vertical-only settle blending does not change the horizontal route.
    if not moving_start:
        weight = 1-smooth(np.arange(len(positions))/SETTLE)
        positions[:, 2] += (start['location'][2]-positions[0, 2])*weight
    if not moving_end:
        weight = 1-smooth(np.arange(len(positions))[::-1]/SETTLE)
        positions[:, 2] += (end['location'][2]-positions[-1, 2])*weight
    positions[0], positions[-1] = start['location'], end['location']
    delta = np.gradient(positions, axis=0)
    yaw = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    # Keep a level view through flights; stairs are read from translation, never an upward look target.
    pitch = np.zeros(len(yaw))
    for edge, endpoint, moving in [(0, start, moving_start), (-1, end, moving_end)]:
        angle = yaw[edge] + math.atan2(math.sin(endpoint['yaw']-yaw[edge]), math.cos(endpoint['yaw']-yaw[edge]))
        if not moving:
            indices = np.arange(len(yaw)) if edge == 0 else np.arange(len(yaw))[::-1]
            weight = 1-smooth(indices/SETTLE)
            yaw += (angle-yaw[edge])*weight
            pitch += endpoint['pitch']*weight
    # Smooth angle values, never blend look vectors across a 180-degree turn.
    kernel = np.hanning(19); kernel /= kernel.sum()
    yaw = np.convolve(np.pad(yaw, (9, 9), mode='edge'), kernel, mode='valid')
    initial = yaw[0]+math.atan2(math.sin(start['yaw']-yaw[0]), math.cos(start['yaw']-yaw[0]))
    final = yaw[-1]+math.atan2(math.sin(end['yaw']-yaw[-1]), math.cos(end['yaw']-yaw[-1]))
    fixed = np.zeros(len(yaw),dtype=bool)
    fixed[:4 if moving_start else 2] = True
    fixed[-4 if moving_end else -2:] = True
    yaw[:4 if moving_start else 2] = initial
    yaw[-4 if moving_end else -2:] = final
    # Project onto rate/acceleration half-spaces with immovable endpoint conditions.
    # Alternating traversal avoids bias towards either end. Audit verifies convergence.
    rate, acceleration = math.radians(YAW_RATE),math.radians(YAW_ACCEL)
    for sweep in range(1800):
        worst = 0.
        order = range(len(yaw)-1) if sweep%2==0 else range(len(yaw)-2,-1,-1)
        for i in order:
            error = yaw[i+1]-yaw[i]
            excess = error-max(-rate,min(rate,error))
            free = int(not fixed[i])+int(not fixed[i+1])
            if free and abs(excess)>1e-9:
                if not fixed[i]: yaw[i] += excess/free
                if not fixed[i+1]: yaw[i+1] -= excess/free
                worst = max(worst,abs(excess))
        order = range(1,len(yaw)-1) if sweep%2==0 else range(len(yaw)-2,0,-1)
        for i in order:
            error = yaw[i-1]-2*yaw[i]+yaw[i+1]
            excess = error-max(-acceleration,min(acceleration,error))
            weights = [(j,c) for j,c in ((i-1,1),(i,-2),(i+1,1)) if not fixed[j]]
            norm = sum(c*c for _,c in weights)
            if norm and abs(excess)>1e-9:
                for j,c in weights: yaw[j] -= c*excess/norm
                worst = max(worst,abs(excess))
        if worst < 1e-7: break
    poses = []
    for i, position in enumerate(positions):
        u = 0. if moving_start and i < 4 else 1. if moving_end and i > frames-4 else float(smooth(i/frames))
        poses.append(dict(location=position, yaw=float(yaw[i]), pitch=float(pitch[i]),
                          **{k: start[k]*(1-u)+end[k]*u for k in ('lens','shift_x','shift_y')}))
    poses[0] = dict(start)
    poses[-1] = dict(end)
    # Store endpoint yaw on the continuous branch too (Euler conversion also uses compatibility).
    poses[0]['yaw'], poses[-1]['yaw'] = initial, final
    return poses


@dataclass
class Clip:
    name: str
    poses: list
    first: int
    phone: bool
    camera: object = None
    start_still: str = None
    end_still: str = None
    moving_start: bool = False
    moving_end: bool = False

    @property
    def last(self): return self.first+len(self.poses)-1


def key_camera(clip, template, scene):
    data = template.data.copy()
    data.animation_data_clear()
    data.dof.use_dof = False
    camera = bpy.data.objects.new('cam-'+clip.name, data)
    scene.collection.objects.link(camera)
    previous = None
    # Guard keys give both cameras identical subframe motion on either side of a
    # shared boundary, so motion blur matches too (constant extrapolation would not).
    before,after = dict(clip.poses[0]),dict(clip.poses[-1])
    if clip.moving_start:
        before['location'] = 2*clip.poses[0]['location']-clip.poses[1]['location']
    if clip.moving_end:
        after['location'] = 2*clip.poses[-1]['location']-clip.poses[-2]['location']
    samples = [before]+clip.poses+[after]
    for i, p in enumerate(samples, start=-1):
        yaw, pitch = p['yaw'], p['pitch']
        direction = Vector((math.cos(yaw)*math.cos(pitch), math.sin(yaw)*math.cos(pitch), math.sin(pitch)))
        q = direction.to_track_quat('-Z', 'Y')
        previous = q.to_euler('XYZ', previous) if previous is not None else q.to_euler('XYZ')
        camera.location, camera.rotation_euler = p['location'], previous
        for key in ('lens','shift_x','shift_y'):
            setattr(data, key, p[key]); data.keyframe_insert(key, frame=clip.first+i)
        camera.keyframe_insert('location', frame=clip.first+i)
        camera.keyframe_insert('rotation_euler', frame=clip.first+i)
    # Blender 4.4+/5.x layered actions and older legacy actions.
    for obj in (camera, data):
        action = obj.animation_data.action
        curves = []
        if hasattr(action, 'layers'):
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags: curves.extend(bag.fcurves)
        elif hasattr(action, 'fcurves'): curves.extend(action.fcurves)
        for curve in curves:
            for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    clip.camera = camera
    return camera


def path_sample_points(clips, spacing=.15):
    """Crowd hook: union of camera paths; keep avatar body bounds >=0.8 m away.

    Pass registries from all rooms to reserve their union, not just the active room.
    Includes intro, both aspects, both directions and seated/standing transitions.
    """
    result = []
    for clip in clips.values():
        for i, p in enumerate(clip.poses):
            point = np.asarray(p['location'])
            if i == 0 or np.linalg.norm(point-result[-1]) >= spacing:
                result.append(point)
    return [list(map(float, p)) for p in result]


def _room_routes(g):
    scene, room, fh = g['scene'], g['n'], g['FH']
    door, side = g['doors'][room], g['side']
    west, face = door['west'], door['face']
    link = next(l for l in g['venue']['links'] if l['id']=='stair-'+side)
    b = link['bounds']; sx = b['x']+b['w']/2
    joint = np.array([sx, b['y']-3., fh+1.65])
    lane = sx+face*4.
    clips, joins, outputs, stills = {}, [], {}, {}
    templates = {'hall': g['hall_cam'], 'hall-phone': g['phone_hall_cam'],
                 f'seat-{room}': g['seat_wide_cam'], f'door-phone-{room}': g['door_cam']}
    stills.update({name: dict(camera=ob, frame=HALL_FRAME) for name, ob in templates.items()})

    def level(x,y,z):
        if b['x']-.2 <= x <= b['x']+b['w']+.2 and b['y']-.4 <= y <= b['y']+b['h']+.4:
            return fitted_height(link,x,y)
        return 0. if z < fh/2 else fh

    rake = next(l for l in g['venue']['links'] if l['id']==f'rake-{room}')
    rb = rake['bounds']
    def room_floor(x,y,z):
        if rb['x']-.4 <= x <= rb['x']+rb['w']+.4 and rb['y'] <= y <= rb['y']+rb['h']:
            return fitted_height(rake,x,y)
        return fh

    def register(name, poses, first, phone, template, start=None, end=None, ms=False, me=False):
        clip = Clip(name, poses, first, phone, start_still=start, end_still=end,
                    moving_start=ms, moving_end=me)
        clips[name] = clip
        return clip

    for phone in (False, True):
        tag = '-phone' if phone else ''
        hall_name = 'hall'+tag
        end_name = f'door-phone-{room}' if phone else f'seat-{room}'
        hall_cam, end_cam = templates[hall_name], templates[end_name]
        hp, ep = camera_pose(hall_cam), camera_pose(end_cam)
        # A common lens at the joint makes the split independent of room destination.
        jp = dict(hp, location=joint, yaw=-math.pi/2, pitch=0., shift_x=0., shift_y=0.)
        back_jp = dict(jp, yaw=math.pi/2)
        h = hp['location']; e = ep['location']
        # The stairwell is glassed in, closed at its hall end; the way in is a 1.8 m gap in its side wall facing the
        # middle of the hall (y 11.6-13.4). From the hall still: turn towards the stair on the spot, across to the gap,
        # through it and round down the middle of the flight, and up.
        foot, gap = b['y']+b['h'], b['y']+b['h']+2.6
        toward = -1 if west else 1                     # the stair's side of the hall, along x
        outside = b['x']+b['w']+1.4 if west else b['x']-1.4   # in the hall, level with the gap
        if phone:      # the phone still stands right by the glass: step back clear of it first
            first = (h[0]-.4, h[1]-1., 1.65)
        else:
            first = (h[0]+.9*toward, h[1]-.9, 1.65)
        hall_out = [h, first, (outside,gap,1.65), (sx,gap,1.65)]
        common = hall_out+[(sx,foot,1.65), (sx,b['y'],fh+1.65), (sx,joint[1]+1.2,fh+1.65), joint]
        a = build_path(common,hp,jp,floor=level,stairs=[b],moving_end=True)
        ca = register(f'walk{tag}-a-{side}', a,HALL_FRAME,phone,hall_cam,hall_name,me=True)
        wx,yc = door['wall_x'],door['yc']-(.4 if room==3 else 0.)
        ay = g['aisle_y_for'](room)
        forward_sign = 1 if yc > joint[1]-3 else -1
        corridor = [joint, (sx,joint[1]-1.3,fh+1.65), (lane,joint[1]-3.5,fh+1.65),
                    (lane,yc-forward_sign*3,fh+1.65)]
        if phone:
            per = corridor+[(e[0]+face*1.5,e[1],fh+1.65), e]
        else:
            high = rb['x']+rb['w'] if west else rb['x']
            per = corridor+[(wx+face*2.4,yc,fh+1.65),(wx-face*1.8,yc,fh+1.65),
                            (high+face*.7,ay,fh+1.65),(e[0]-face*.4,ay,e[2]+.7),
                            (e[0]-face*.4,e[1],e[2]+.7), e]
        bp = build_path(per,jp,ep,floor=room_floor,moving_start=True)
        cb = register(f'walk{tag}-b-{room}',bp,ca.last,phone,hall_cam,end=end_name,ms=True)
        joins.append((ca.name,cb.name))
        stills[end_name]['frame'] = cb.last
        outputs[f'walk{tag}-{room}'] = [ca.name,cb.name]
        # Return follows the same ground with new travel-facing orientations. The small departure
        # arc moves initially towards the screen, then steps across the row into the aisle.
        reverse = [np.array(p,dtype=float) for p in per[::-1]]
        if phone:
            direction = 1 if joint[1] > e[1] else -1
            tail = reverse[2:]
            # a lane point already passed (the totem can stand beyond the door's centre) would double back
            if (tail[0][1]-(e[1]+direction*3))*direction < 1.:
                tail = tail[1:]
            reverse = [e,(e[0]-face*.35,e[1],e[2]),
                       (e[0]-face*.35,e[1]+direction*1.5,fh+1.65),
                       (lane,e[1]+direction*3,fh+1.65)]+tail
        # Ensure the arrival at the return joint is northbound and straight.
        reverse[-2] = joint+np.array([0.,-1.3,0.])
        rp = build_path(reverse,ep,back_jp,floor=room_floor,moving_end=True)
        cr = register(f'back{tag}-b-{room}',rp,cb.last,phone,end_cam,start=end_name,me=True)
        # back down the stair, out of the stairwell and up the hall to the still, arriving heading its way (north)
        common_return = [joint,(sx,joint[1]+1.2,fh+1.65),(sx,b['y'],fh+1.65),(sx,foot,1.65),(sx,gap,1.65),
                         (outside,gap,1.65),(h[0]+toward*(.2 if phone else 1.),h[1]-1.8,1.65),(h[0],h[1]-1.,1.65),h]
        ret = build_path(common_return,back_jp,hp,floor=level,stairs=[b],moving_start=True)
        # Different arrival times require a still occurrence for the crowd at this exact frame.
        return_name = f'hall{tag}-return-{side}'
        ra = register(f'back{tag}-a-{side}',ret,cr.last,phone,hall_cam,end=return_name,ms=True)
        joins.append((cr.name,ra.name))
        outputs[f'back{tag}-{room}'] = [cr.name,ra.name]
        stills[return_name] = dict(camera=hall_cam, frame=ra.last, source=hall_name)
        # Intro crosses the actual forecourt/reception boundary through a 3 m door opening.
        outside = next(r for r in g['venue']['rooms'] if r['id']=='forecourt')
        fy = outside['bounds']['y']+outside['bounds']['h']
        intro_start = dict(hp,location=np.array([-6.,fy-4.,outside.get('elevation',0)+1.65]),yaw=math.pi/2,pitch=0.)
        # the ground under the walk in, measured in the built scene (the facade and reception are modelled
        # separately and may move): the first surface below 2.6 m, under the door heads (the forecourt and the
        # reception are 1.2 m up, the hall at 0)
        graph = bpy.context.evaluated_depsgraph_get()
        hall_y = next(l for l in g['venue']['links'] if l['id']=='hall-steps')['bounds']
        hall_y = hall_y['y']+hall_y['h']
        def intro_floor(x,y,z):
            if y > hall_y+.3:
                return 0.  # the hall floor; people and booths stand on it
            top = 2.6
            for _ in range(8):  # look through people, plants and furniture to the floor
                hit, at, normal, _, ob, _ = scene.ray_cast(graph, Vector((x, y, top)), Vector((0, 0, -1)), distance=top+1.)
                if not hit:
                    return 0.
                if normal.z > .9 and not (ob.parent and ob.parent.name.startswith('crowd')) and at.z < 1.25:
                    return at.z
                top = at.z-.001
            return 0.
        intro_start['location'] = np.array([-6., fy-4., intro_floor(-6., fy-4., 0.)+1.65])
        intro_points = [intro_start['location'],(-6,fy,2.85),(-6,-48,2.85),
                        (-6,-39,2.85),(-6,-34.4,2.85),(-6,-32.0,1.65),
                        (0,-25,1.65),(0,-10,1.65),(0,5,1.65)]
        main = camera_pose(templates['hall'])['location']
        # the phone walk shares the main approach and leaves it for the totem only over the last metres
        intro_points += [(main[0],main[1]-3.,1.65),(h[0]-.6,h[1]-1.2,1.65),h] if phone else [(h[0],h[1]-3.,1.65),h]
        steps = next(l for l in g['venue']['links'] if l['id']=='hall-steps')['bounds']     # 1.2 m down into the hall
        poses = build_path(intro_points,intro_start,hp,floor=intro_floor,stairs=[steps],target_seconds=15.)
        ci = register('intro'+tag,poses,HALL_FRAME-len(poses)+1,phone,hall_cam,end=hall_name)
        outputs[ci.name] = [ci.name]
    return clips, joins, outputs, stills


def animate_doors(g, clips):
    room, fh = g['n'],g['FH']
    door = g['doors'][room]
    face = door['face']
    # Both travel directions open the real hinges early enough to clear the approach.
    crossings = []
    for clip in clips.values():
        if clip.phone: continue
        if clip.name.startswith(('walk-b-', 'back-b-')):
            target = np.array([door['wall_x'],door['yc'],fh+1.65])
            idx = min(range(len(clip.poses)),key=lambda i: np.linalg.norm(clip.poses[i]['location']-target))
            crossings.append(clip.first+idx)
            if clip.name.startswith('walk-b-'):
                g['doors'][room]['door_frame'] = idx
    for hinge, hand in door['leaves']:
        hinge.animation_data_clear()
        for fr in sorted(set([min(crossings)-50]+[f+d for f in crossings for d in (-45,-15,20,50)])):
            opened = any(f-15 <= fr <= f+20 for f in crossings)
            hinge.rotation_euler.z = -hand*face*1.45 if opened else 0.
            hinge.keyframe_insert('rotation_euler',frame=fr)



def stretch(clip, intervals):
    """Retiming with exact unit-rate samples at the moving joint, monotonic elsewhere."""
    old = len(clip.poses)-1
    if intervals <= old: return
    indices = np.arange(intervals,dtype=float)+.5
    distance = indices if clip.moving_start else intervals-indices
    width = min(90.,old*.4)
    weights = 1-smooth((distance-4)/width) if clip.moving_start or clip.moving_end else np.zeros(intervals)
    constant = (old-weights.sum())/(intervals-weights.sum())
    times = np.r_[0.,np.cumsum(constant+(1-constant)*weights)]
    times[-1] = old
    old_times = np.arange(old+1)
    poses = clip.poses
    coordinates = np.array([p['location'] for p in poses])
    positions = np.array([np.interp(times,old_times,coordinates[:,k]) for k in range(3)]).T
    channels = {}
    for key in ('yaw','pitch','lens','shift_x','shift_y'):
        values = np.array([p[key] for p in poses])
        if key=='yaw': values=np.unwrap(values)
        channels[key] = np.interp(times,old_times,values)
    clip.poses = [dict(location=point,**{k:float(v[i]) for k,v in channels.items()})
                  for i,point in enumerate(positions)]


def build_routes(g):
    # Plan every talk room before assigning timestamps. Equal round-trip B slots per
    # side/aspect let BOTH shared pieces render once while every room still anchors
    # its outward arrival and return departure to exactly the same scene frame.
    planned = {}
    for room in range(3,11):
        context = dict(g,n=room,side='west' if g['doors'][room]['west'] else 'east')
        if room != g['n']:
            loc,look,fov,_ = g['seat_for'](room)
            narrow = g['still_cam'](f'cam-plan-seat-{room}',loc,look,fov,level_for=16/9)
            bpy.context.view_layer.update()
            wide,_,_ = g['widened'](narrow,g['LAPTOP'],.16,.5)
            tot = g['doors'][room]['totem']; face=g['doors'][room]['face']; z=tot['z']+.14
            hfov=2*math.atan(tot['w']/2/.74/2.)
            phone = g['still_cam'](f'cam-plan-door-{room}',(tot['x']+face*2,tot['y'],z),
                                   (tot['x'],tot['y'],z),2*math.degrees(math.atan(math.tan(hfov/2)*1170/540)))
            context.update(seat_wide_cam=wide,door_cam=phone)
        planned[room] = _room_routes(context)
    # Timeline: the walk out starts on the hall still (HALL_FRAME) and the per-room half follows the shared one.
    # The walk back's shared half ends on the hall still a whole number of crowd periods later, so it matches
    # the still; the per-room half ends where it starts. Nobody walks in the rooms or near the door totems (the
    # crowd there stands still), so the seat and door stills need not share a frame with the walk back.
    longest = max(len(c.poses) for clips,_,_,_ in planned.values() for c in clips.values())
    back_last = HALL_FRAME+CROWD_PERIOD*math.ceil(4*longest/CROWD_PERIOD)
    all_clips = {}
    for room,(clips,joins,outputs,stills) in planned.items():
        side='west' if g['doors'][room]['west'] else 'east'
        for tag in ('','-phone'):
            a,b,r,z=[clips[name] for name in (f'walk{tag}-a-{side}',f'walk{tag}-b-{room}',
                                             f'back{tag}-b-{room}',f'back{tag}-a-{side}')]
            b.first=a.last
            z.first=back_last-len(z.poses)+1
            r.first=z.first-len(r.poses)+1
            stills[b.end_still]['frame']=b.last
            stills[z.end_still]['frame']=z.last
        all_clips.update({f'{room}:{name}':c for name,c in clips.items()})
    clips,joins,outputs,stills=planned[g['n']]
    g['all_path_clips']=all_clips  # Phase-2 crowd placement reserves all eight rooms, both aspects.
    for clip in clips.values():
        template=g['phone_hall_cam'] if clip.phone else g['hall_cam']
        key_camera(clip,template,g['scene'])
    animate_doors(g,clips)
    return clips,joins,outputs,stills


def write_manifest(g, clips, joins, outputs, stills):
    shots, room = g['shots'],g['n']
    for name, clip in clips.items():
        shots[name] = dict(kind='clip',pipeline=2,frames=len(clip.poses),fps=FPS,first=clip.first,
                           last=clip.last,side=g['side'],phone=clip.phone,
                           timeline_scope='shared' if '-a-' in name or name.startswith('intro') else 'room',
                           start_still=clip.start_still,end_still=clip.end_still)
    for name, parts in outputs.items():
        count = sum(len(clips[p].poses)-1 for p in parts)+1
        shots[name] = dict(shots.get(name,{}),kind='clip',pipeline=2,parts=parts,frames=count,fps=FPS,
                           first=clips[parts[0]].first,last=clips[parts[-1]].last,
                           start_still=clips[parts[0]].start_still,end_still=clips[parts[-1]].end_still)
        if name == f'walk-{room}':
            shots[name]['door_frame'] = len(clips[parts[0]].poses)-1+g['doors'][room]['door_frame']
    for name, entry in stills.items():
        if 'source' in entry: shots[name] = dict(shots[entry['source']])
        shots[name].update(frame=entry['frame'],camera=entry['camera'].name,pipeline=2)
        if 'source' in entry and 'front' in shots[name]: shots[name]['front'] = name+'-front'
    serial = {name: dict(first=c.first,phone=c.phone,moving_start=c.moving_start,moving_end=c.moving_end,
                        poses=[{k:(list(map(float,v)) if k=='location' else float(v)) for k,v in p.items()} for p in c.poses])
              for name,c in clips.items()}
    payload = dict(room=room,clips=serial,joins=joins,outputs=outputs,crowd_clearance=.8,
                   crowd_points=path_sample_points(g.get('all_path_clips',clips)),stills={k:v['frame'] for k,v in stills.items()})
    (g['OUT']/f'paths-{room}.json').write_text(json.dumps(payload,separators=(',',':')))
    return payload
