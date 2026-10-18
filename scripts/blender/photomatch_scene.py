"""Photo-matched venue: build one area (scripts/blender/pm_areas/<area>.py) and render it from the cameras solved
for its reference photos (data/photomatch/cameras/<area>.json, solved by scripts/photomatch/calib.py), so every render
can be laid over its photo.

  blender.exe -b --python scripts/blender/photomatch_scene.py -- --root <repo> --area upstairs
      [--cams upstairs_hall,upstairs_w_people] [--out C:/Users/wilkojo/kino-renders/photomatch]
      [--samples 64] [--width 1280] [--engine cycles|workbench|eevee] [--save area.blend]
Run from WSL with scripts/photomatch/render.sh.
"""
import argparse
import importlib
import math
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--area", required=True)
ap.add_argument("--cams", default="")
ap.add_argument("--out", default="C:/Users/wilkojo/kino-renders/photomatch")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--width", type=int, default=1280)
ap.add_argument("--engine", default="cycles", choices=["cycles", "workbench", "eevee"])
ap.add_argument("--shadow-scale", type=float, default=0.0, help="EEVEE shadow map resolution scale (< 1: fewer pages, no 'shadow buffer full' at 1600 px)")
ap.add_argument("--tex-limit", default="", help="cap every GPU texture at this size (1024, 2048): EEVEE on a 4 GB card")
ap.add_argument("--final", action="store_true", help="EEVEE final quality: ray tracing at full resolution, more shadow rays")
ap.add_argument("--save")
ap.add_argument("--walk", default="", help="render walk frames: a comma list, every:N, or all (area venue)")
ap.add_argument("--plan", default="", help="top-down cut below this height: x0,y0,x1,y1,cut_z[,ppm] (Workbench)")
ap.add_argument("--variant", default="", help="area variant, e.g. phone for venue's portrait walk")
ap.add_argument("--blur", action="store_true", help="walk stills: the clip's motion blur (full-frame shutter, centred)")
ap.add_argument("--blur-steps", default="4", help="EEVEE motion blur steps (accumulation; 4 fixed the vector blur's hard edges on near columns, 16/10 A/B; 0 = Blender's 1); stills take a comma list to A/B")
ap.add_argument("--max-spf", type=float, default=0, help="walk anim: render 5 frames, stop if they average more seconds a frame than this")
ap.add_argument("--back", action="store_true", help="with --room: the walk back from the room to the hall still")
ap.add_argument("--anim-range", default="", help="walk anim: only frames a-b (time a clip before rendering it all)")
ap.add_argument("--hide", default="", help="collections to leave out of the render, comma list (checks)")
ap.add_argument("--stills", action="store_true", help="venue with --room: the page's stills from this walk's build "
                "(laptop: hall + seat, phone: hall totem + door totem), each with its front layer and overlay corners")
ap.add_argument("--room", type=int, default=0, help="venue: the walk to this room (3-10) instead of the fly-through")
ap.add_argument("--crowd", action="store_true", help="venue: add the crowd (pm_areas/crowd.py)")
ap.add_argument("--unified", action="store_true", help="build the area as part of the whole venue (no photo hacks)")
args = ap.parse_args(argv)
ROOT = Path(args.root)
sys.path[:0] = [str(ROOT / "scripts" / "blender"), str(ROOT / "scripts" / "photomatch")]
from pm import Cam  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

t0 = time.time()
area = importlib.import_module(f"pm_areas.{args.area}")
if args.variant:
    area.VARIANT = args.variant
if args.crowd:
    area.CROWD = True
if args.room:
    area.ROOM = args.room
    area.BACK = args.back
if args.unified:
    area.build(ROOT, unified=True)
else:
    area.build(ROOT)
print(f"BUILT {args.area} in {time.time() - t0:.1f}s, {len(scene.objects)} objects")
for cn in [c for c in args.hide.split(",") if c]:
    if cn in bpy.data.collections:
        bpy.data.collections[cn].hide_render = True
        print(f"HIDDEN collection {cn}")

# ---------------------------------------------------------------------------------- render settings
if args.engine == "cycles":
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
    scene.cycles.device = "GPU"
    scene.cycles.samples = args.samples
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
elif args.engine == "eevee":
    scene.render.engine = "BLENDER_EEVEE"
    ev = scene.eevee
    for attr, val in (("taa_render_samples", args.samples), ("use_raytracing", True), ("use_shadows", True),
                      ("use_gtao", True), ("use_bloom", True), ("shadow_pool_size", "1024")):
        if hasattr(ev, attr):
            setattr(ev, attr, val)
    if args.shadow_scale:
        ev.shadow_resolution_scale = args.shadow_scale
        ev.shadow_step_count = 16                    # cheap, and stops light leaks from the coarser maps
        print(f"FINAL shadows at {args.shadow_scale:g} resolution, 16 steps", flush=True)
    if args.tex_limit:                               # BRIEF.md render notes: the crowd's 2K textures fill a 4 GB card
        bpy.context.preferences.system.gl_texture_limit = f"CLAMP_{args.tex_limit}"
        print(f"FINAL textures capped at {args.tex_limit} px", flush=True)
    if args.final:                                   # BRIEF.md's rubric: the preview passed at half-res tracing
        rt = getattr(ev, "ray_tracing_options", None)
        for holder, attr, val in ((rt, "resolution_scale", "1"), (ev, "shadow_ray_count", 2), (ev, "shadow_step_count", 8),
                                  (ev, "shadow_resolution_scale", 1.0)):
            if holder is not None and hasattr(holder, attr):
                setattr(holder, attr, val)
        print(f"FINAL quality: ray tracing x{getattr(rt, 'resolution_scale', '?')}, shadow rays {getattr(ev, 'shadow_ray_count', '?')}",
              flush=True)
else:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
scene.view_settings.view_transform = getattr(area, "VIEW_TRANSFORM", "AgX")   # AgX greys out saturated lights; "Khronos PBR Neutral" keeps them
try:
    scene.view_settings.look = getattr(area, "LOOK", "AgX - Medium High Contrast")
except TypeError:
    scene.view_settings.look = "None"
scene.view_settings.exposure = getattr(area, "EXPOSURE", 0.0)
scene.render.image_settings.file_format = "PNG"

# ---------------------------------------------------------------------------------- walk frames / plan cut
def render_plan():
    vals = [float(v) for v in args.plan.split(",")]
    x0, y0, x1, y1, cut = vals[:5]
    ppm = vals[5] if len(vals) > 5 else 10
    data = bpy.data.cameras.new("cam-plan")
    data.type, data.ortho_scale = "ORTHO", max(x1 - x0, y1 - y0)
    data.clip_start, data.clip_end = 100 - cut, 120
    ob = bpy.data.objects.new("cam-plan", data)
    scene.collection.objects.link(ob)
    ob.location, ob.rotation_euler = ((x0 + x1) / 2, (y0 + y1) / 2, 100), (0, 0, 0)
    keep = (scene.render.engine, scene.camera, scene.render.resolution_x, scene.render.resolution_y)
    scene.camera = ob
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light, scene.display.shading.color_type = "FLAT", "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = round((x1 - x0) * ppm), round((y1 - y0) * ppm)
    if (x1 - x0) < (y1 - y0):
        data.sensor_fit = "VERTICAL"
    out = Path(args.out) / args.area
    out.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out / f"plan-cut{cut:g}.png")
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED plan -> {scene.render.filepath}")
    scene.render.engine, scene.camera, scene.render.resolution_x, scene.render.resolution_y = keep


def set_blur_steps(n):
    for holder in (scene.render, scene.eevee):        # EEVEE: accumulation steps fix the vector blur's edges
        if n and hasattr(holder, "motion_blur_steps"):
            holder.motion_blur_steps = n
            print(f"BLUR steps {n} on {type(holder).__name__}", flush=True)
            return


def render_stills():
    """The page's stills from a room walk's build (John 18/10: the stills over, so they match the walks): laptops the
    hall still (the walk's first frame) and the room's wide seat still (its last; the published camera); phones the
    hall totem still and the door totem still. Each with its cut-out front layer (what stands in front of the screen,
    on transparency) and the screen's corners on the image, in shots-stills-<variant>-<n>.json (the seat's overlay is
    the published one: same camera, same auditorium)."""
    from bpy_extras.object_utils import world_to_camera_view
    import pm_areas.hall_screen as HS
    import pm_areas.door_totems as DT
    n, phone = args.room, args.variant == "phone"
    seats = json.loads((ROOT / "data" / "photomatch" / "seats.json").read_text())
    published = json.loads((ROOT / "site" / "cinema" / "media" / "shots.json").read_text())
    out = Path(args.out) / args.area / "stills"
    out.mkdir(parents=True, exist_ok=True)

    def cam_from(spec, name):
        data = bpy.data.cameras.new(name)
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.matrix_world = Matrix(spec["matrix"])
        data.sensor_fit, data.sensor_width, data.sensor_height = spec["sensor_fit"], spec["sensor_width"], spec["sensor_height"]
        data.lens, data.shift_x, data.shift_y, data.clip_start = spec["lens"], spec["shift_x"], spec["shift_y"], 0.05
        return ob

    def grow(corners, by=0.01):                       # a little larger: the HTML tucks under the bezel (build_scene)
        c = Vector([sum(p[i] for p in corners) / 4 for i in range(3)])
        return [c + (Vector(p) - c) * (1 + by / max(0.1, (Vector(p) - c).length)) for p in corners]

    def quad(corners, camera):
        bpy.context.view_layer.update()
        return [[round(v.x, 5), round(1 - v.y, 5)] for v in (world_to_camera_view(scene, camera, Vector(c)) for c in corners)]

    def seat_front(o):                                # this room's "#DEVOXX" and the seats (build_scene.front_layer);
        base = o.name.split(".")[0].removeprefix(f"aud{n}-")   # extract_auditorium.py names them aud<n>-<source>
        return base.startswith(f"word-{n}-") or base in ("seats", "seat-model")
    f0, f1 = scene.frame_start, scene.frame_end
    if phone:
        jobs = [("hall-phone", bpy.data.objects["cam-hall-phone"], (1080, 2340), f0, lambda o: o.name in HS.FRONT,
                 ("programme", HS.totem_corners, [HS.TOTEM["w"], HS.TOTEM["h"]])),
                (f"door-phone-{n}", cam_from(seats["doors_phone"][str(n)], f"cam-door-phone-{n}"), (1080, 2340), f1, None,
                 ("screen", DT.CORNERS[str(n)], [DT.W, DT.H]))]
    else:
        px = published.get(f"seat-{n}", {}).get("px", [2534, 1620])
        jobs = [("hall", bpy.data.objects["cam-hall"], (1920, 1080), f0, lambda o: o.name in HS.FRONT,
                 ("programme", HS.screen_corners, [HS.SCREEN["w"], HS.SCREEN["h"]])),
                (f"seat-{n}", cam_from(seats["seats"][str(n)], f"cam-seat-{n}"), tuple(px), f1, seat_front, None)]
    shots = {}
    for name, camera, res, frame, front, ov in jobs:
        scene.camera = camera
        scene.frame_set(frame)
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(out / f"{name}.png")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED still {name} {res[0]}x{res[1]} at frame {frame} in {time.time() - t1:.0f}s", flush=True)
        entry = dict(published.get(name, {"kind": "still"}))
        if ov:
            key, corners, size = ov
            entry["overlay"], entry["size"] = {key: quad(grow(corners), camera)}, {key: size}
        if front:
            held = [o for o in scene.objects if o.type in ("MESH", "CURVE", "FONT") and not front(o) and not o.is_holdout]
            for o in held:
                o.is_holdout = True
            comp, scene.render.use_compositing = scene.render.use_compositing, False
            scene.render.film_transparent, scene.render.image_settings.color_mode = True, "RGBA"
            scene.render.filepath = str(out / f"{name}-front.png")
            bpy.ops.render.render(write_still=True)
            for o in held:
                o.is_holdout = False
            scene.render.film_transparent, scene.render.image_settings.color_mode = False, "RGB"
            scene.render.use_compositing = comp
            entry["front"] = f"{name}-front"
            print(f"RENDERED still {name}-front ({len(held)} objects held out)", flush=True)
        shots[name] = entry
    (out / f"shots-stills-{'phone' if phone else 'laptop'}-{n}.json").write_text(json.dumps(shots, indent=1))
    print("done")
    sys.exit(0)


if args.stills:
    render_stills()
if args.plan:
    render_plan()
    if not args.walk:
        print("done")
        sys.exit(0)
if args.walk:
    out = Path(args.out) / args.area / ("walk" + (f"-{args.variant}" if args.variant else "") + (f"-room{args.room}" if args.room else "") + ("-back" if args.back else ""))
    out.mkdir(parents=True, exist_ok=True)
    cam = bpy.data.objects["cam-walk"]
    scene.camera = cam
    ww, wh = getattr(area, "WALK_SIZE", (16, 9))
    scene.render.resolution_x, scene.render.resolution_y = args.width, round(args.width * wh / ww)
    f0, f1 = scene.frame_start, scene.frame_end
    if args.walk == "anim" or args.blur:      # the clip's motion blur
        scene.render.use_motion_blur, scene.render.motion_blur_shutter = True, 1.0   # a full frame: long, soft streaks (John: "the blurrier the crowd, the better")
        if hasattr(scene.render, "motion_blur_position"):
            scene.render.motion_blur_position = "CENTER"
        set_blur_steps(int(args.blur_steps.split(",")[0]))
    if args.walk == "anim":
        if args.anim_range:
            a, b = (int(v) for v in args.anim_range.split("-"))
            scene.frame_start, scene.frame_end = a, b
            f0, f1 = a, b
        scene.render.filepath = str(out / "anim" / "f_####")
        t1 = time.time()
        if args.max_spf and f1 - f0 > 5:                 # time the clip before committing to it
            # 5 frames spread over the whole clip: the first 5 (the street) ran 7.6 s, the hall averaged 11.4 (16/10)
            for f in [f0 + round(i * (f1 - f0) / 4) for i in range(5)]:
                scene.frame_set(f)
                scene.render.filepath = str(out / "anim" / f"f_{f:04d}")
                bpy.ops.render.render(write_still=True)
            spf = (time.time() - t1) / 5
            print(f"TIMING {spf:.1f} s a frame over 5 spread frames: the clip would take {spf * (f1 - f0 + 1) / 60:.0f} min", flush=True)
            if spf > args.max_spf:
                print(f"STOPPED: over the {args.max_spf:.0f} s a frame limit", flush=True)
                sys.exit(3)
            scene.render.filepath = str(out / "anim" / "f_####")
            t1 = time.time()
        bpy.ops.render.render(animation=True)
        print(f"RENDERED anim {f1 - f0 + 1} frames in {time.time() - t1:.0f}s ({(time.time() - t1) / (f1 - f0 + 1):.1f} s a frame)")
        print("done")
        sys.exit(0)
    if args.walk == "all":
        frames = list(range(f0, f1 + 1))
    elif args.walk.startswith("every:"):
        n = int(args.walk.split(":")[1])
        frames = list(range(f0, f1 + 1, n)) + [f1]
    else:
        frames = [int(f) for f in args.walk.split(",")]
    for steps in ([int(n) for n in args.blur_steps.split(",")] if args.blur else [0]):
        if args.blur:
            set_blur_steps(steps)
        for f in frames:
            scene.frame_set(f)
            tag = (f"-blur{steps}" if args.blur else "")
            scene.render.filepath = str(out / f"walk-{f:04d}{tag}.png")
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"RENDERED walk {f}/{f1}{tag} in {time.time() - t1:.0f}s")
    print("done")
    sys.exit(0)
# ---------------------------------------------------------------------------------- cameras
cams = {k: v for f in sorted((ROOT / "data" / "photomatch" / "cameras").glob("*.json")) for k, v in json.loads(f.read_text()).items()}
wanted = [c for c in args.cams.split(",") if c] or [k for k, v in cams.items() if v["area"] == args.area]
out = Path(args.out) / args.area
out.mkdir(parents=True, exist_ok=True)
for name in wanted:
    spec = cams[name]
    if "cal" in spec:
        cam = Cam(json.loads((ROOT / "data" / "photomatch" / spec["cal"]).read_text()), spec["C"], spec.get("turns", 0))
        b = cam.blender()
    elif "blender" in spec:                   # a ready camera (e.g. a Street View crop with its off-centre optical axis)
        b = spec["blender"]
    else:
        # a check view with no photo: "C" (eye), "look" (target), "fov_h", optional "size" [w, h]
        fwd = (Vector(spec["look"]) - Vector(spec["C"])).normalized()
        M = fwd.to_track_quat("-Z", "Y").to_matrix().to_4x4()
        M.translation = Vector(spec["C"])
        W0, H0 = spec.get("size", [16, 9])
        b = {"matrix": [list(r) for r in M], "lens": 18 / math.tan(math.radians(spec["fov_h"]) / 2),
             "sensor_width": 36, "shift_x": 0.0, "shift_y": 0.0, "size": [W0, H0]}
    data = bpy.data.cameras.new(f"cam-{name}")
    ob = bpy.data.objects.new(f"cam-{name}", data)
    scene.collection.objects.link(ob)
    ob.matrix_world = Matrix(b["matrix"])
    data.sensor_fit, data.sensor_width, data.lens = b.get("sensor_fit", "HORIZONTAL"), b["sensor_width"], b["lens"]
    if "sensor_height" in b:
        data.sensor_height = b["sensor_height"]
    data.shift_x, data.shift_y = b["shift_x"], b["shift_y"]
    data.clip_start, data.clip_end = 0.05, 1000
    W, H = b["size"]
    scene.render.resolution_x = args.width
    scene.render.resolution_y = round(args.width * H / W)
    scene.render.resolution_percentage = 100
    scene.camera = ob
    if hasattr(area, "before_render"):
        area.before_render(name)
    scene.render.filepath = str(out / f"{name}.png")
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED {name} in {time.time() - t1:.0f}s -> {scene.render.filepath}")
if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=args.save)
print("done")
