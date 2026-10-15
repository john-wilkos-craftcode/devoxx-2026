"""Cheap render/contact-sheet mode, numerical plan export, and opt-in frame timing."""
import json
import math
import time
import numpy as np
import bpy


def selected(clips,outputs,selection):
    result = []
    for name in (list(clips) if selection=='all' else selection.split(',')):
        parts = outputs.get(name,[name])
        for part in parts:
            if part not in clips: raise ValueError(f'Unknown clip {part}; choices: {list(clips)}')
            if part not in result: result.append(part)
    return result


def render_clip(scene,clip,out,walk_res,preview=False,step=1,samples=24,engine='cycles',single=None):
    scene.camera = clip.camera
    w,h = (540,1170) if clip.phone else walk_res
    if preview:
        scale = 480/max(w,h); w,h = round(w*scale),round(h*scale)
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.show_shadows = True
        scene.render.use_compositing = False
    else:
        scene.render.engine = 'CYCLES' if engine=='cycles' else 'BLENDER_EEVEE'
        scene.cycles.samples = samples
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = .25
        scene.render.use_persistent_data = True   # keep textures and static geometry between frames
    scene.render.resolution_x,scene.render.resolution_y = w,h
    scene.render.resolution_percentage = 100
    directory = out/clip.name
    directory.mkdir(parents=True,exist_ok=True)
    indices = [single] if single is not None else list(range(0,len(clip.poses),3 if preview else step))
    if single is None and indices[-1] != len(clip.poses)-1: indices.append(len(clip.poses)-1)
    files = []
    for i in indices:
        scene.frame_set(clip.first+i)
        # Relative index, independent of global timeline: publish validates complete 0..N-1 sequences.
        path = directory/f'f_{i:05d}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        files.append((path,clip.first+i))
    if preview: contact_sheet(files,out/f'{clip.name}-sheet.png',clip.phone)
    return files


DIGITS = ['111101101101111','010110010010111','111001111100111','111001111001111',
          '101101111001001','111100111001111','111100111101111','111001001001001',
          '111101111101111','111101111001111']


def contact_sheet(files,destination,phone=False):
    """Blender/numpy only: no Pillow install needed in Windows Blender's Python."""
    tw,th = (92,200) if phone else (192,108)
    columns = 8 if phone else 6
    rows = math.ceil(len(files)/columns)
    pixels = np.ones((rows*(th+18),columns*tw,4),dtype=np.float32)*.06
    pixels[:,:,3] = 1
    for i,(path,frame) in enumerate(files):
        im = bpy.data.images.load(str(path),check_existing=False)
        w,h = im.size
        data = np.empty(w*h*4,dtype=np.float32); im.pixels.foreach_get(data)
        data = data.reshape(h,w,4)[::-1]
        thumb = data[np.linspace(0,h-1,th).astype(int)][:,np.linspace(0,w-1,tw).astype(int)]
        y,x = (i//columns)*(th+18),(i%columns)*tw
        pixels[y:y+th,x:x+tw] = thumb
        for j,char in enumerate(str(frame)):
            if not char.isdigit(): continue
            bitmap = np.array([float(v) for v in DIGITS[int(char)]]).reshape(5,3)
            bitmap = np.repeat(np.repeat(bitmap,2,axis=0),2,axis=1)
            pixels[y+th+3:y+th+13,x+4+j*8:x+10+j*8,:3] = bitmap[:,:,None]
        bpy.data.images.remove(im)
    h,w,_ = pixels.shape
    sheet = bpy.data.images.new(destination.stem,width=w,height=h)
    sheet.pixels.foreach_set(np.ascontiguousarray(pixels[::-1]).ravel())
    sheet.filepath_raw, sheet.file_format = str(destination),'PNG'
    sheet.save(); bpy.data.images.remove(sheet)
    print(f'CHECK PREVIEW sheet={destination} frames={len(files)}')


def render_selected(scene,clips,outputs,selection,out,walk_res):
    for name in selected(clips,outputs,selection):
        render_clip(scene,clips[name],out,walk_res,preview=True)


def benchmark(scene,clips,outputs,selection,out,walk_res):
    results = {}
    for name in selected(clips,outputs,selection):
        clip = clips[name]
        start = time.perf_counter()
        # Isolated output so a timing sample cannot masquerade as a complete render.
        render_clip(scene,clip,out/'timing',walk_res,samples=24,single=len(clip.poses)//2)
        seconds = time.perf_counter()-start
        results[name] = dict(frame_seconds=seconds,frames=len(clip.poses),
                             estimated_minutes=seconds*len(clip.poses)/60,
                             note='single cold frame, includes scene upload and shader setup')
        print(f'CHECK TIMING {name} frame={seconds:.2f}s frames={len(clip.poses)} estimate={seconds*len(clip.poses)/60:.1f}min')
    (out/'timings.json').write_text(json.dumps(results,indent=2))


def export_footprints(scene,out,room,payload):
    """Slice actual evaluated meshes, including future people; never substitute JSON colliders."""
    graph = bpy.context.evaluated_depsgraph_get()
    plans = {'ground':[],'upstairs':[],'west-stair':[],'east-stair':[]}
    slices = [('ground',2, .8,(0,1)),('upstairs',2,7.,(0,1)),
              ('west-stair',0,-6.,(1,2)),('east-stair',0,11.4,(1,2))]
    for obj in scene.objects:
        if obj.type not in ('MESH','CURVE','FONT'): continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        if not mesh: continue
        try:
            vertices = [evaluated.matrix_world@v.co for v in mesh.vertices]
            for name,axis,level,projection in slices:
                coords = [v[axis] for v in vertices]
                if not coords or not min(coords)<=level<=max(coords): continue
                for polygon in mesh.polygons:
                    points = [vertices[i] for i in polygon.vertices]
                    hits = []
                    for a,b in zip(points,points[1:]+points[:1]):
                        if (a[axis]-level)*(b[axis]-level)<0:
                            hit = a.lerp(b,(level-a[axis])/(b[axis]-a[axis]))
                            hits.append([round(hit[k],3) for k in projection])
                    if len(hits)>=2: plans[name].append(hits[:2])
        finally: evaluated.to_mesh_clear()
    payload['geometry_slices'] = plans
    (out/f'paths-{room}.json').write_text(json.dumps(payload,separators=(',',':')))
    print(f'CHECK PLAN room={room} slices='+str({k:len(v) for k,v in plans.items()}))


def realize_for_audit(scene):
    """Scene ray_cast cannot reliably see unrealized Geometry Nodes instances.

    Temporarily realize modifier outputs, including the seat instances, so clearance,
    floor rays and plan slices inspect the same surfaces the renderer sees. Restore
    the instanced originals before rendering to retain their memory savings.
    """
    changed = []
    for obj in scene.objects:
        for modifier in obj.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group: continue
            original = modifier.node_group
            group = original.copy()
            outputs = [node for node in group.nodes if node.type=='GROUP_OUTPUT']
            for output in outputs:
                for socket in output.inputs:
                    if socket.type!='GEOMETRY' or not socket.is_linked: continue
                    link=socket.links[0]; source=link.from_socket
                    group.links.remove(link)
                    realize=group.nodes.new('GeometryNodeRealizeInstances')
                    group.links.new(source,realize.inputs['Geometry'])
                    group.links.new(realize.outputs['Geometry'],socket)
            modifier.node_group=group
            changed.append((modifier,original,group))
    bpy.context.view_layer.update()
    return changed


def restore_instances(changed):
    for modifier,original,temporary in changed:
        modifier.node_group=original
        bpy.data.node_groups.remove(temporary)
    bpy.context.view_layer.update()
