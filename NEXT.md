# Where this stands (13/10, 11:00)

## Right now
- **Render queue running** (started 13/10 10:15, ETA ~18:30): `scripts/blender/render_rooms.sh` renders
  the hall stills, both shared walk halves (walk-a-east/-west) and, per room 3-10, the seat still + cut-out
  layer, the phone door still and the room's walk half (walk-b-N), into `C:\Users\wilkojo\kino-renders\final`,
  then runs `publish_renders.py` into `site/cinema/media/`. Log: `final/render_rooms.log`. Restartable: rooms
  already done are skipped. It waits for any running Blender, so never start a second Blender meanwhile
  (4 GB GPU).
- **Not pushed.** Pushing to main deploys GitHub Pages; ask John first.

## When the queue is done
1. Serve `python3 -m http.server 8765 -d site`, open /cinema/, check the walk videos there and back on laptop
   and phone (known risk: on phones the landscape walk is cropped to portrait and its first frame doesn't match
   the totem shot; the phone walk stops at the door via `door_frame` in shots.json).
2. Rerun `node tools/ux/shoot.mjs tools/ux/out/rN` and the two judges (see `tools/ux/RUBRIC.md`) once with
   real walks and all rooms orange.
3. Ask John: push? And whether to try real seat/plant 3D models (CC0 or bought) to get past the art
   plateau.

## The cinema page (`site/cinema/`), status
- Diegetic UI pinned onto Blender stills with a CSS matrix (2D when square on, so text is sharp): programme on
  the hall screen (laptop) / hall totem (phone); talk on the cinema screen from a seat (laptop) / on the totem
  at the room's door under a backlit room-number plate (phone).
- 19 review rounds with a UX judge and an art-director judge (fresh agents each round, screenshots from
  `tools/ux/shoot.mjs`): plateau at UX ~8 (laptop) / 7.5-8.5 (phone), art ~7 / 7-8. Score history in
  `tools/ux/RUBRIC.md`. What the art judges keep asking for: real cinema seats, real foliage, the screen
  lighting the room, more hall around the hall screen (conflicts with legibility at 1280).
- Main site's "Enter the cinema" link points to `cinema/`. The WebGL `site/kino/` is still there; retire it
  once the cinema page ships.

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
