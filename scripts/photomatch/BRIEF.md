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

## Render notes (from the Blender forums and the manual)
- EEVEE motion blur with one step is a post-process vector blur that breaks at object borders on fast camera
  moves; more Steps (each a full scene re-evaluation, samples round up to a multiple) fix it.
- Flicker comes from thin reflections and sharp highlights: more samples on those shots, a slightly wider film
  filter, rougher materials; in Cycles, set min samples by hand and prefer 2x resolution with fewer samples then
  downscale. Cycles' temporal denoiser doesn't work with Cycles motion blur: don't use it here.
- EEVEE glass: Blended renders smoother than Dithered.
