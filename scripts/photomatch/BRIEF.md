# Brief: the photo-matched venue and its prerendered walks

Hand this file to every helper (subagent, Codex) working on the venue. The goal: a smooth, good-looking venue for
quick prerendered fly-throughs and walkthroughs (the intro from the street to the hall screen, the walks to the
rooms and back), judged the way a person watching the clip sees it.

## John's rules (confirmed, don't re-litigate)
- **Plan vs photos:** data/venue/venue.json decides positions on the ground (walls, columns, bays, stairs); the
  reference photos decide anything vertical or finer (heights, dressing). Flag every conflict to John.
- Layout: the ground-floor facade is a wall of glass doors; the grand stair stands mid-reception rising north; the
  wood-slat reception sits under it; the queue is WEST of the stair; booth blocks 4 per side of the aisle (left
  JetBrains, Google Cloud, Belfius, Docker; right ING, Java, ?, Red Hat); the schedule screen is on the far north
  wall between the stairwells; no columns under the coffer.
- Motion: no pauses; already moving while looking at the sign; ~8 m/s through door and reception, ~13 m/s through
  the booths; ease only into the screen. The walk back from the rooms has no photos: plausible + heavy blur.
- Crowd: Rocketbox avatars on Rocketbox's own mocap (MIT); badges + lanyards + backpacks; **no handheld props**
  (three attempts failed); never photo cut-outs. Anti-clipping: skin to the armature, Shrinkwrap after it, verify.
  "The blurrier the crowd, the better."
- Never upload or commit the reference photos (CC BY-NC-ND / Street View) or the Slack webhook.

## Priority: what the camera actually sees (John, 16/10)
Effort goes where the fly-through and the walks are readable. Next to the camera, details matter (people, props,
badges, edges, fixings). Far away, a thing only matters if it is obviously broken from afar (a gap of sky, a
floating block, a missing wall); what is small on screen or there for a split second can be fudged. The sanity
report ranks every finding by its largest size on screen and its time in view (FIX / FUDGE; no occlusion, so
it's an upper bound); critics report near-camera problems first and drop far, fleeting nitpicks.

## The process (locked 16/10 after the forum/paper research)
1. **Build from scripts only** (headless, factory settings, `--python-exit-code 1`); change one area at a time.
2. **Sanity report must be clean** before anything is rendered: no floating objects, nothing interpenetrating,
   people >= 1 m clear of both camera paths, counts per zone. Numbers in text beat screenshots for precise geometry.
3. **Cheap views first:** single frames from the reference cameras (Workbench/EEVEE, small), the critical walk
   frames (door, steps, booth whoosh, end pose) and a top-down plan. Never queue cheap previews nobody needs now:
   Blender runs serially on one GPU.
4. **Fresh-eyes critic:** a subagent that has NOT seen the code gets only the renders, the matching photos and the
   checklist below, and answers each item yes / no / unclear with the pixel region. It may ask for extra views
   (camera position + target). "Looks fine" is not an answer. A fix that makes a view worse is reverted, not
   patched.
5. **John spot-checks** the model views beside the photos (local review page, photos never uploaded).
6. **EEVEE preview** of the clip; John reviews the motion.
7. **Cycles final only on John's go.**

## Checklist (every item comes from a past rejection; add new ones as John finds them)
Facade/outside: sign size and depth match the photo and the star is there; the camera isn't too close; the
ground floor is a wall of glass doors (count them); bollards on the road edge, not on the pavers; trees full;
road dark asphalt.
Reception: dark ceiling, white wall and palms present; queue in the belt snake, loose, not single file; the
reception camera's view not blocked by a person.
Hall: not too bright; booths on both sides where the photo shows them; booth names readable and right-sized.
Crowd: no prop in or near a hand; no badge on a back; no body part through a badge, lanyard or backpack; hand
poses varied (no two neighbours in the same pose); nobody floating or sunk in the floor; groups look organic,
not on a grid; nobody inside a wall, counter or another person; nobody inside a high-table frame; no arm into
a backpack's side; the same avatar not twice close together; nobody standing alone facing nothing; the end of the
walk thins out but isn't an empty closed hall.
Environment: nothing hovering without legs, posts or cables (trolley, planters, signs); hanging foliage cards
and thin LED strips near the camera (sparkle/shimmer); the camera not brushing a column.
Motion (clips): no jolt, lurch or tumble; nothing whips through the frame within 1 m of the lens; no flicker on
glass, metal or thin highlights; motion blur without hard edges round foreground objects.

## EEVEE final rubric (17/10; a clip must pass before a full-quality render)
Drawn from the IRPR render-quality checklist (3d.irpr.agency/guides/3d-render-quality-checklist), the Blender
manual's EEVEE shadow/light-probe notes (light leaks, shadow pool, jitter) and the V-Ray/CGArchitect animation
flicker notes. Judged on the EEVEE preview of the same walk; the automatic half is `scripts/photomatch/qc.py
<frames>`, its thresholds calibrated on the fly-through John approved (16/10), so "passes" means "at least as
clean as that".
Automatic (qc.py, all must pass):
- no pops: no frame whose change is > 3x the change around it (crowd or rooms switching visibility in view,
  lights popping)
- noise: Immerkaer sigma <= 1.5 grey levels on every frame
- breathing: the frame-wide median brightness shift <= 1.0 grey level (GI/shadows re-solving, flicker)
- blown highlights <= 2 % of a frame; crushed blacks <= 25 %
- frame count complete; the log has no "Shadow buffer full" or Python errors
Visual (contact sheet every ~0.5 s + the critical frames, judged by a fresh-eyes critic and by me):
- lighting reads as intended (not flat, not muddy), contact shadows ground people and furniture
- materials read as the real substance; no stretched, seamed or visibly tiled textures near the camera
- no light leaks in room corners, under the girders or through the stair shafts
- nothing floating, intersecting or clipping (sanity report clean; crowd clearance; the camera >= 0.45 m from
  everything)
- crowd: no foot sliding near the camera, nobody walking through anything
- camera motion smooth, no jolts; the end frame matches the published still (screen size >= the still's)
- the checklist above for every area in view

## Render notes (from the Blender forums and the manual)
- EEVEE motion blur with one step is a post-process vector blur that breaks at object borders on fast camera
  moves; more Steps (each a full scene re-evaluation, samples round up to a multiple) fix it.
- Flicker comes from thin reflections and sharp highlights: more samples on those shots, a slightly wider film
  filter, rougher materials; in Cycles, set min samples by hand and prefer 2x resolution with fewer samples then
  downscale. Cycles' temporal denoiser doesn't work with Cycles motion blur: don't use it here.
- EEVEE glass: Blended renders smoother than Dithered.
- Weak GPU (4 GB here; 17/10 research, forums + manual + bug tracker). A 1920 px frame at 64 samples with full-res
  ray tracing and 4 blur steps took ~3 min and then stalled the card (3.7 of 4 GB used, 0 % load, 7 h): never run
  a full clip without a watcher that flags a stall.
  - Measured 17/10 (room 8, 1600 px, 48 samples, 4 blur steps, crowd): --tex-limit 1024 --shadow-scale 0.5 took the
    hall/corridor frames from 20-72 s to 13-32 s, cleared every "shadow buffer full" warning, same look, noise 0.70.
    Full-quality clips use these two flags.
  - Cap texture size: EEVEE has no per-render texture limit, but the GPU texture limit preference
    (preferences.system.gl_texture_limit) caps every image uploaded; 1024 or 2048 keeps the crowd's 2K Rocketbox
    textures from filling VRAM (bug reports: 4K textures + EEVEE = out of memory where Cycles copes).
  - Build once, save the .blend (--save), render the clip in chunks of ~100 frames in fresh Blender processes:
    EEVEE's per-frame GPU memory growth is a recurring bug-tracker pattern, and a fresh process also resets a stall.
  - Motion-blur steps multiply the cost (each step re-evaluates the scene): samples are split across steps, so 4
    steps x 12 samples ~ 48 samples' quality at the price of 4 evaluations.
  - Shadows: shadow_resolution_scale below 1 is faster and soft shadows hide it; shadow steps up to 16 are cheap and
    stop light leaks. Ray tracing at half resolution (the default) is fine for rough surfaces.
  - Render small, upscale (Real-ESRGAN, e.g. realesr-animevideov3): big savings claimed by add-on authors, but the
    known risk is frame-to-frame detail shimmer: test on a short stretch with qc.py before using it.
  - Render every other frame and interpolate (RIFE/Flowframes): users report trouble with fast motion, edges and
    frame-precise events; our crowd limbs and whip turns near the lens make it risky.
  - Cycles + OpenImageDenoise for animation needs stable noise (fixed seed is not the answer: it smears) and
    hundreds of samples indoors on a weak GPU: not quicker than EEVEE here.
