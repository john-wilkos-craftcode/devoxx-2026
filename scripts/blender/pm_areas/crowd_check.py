"""Close-up check of the crowd test set (crowd.TEST_SPEC: six people, backpacks on three): each person from the
front, the side and the back at 2 m (backpack wearers at 1.5 m, plus three-quarter behind), a talker's chest at 1 m,
Cycles 64, others hidden.

  scripts/photomatch/render.sh crowd_check
Writes C:/Users/wilkojo/kino-renders/photomatch/crowd/check/<person>-<view>.png; PACK lines report the backpack fit.
"""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

import pm_areas.crowd as C

OUT = Path("C:/Users/wilkojo/kino-renders/photomatch/crowd/check")
FRAME = 160


def tree_of(ob):
    out = [ob]
    for c in ob.children:
        out += tree_of(c)
    return out


def build(root, unified=False):
    scene = bpy.context.scene
    crowd = C.build(root)
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.type == backend for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == backend
                break
        except TypeError:
            continue
    scene.cycles.device, scene.cycles.samples, scene.cycles.use_denoising = "GPU", 64, True
    scene.view_settings.view_transform, scene.view_settings.look = "AgX", "AgX - Medium High Contrast"
    scene.render.resolution_x, scene.render.resolution_y = 600, 900
    data = bpy.data.cameras.new("cam-check")
    data.sensor_fit, data.angle_y = "VERTICAL", math.radians(56)
    cam = bpy.data.objects.new("cam-check", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    OUT.mkdir(parents=True, exist_ok=True)
    anchors = [o for o in crowd.coll.objects if o.type == "EMPTY" and o.parent is None]
    groups = {a.name: set(tree_of(a)) for a in anchors}
    scene.frame_set(FRAME)
    people = {p["name"]: p for p in crowd.people}
    for a in anchors:
        for name, objs in groups.items():
            for o in objs:
                o.hide_render = name != a.name
        for o in bpy.data.objects:                      # wearables are parented to the rig, already in the group
            if o.name.startswith(a.name + "-") and o.name.endswith("-proxy"):
                o.hide_render = True
        x = a.location.x
        p = people.get(a.name, {})
        d, aim = (1.5, 1.15) if p.get("pack_ob") else (2.0, 0.95)
        views = [("front", (x, -d, 1.55)), ("side", (x + d, 0.0, 1.55)), ("back", (x, d, 1.55))]
        if p.get("pack_ob"):
            views.append(("back34", (x + d * 0.71, d * 0.71, 1.6)))
        if "talk" in p.get("clip", "") and not any("close" in v for v, _ in views):
            views.append(("close-front", (x, -1.0, 1.5)))
        for view, loc in views:
            cam.location = loc
            target = Vector((x, 0, 1.35 if view == "close-front" else aim))
            cam.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(OUT / f"{a.name}-{view}.png")
            bpy.ops.render.render(write_still=True)
    print("done", flush=True)
    sys.exit(0)
