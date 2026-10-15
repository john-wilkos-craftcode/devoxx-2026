"""Per-frame scene audit for phase-1 routes. Failures aggregate by rule and clip."""
import json
import math
from collections import defaultdict
from mathutils import Vector


def pose(camera):
    return {
        'location': camera.matrix_world.translation.copy(),
        'rotation': camera.matrix_world.to_quaternion(),
        'euler': camera.rotation_euler.copy(),
        'lens': camera.data.lens,
        'shift_x': camera.data.shift_x,
        'shift_y': camera.data.shift_y,
    }


def pose_error(a, b):
    return ((a['location'] - b['location']).length,
            math.degrees(2*math.acos(min(1.,abs(a['rotation'].normalized().dot(b['rotation'].normalized()))))),
            max(abs(a[k] - b[k]) for k in ('lens', 'shift_x', 'shift_y')))


def matches(a, b):
    distance, angle, optics = pose_error(a, b)
    return distance < .001 and angle < .05 and optics < 1e-6


def heading(p):
    d = p['rotation'] @ Vector((0, 0, -1))
    return math.atan2(d.y, d.x), math.atan2(d.z, math.hypot(d.x, d.y)), d


def angle_delta(a, b):
    return abs(math.degrees(math.atan2(math.sin(a-b), math.cos(a-b))))


def ray_directions():
    # Fibonacci sphere plus cardinal axes: glass and animated leaves count as geometry.
    directions = [Vector(v) for v in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))]
    for i in range(64):
        z = 1 - 2 * (i + .5) / 64
        r, a = math.sqrt(1-z*z), i * math.pi * (3-math.sqrt(5))
        directions.append(Vector((r*math.cos(a), r*math.sin(a), z)))
    return directions


def physical_ray(scene,graph,origin,direction,distance):
    travelled=0.; point=origin.copy()
    while travelled<distance:
        result=scene.ray_cast(graph,point,direction,distance=distance-travelled)
        if not result[0]: return result
        ob=result[4]
        # A pure atmospheric volume has no physical surface. Glass still counts.
        materials=[m for m in ob.data.materials if m] if hasattr(ob.data,'materials') else []
        volume=bool(materials) and all(m.use_nodes and any(n.type=='OUTPUT_MATERIAL' and
            n.inputs['Volume'].is_linked and not n.inputs['Surface'].is_linked for n in m.node_tree.nodes) for m in materials)
        if not volume: return result
        hop=(result[1]-point).length+.001; travelled+=hop; point=result[1]+direction*.001
    return (False,None,None,None,None,None)


RAKES = []
SETTLE = 54     # frames at either end of a clip that turn on the spot and blend to or from a still


def audit_clip(scene, fps, clip, stills, stair_links):
    import bpy
    records, problems = [], defaultdict(list)
    directions = ray_directions()
    maximum = dict(speed=0., acceleration=0., yaw=0., yaw_acceleration=0., pitch=0.)
    clearance = .35
    steps, yaw_steps, accels = [], [], []
    rakes = RAKES

    def fail(rule, frame, detail):
        problems[rule].append((frame, detail))

    for i in range(len(clip.poses)):
        frame = clip.first+i
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        p = pose(clip.camera.evaluated_get(graph)); records.append(p)
        loc = p['location']
        settling = (not clip.moving_start and i < SETTLE) or (not clip.moving_end and i >= len(clip.poses)-SETTLE)
        for direction in directions:
            hit, at, _, _, ob, _ = physical_ray(scene,graph,loc,direction,.35)
            if hit:
                distance = (at-loc).length
                clearance = min(clearance,distance)
                fail('clearance',frame,f'{ob.name}: {distance:.3f} m at ({loc.x:.2f},{loc.y:.2f},{loc.z:.2f})')
                break
        # over the seating (the last stretch into the seat, the first out of it) the camera crouches along the row
        in_rows = any(r['x'] <= loc.x <= r['x']+r['w'] and r['y'] <= loc.y <= r['y']+r['h'] for r in rakes)
        if not settling and not in_rows:
            hit, at, _, _, ob, _ = physical_ray(scene,graph,loc,Vector((0,0,-1)),30)
            if not hit: fail('head height',frame,'no floor within 30 m')
            elif not 1.45 <= loc.z-at.z <= 1.8:
                fail('head height',frame,f'{loc.z-at.z:.3f} m above {ob.name} at ({loc.x:.2f},{loc.y:.2f})')
        yaw,pitch,view = heading(p)
        if not settling and abs(math.degrees(pitch)) > 25:
            fail('pitch',frame,f'{math.degrees(pitch):.2f} degrees')
        if not i: continue
        previous = records[-2]
        delta = loc-previous['location']; steps.append(delta)
        speed = delta.length*fps
        maximum['speed'] = max(maximum['speed'],speed)
        if speed >= 7: fail('peak speed',frame,f'{speed:.3f} m/s')
        for link in stair_links:
            b = link['bounds']
            if b['x'] <= loc.x <= b['x']+b['w'] and b['y'] <= loc.y <= b['y']+b['h']:
                if delta.xy.length*fps > 3.001: fail('stair speed',frame,f'{delta.xy.length*fps:.3f} m/s')
        old_yaw,old_pitch,_ = heading(previous)
        signed_yaw = math.degrees(math.atan2(math.sin(yaw-old_yaw),math.cos(yaw-old_yaw)))
        dy,dp = abs(signed_yaw),angle_delta(pitch,old_pitch)
        yaw_steps.append(signed_yaw)
        maximum['yaw'],maximum['pitch'] = max(maximum['yaw'],dy),max(maximum['pitch'],dp)
        if dy > 4.501: fail('yaw rate',frame,f'{dy:.3f} degrees/frame')
        if dp > 1.501: fail('pitch rate',frame,f'{dp:.3f} degrees/frame')
        if max(abs(math.degrees(a-b)) for a,b in zip(p['euler'],previous['euler'])) > 90:
            fail('Euler wrap',frame,'component jump >90 degrees')
        if not settling and delta.xy.length*fps > .3 and view.xy.length > 1e-8:
            angle = math.degrees(view.xy.angle(delta.xy))
            if angle > 60: fail('backwards',frame,f'{angle:.2f} degrees from travel')
        if len(steps)>1:
            acceleration = (steps[-1]-steps[-2]).length*fps*fps
            maximum['acceleration'] = max(maximum['acceleration'],acceleration)
            ya = abs(yaw_steps[-1]-yaw_steps[-2])
            maximum['yaw_acceleration'] = max(maximum['yaw_acceleration'],ya)
            if ya > .61: fail('yaw acceleration',frame,f'{ya:.3f} degrees/frame²')
            # along the path: how hard it speeds up or brakes, and how suddenly that changes (a lurch)
            along = (delta.length-steps[-2].length)*fps*fps
            accels.append(along)
            if not settling:
                if acceleration > 6.501: fail('acceleration',frame,f'{acceleration:.3f} m/s²')
                if len(accels) > 1 and abs(accels[-1]-accels[-2]) > .8:
                    fail('lurch',frame,f'{accels[-2]:.2f} -> {accels[-1]:.2f} m/s² in one frame')
    for label, actual, key in [('start still',records[0],clip.start_still),('end still',records[-1],clip.end_still)]:
        if not key: continue
        entry = stills[key]
        expected_frame = clip.first if label.startswith('start') else clip.last
        scene.frame_set(entry['frame'])
        expected = pose(entry['camera'])
        # the crowd only walks in the hall: the seat and the door totems' stills needn't share the walk back's frame
        if entry['frame'] != expected_frame and not (label.startswith('start') and key.startswith(('seat-','door-phone-'))):
            fail('timeline',expected_frame,f'{key} is at {entry["frame"]}')
        if not matches(actual,expected):
            fail(label,expected_frame,'metres/degrees/optics='+str(pose_error(actual,expected)))
    summary = {}
    print(f'CHECK {clip.name:22s} frames={len(records):4d} timeline={clip.first}:{clip.last} '
          + ' '.join(f'{k}={v:.3f}' for k,v in maximum.items())+f' clearance>={clearance:.3f}')
    for rule,events in problems.items():
        frame,detail = events[0]
        count = len({f for f,_ in events})
        summary[rule] = dict(frames=count,first=frame,detail=detail)
        print(f'FAIL {clip.name}: {rule}: {count} frames; first={frame}: {detail}')
    return records,dict(frames=len(records),first=clip.first,last=clip.last,maximum=maximum,failures=summary)


def audit_paths(scene,fps,out,room,clips,joins,outputs,stills,stair_links,rakes=()):
    RAKES[:] = [l['bounds'] for l in rakes]
    result,paths,structural = {},{},[]
    for name,clip in clips.items():
        paths[name],result[name] = audit_clip(scene,fps,clip,stills,stair_links)
    for a,b in joins:
        pa,pb = paths[a],paths[b]
        if not matches(pa[-1],pb[0]): structural.append(f'{a}/{b}: joint pose mismatch {pose_error(pa[-1],pb[0])}')
        va,vb = pa[-1]['location']-pa[-2]['location'],pb[1]['location']-pb[0]['location']
        if (va-vb).length*fps > .005 or min(va.length,vb.length)*fps < .3:
            structural.append(f'{a}/{b}: joint velocity mismatch/stop: {tuple(va*fps)} / {tuple(vb*fps)}')
        # Check angular velocity as well, including the seam's second difference.
        ya0,_,_ = heading(pa[-2]); ya1,_,_ = heading(pa[-1]); yb1,_,_ = heading(pb[1])
        if abs(angle_delta(ya1,ya0)-angle_delta(yb1,ya1)) > .6:
            structural.append(f'{a}/{b}: joint yaw acceleration exceeds 0.6')
        if clips[a].last != clips[b].first: structural.append(f'{a}/{b}: timeline gap')
        for offset in (-.25,.25):
            instant=clips[a].last+offset
            whole=math.floor(instant)
            scene.frame_set(whole,subframe=instant-whole)
            if not matches(pose(clips[a].camera),pose(clips[b].camera)):
                structural.append(f'{a}/{b}: subframe pose mismatch at shutter offset {offset}')
    for name,parts in outputs.items():
        frames = sum(len(clips[p].poses)-1 for p in parts)+1
        seconds = (frames-1)/fps
        limit = 18 if name.startswith('intro') else 16
        # Seat departures explicitly allow additional turn time; report measured length anyway.
        print(f'CHECK OUTPUT {name} frames={frames} seconds={seconds:.2f} parts={"+".join(parts)}')
        if seconds > limit and not (name.startswith('back-') and not name.startswith('back-phone-')):
            structural.append(f'{name}: duration {seconds:.2f}s exceeds requested {limit}s; motion caps retained')
    for problem in structural: print('FAIL '+problem)
    failures = sum(len(x['failures']) for x in result.values())+len(structural)
    report = dict(room=room,status='FAIL' if failures else 'PASS',failure_groups=failures,
                  clips=result,structural_failures=structural)
    (out/f'check-{room}.json').write_text(json.dumps(report,indent=2))
    print(f'CHECK RESULT room={room} status={report["status"]} failure_groups={failures}')
    return failures
