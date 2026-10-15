# Where this stands (15/10)

## Right now: the photo-matched venue and the intro fly-through (15/10)
A new modelling approach replaces build_scene.py's by-eye venue for the walk from the street to the hall screen:
- **Photo match** (`scripts/photomatch/`, `scripts/blender/photomatch_scene.py`, `pm_lib.py`, `pm_areas/`): every
  reference photo (C:\Users\wilkojo\Downloads\reference, copied to data/references/img/site-2026/, gitignored) has a
  solved camera (calib.py: vanishing lines, fSpy-style; resect.py: from plan points) in data/photomatch/cameras/ and
  cal/; each area is modelled in venue coordinates (data/venue/venue.json's frame) over its photos. Review page:
  `python3 scripts/photomatch/page.py --open` -> C:\Users\wilkojo\kino-renders\photomatch\index.html (local only, the
  photos are CC BY-NC-ND / Street View). Edge fit 1-2 px (facade, upstairs, Hollywood), ~4.5 px (telephoto side shots).
- **Plan vs photos rule:** the plan decides positions on the ground; the photos decide anything vertical or finer.
  Decisions John confirmed are listed on the review page (no columns under the coffer, facade heights, a wall of doors,
  reception under the grand stair with the queue west of it, booth blocks 4 per side, screen on the north wall
  between the stairwells).
- **Unified venue + fly-through** (`render.sh venue`, `pm_areas/venue.py`, route and speeds in
  data/photomatch/walk.json): outside -> a door west of the grand stair -> past the queue -> down the hall steps ->
  the aisle between the booth blocks -> the schedule screen (hall_screen.py: the old screen, plants, ivy, totem; the
  walk lands on the old hall still's pose). Phones: `--variant phone`, the same path drifting onto the totem.
  ~12.3 s + 1 s hold; ~8 m/s, ~13 m/s through the booths (John liked the motion; asked a smidge faster). EEVEE
  previews: `build/photomatch/preview.sh` -> venue/preview-laptop.mp4 / preview-phone.mp4; motion blur full frame.
- **Crowd** (`pm_areas/crowd*.py`, `scripts/fetch_rocketbox_anims.py`): Rocketbox avatars with Rocketbox's own mocap
  (MIT). John OK'd poses/models. No handheld props (three attempts failed); badges + lanyards + a CC-BY Oakley
  backpack (data/models/backpack_oakley, credited in THIRD_PARTY.md) being fitted with the anti-clipping recipe
  (skin to the armature, Shrinkwrap after it, Mask the body underneath). Not placed in the venue yet: John reviews
  close-ups first (C:\Users\wilkojo\kino-renders\photomatch\crowd\).
  Crowd state at the stop (15/10): backpack decimated to 8k faces, straps removed, skinned + shrinkwrapped (6 mm);
  lanyard skinned + shrinkwrapped (4 mm); badge rigid on Spine2; 0 mm penetration measured on the test set. Open: the
  body Mask under the pack cut too big a patch (switched off, MASK_UNDER_PACK = False in crowd_wear.py, not re-rendered),
  the lanyard cord isn't visible in the close-ups (check at 1 m), the reverse check (body into pack) needs a sealed
  collision shell, crowd_place.py (placement) doesn't exist yet.
- **Stopped 15/10 ~17:05 (all Blender killed on purpose):** preview-laptop.mp4 on the review page is the earlier
  16 s timing; the current 12.3 s timing with the full-frame shutter (1.0) has NOT been previewed yet, and
  preview-phone.mp4 is the older ~24 s one. Re-run (one at a time, nothing else on the GPU; ~15-20 min each):
  `scripts/photomatch/render.sh venue --engine eevee --walk anim --samples 16 --width 960` then
  `ffmpeg -y -framerate 30 -i C:/Users/wilkojo/kino-renders/photomatch/venue/walk/anim/f_%04d.png -c:v libx264
  -pix_fmt yuv420p -crf 20 -movflags +faststart .../venue/preview-laptop.mp4` (paths via /mnt/c in WSL); the same
  with `--variant phone --width 540` and walk-phone/anim -> preview-phone.mp4. Empty the anim folders first (stale
  frames from the killed runs are in them). Then `python3 scripts/photomatch/page.py --open`.
- **Next, in order:** (1) the previews above; (2) crowd close-ups again with MASK_UNDER_PACK = False (the 22 in
  crowd/check/ still show the mask hole), check the lanyard cord is visible at 1 m, then show John; (3) crowd_place.py:
  queue west of the stair, booth fronts and the area below the steps dense, sparse towards the screen, >= 1 m clear of
  the camera, phone path too; add "crowd" to venue.py PARTS; (4) Cycles renders of both fly-throughs (ask John first);
  (5) the walk back from the rooms (no photos: plausible + heavy blur); (6) wire the new intro walk and hall stills into
  the cinema page (the screen moved: new shots.json quad, front layer from hall_screen.FRONT).

## Before that: the seat on laptops (14/10 afternoon)
- The cinema screen carries the YouTube player (own poster, YouTube's chrome off, cropped so its overlays never show)
  with only the title, speakers and "Worth your time if" beside it. The notes are on a Dell Precision 5570 on your lap
  (scripts/blender/build_laptop.py, a separate transparent render laid over the room like a first-person view model):
  Overview (gist + chapters), Summary, Key points, To try, and a transport (scrubber with chapter ticks, chapter menu,
  CC, sound, video full screen). Lid opens/closes (14 frames, sticker on the lid, Play/Open on it), Z zooms the laptop
  to fill the window with the recording moved onto it, F full-screens the video with the page's own bar.
  Keys K [ ] arrows C M F Z L ? Esc. Chapters are YouTube's own where it has them (scripts/fetch_chapters.py).
- Seat stills are wider and taller than the walk (same camera; the walk's frame measured inside them, "inner" in
  shots.json): render with scripts/blender/render_seat_laptop.sh (~8 min a room; the laptop ~6 min).
- UX: 9/10 on 1440, 1280 and 1920 (tools/ux/RUBRIC-seat.md, shoot-seat.mjs; 12 rounds). Art: 6-6.5/10 after 3
  rounds; the open items are listed at the end of RUBRIC-seat.md. Phones are unchanged (door totem).

## Before that
- **All eight rooms (3-10) rendered and published** into `site/cinema/media/` (stills, cut-out layers, walks).
  Rooms 3 and 6 re-rendered up to their door after their phone totems were moved: room 3's stood over the west
  stairwell (its phone still was solid blue), room 6's against the railing round a floor opening. build_scene.py
  now moves a totem to the number-panel side of its door when anything stands there.
- **The walks are fixed in post, not re-rendered** (John: "tired of rendering"). The stair climb's camera tumbles
  (its euler rotation wraps past ±180° under motion blur), so publish_renders.py cuts it: hall → stairwell, a
  dip to black, the corridor upstairs (without the rest at the top). One-frame smears elsewhere are blended
  out. The way back is a fade through black on the page, no reversed clip any more.
  If the walks are ever rendered again: make the camera's euler compatible frame to frame
  (`rot.to_euler("XYZ", previous)`) in `keyframe_segment`, then the stair can go back in.
- **Phones get their own portrait walks** (`scripts/blender/render_phone_walks.sh`, ~1 h 50 for all eight rooms):
  the laptop walk cropped to portrait looked broken. From the hall totem still the camera steps back and turns
  away (left across the hall for west rooms; right for east, after first stepping clear of the stairwell glass
  beside the totem, which otherwise fills the frame as a blur), a dip to black, then a push-in on the room's door
  totem that settles on its still. 540x1170, eulers kept compatible frame to frame (no smears).
  publish_renders.py joins them into `walk-phone-<n>.mp4`; cinema.js plays them on phones. Once the walk settles,
  cinema.js zooms the still by hand onto the totem until its screen nearly fills the phone (8 px of room left on
  the tight side) and lays the talk out for that bigger screen: ~374 css px wide on a 390 px phone, was ~297.
- Live on Pages: laptop walks mended, fade back, text fixes (13/10 ~19:45), phone walks (13/10 ~23:00).
- **Text fixes:** the talk's summary scrolls inside the left column on laptops so the buttons stay on the cinema
  screen; programme cards shorten their title, then speakers, until they fit. `tools/ux/overflow.mjs` checks
  every talk and slot.
- WebGL page retired: `site/kino/` deleted, the venue model and credits moved to `data/venue/`.
- Serve locally with `node tools/ux/serve.mjs` (byte ranges; Python's http.server can't seek videos).
- Pushing to main deploys GitHub Pages; the page is unreleased, so push every change for John to review live.

## The cinema page (`site/cinema/`), status
- Diegetic UI pinned onto Blender stills with a CSS matrix (2D when square on, so text is sharp): programme on
  the hall screen (laptop) / hall totem (phone); talk on the cinema screen from a seat (laptop) / on the totem
  at the room's door under a backlit room-number plate (phone).
- 19 review rounds with a UX judge and an art-director judge (fresh agents each round, screenshots from
  `tools/ux/shoot.mjs`): plateau at UX ~8 (laptop) / 7.5-8.5 (phone), art ~7 / 7-8. Score history in
  `tools/ux/RUBRIC.md`. What the art judges keep asking for: real cinema seats, real foliage, the screen
  lighting the room, more hall around the hall screen (conflicts with legibility at 1280).
- Main site's "Enter the cinema" link points to `cinema/`. The WebGL `site/kino/` is retired (13/10).

## Earlier (12/10)
Done:
- All 205 sessions summarised (168 from Whisper transcripts, 37 from abstracts: no recording yet).
- Flat site and the WebGL cinema (`site/kino/`) live on GitHub Pages.
- Blender pipeline works end to end: `scripts/blender/build_scene.py` builds the venue from
  Ghost Light's data, keyframes the walk to a room and exports where the LED wall and cinema
  screen land per shot (`shots.json`). Cycles on the A1000: ~25 s per 1080p still, ~30 min per walk.
  Run from WSL against Windows Blender 5.2 (see the docstring); renders in C:\Users\wilkojo\kino-renders.

How we get to photoreal (revised 12/10, after reading up on agent-driven Blender work):
- Calibrate against the photos, not by eye from memory. Every area gets a reference camera placed
  where a reference photo was taken (`data/references/cameras.json`, rendered with
  `--render ref:<name>`), and `scripts/compare_render.py` puts render and photo side by side with
  luminance and colour stats. Materials and light are tuned on that matched view, then carried over to
  the real shots. One change at a time, at look-dev quality (960 px, 64 samples), then final quality.
- A fresh reviewer agent (no stake in the build) critiques each render/photo pair and lists the
  biggest realism gaps; fix those first.
- Real CC0 PBR textures (ambientCG, Poly Haven; `scripts/fetch_textures.py`, gitignored) mapped in
  world space, so the batched boxes need no UVs. Procedural detail on top where no texture fits (the
  50 cm carpet tiles, the acoustic spray).
- Physically based light: fixtures shaped like the real ones (hexagon LED panels, downlights, track
  spots), colour temperature from the photos, haze only inside the auditoriums.
- Small-scale realism: bevelled edges, plinths, speakers and signs on columns, curtain folds, glass.
- Camera and post like a phone photo: real focal length, AgX, a little bloom and vignetting.

Next:
1. Art pass on the camera route so it matches the reference photos. These are now 2026 photos from
   the official Devoxx Flickr albums, listed with captions in `data/references/references.json`;
   `python3 scripts/fetch_references.py` downloads them into `data/references/img/` (gitignored,
   CC BY-NC-ND) with one contact sheet per area. The old references were wrong: what we built as the
   ground-floor exhibition hall (sloped ceiling, screen between columns, funnel, red portals) is the
   upstairs foyer. Downstairs, where the booths are, is the **Hollywood room**:
   - Hollywood room (start of the walk): calibrated against `hollywood-empty.png` (ref camera
     `hollywood`); per-band luminance within ~0.03 of the photo. White drop ceiling at 3 m with
     hexagon LED panels (area light under each) and downlights (narrow spots: the pools on the carpet),
     the blue-lit coffer at the entrance end, higher entrance ceiling with track spots and black panels.
     Carpet: ambientCG Carpet016 fibre, 50 cm tiles laid quarter-turned with per-tile shade and sheen.
     Curtains: pleated meshes with UVs and Poly Haven "terlenka". Frosted glass stairwells with alu
     mullions, speakers and plinths on columns, extinguishers, exit signs, trusses, translucent ivy.
     Floor-1 cinema walls and rakes stop above the drop ceiling over the room (Ghost Light stacks the
     floors too close). Post: bloom, slight dispersion, vignette; AgX Medium High Contrast, -0.9 EV.
     Reviewer scores (a fresh agent each round, render vs photo, out of 10):
       round                      matched view  opening shot  to stairwell  stair foot
       1 first pass                    4             3             3.5          -
       2 textures, real lights         5             4             5            2
       3 stair rebuilt, dirt           4.5           4             5            3
       4 black entrance ceiling        5             4             4.5          3
     Plateaued around 4-5. What the reviewers keep naming is mostly beyond procedural boxes: cloth-
     simulated curtains, carpet with large-scale wear and traffic paths, ceiling clutter (sprinklers,
     diffusers, signs), real thickness and edge wear everywhere. Some of their fixes were already in
     (no world fill, nosings, bevels), which says the look, not the settings, is what's missing.
   - upstairs foyer: as before (sloped ceiling, LED lines, track spots, screen between dark columns,
     red side portals), but the tensile funnels are white fabric lit blue this year, not red
   - entrance: navy walls, blue "uitgang zaal 6/7" signs, glass front, white desks, stanchions
   - side stair (scored 2/10, next up) and corridor (older references, no 2026 photos): speckled grey treads, blue-lit wall,
     one grey rail, red door at the top; vaults, square columns, blue LEDs, orange backlit poster
     boxes, blue "uitgang zaal" signs
   - room door: red portal + ring handles, big white room numeral with red/orange streaks,
     LASER ULTRA board, schedule screen on a stand, rope stanchions (no 2026 photo of this yet)
   - auditorium: black room, star-field ceiling spots, truss light towers either side of the stage,
     blue-grey seats, aisle steps with red LED edge lights, "#DEVOXX" in real type with an orange X
     standing on the stage floor (replace Ghost Light's box letters)
   Fixed on the way: a Ghost Light collider was built as a 6 m wall across the foot of each side
   stair, so the walk went through it (the WebGL version has the same bug).
   Look-dev: `--render walk@40+46` renders single frames of the walk.
2. Room 8 walk and the test page (12/10, in progress):
   - corridor and auditorium dressed after the 2026 photos (sloped white ceiling planes with blue LED
     lines and track spots, navy walls, poster boxes; star-field ceiling, truss light towers, red aisle
     LEDs, "#DEVOXX" in Archivo Black with an orange X)
   - `site/cinema/`: the stills and walk clips with the programme and the talk as HTML pinned onto the
     screens by a CSS matrix3d from `shots.json` (which now also carries each screen's size in metres).
     Rooms without a rendered walk open their summary on the hall screen. Phones get the panels as a
     sheet, like the WebGL version.
   - `scripts/blender/publish_renders.py <render dir>` turns a render folder into `site/cinema/media/`
     (JPEG stills, walk clip forward and reversed, merged shots.json).
   - Final walk: 1080p at 64 samples, about a minute per frame on the A1000.
3. Then all 14 rooms (~7 h of GPU, overnight), and retire the WebGL version.
4. Done: the "What we heard this week" recap (`data/recap.json`) is live.
5. Later: slide-by-slide navigation (`scripts/detect_slides.py` works; prefers H.264).
