# Where this stands (13/10, 22:45)

## Right now
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
  publish_renders.py joins them into `walk-phone-<n>.mp4`; cinema.js plays them on phones.
- Live on Pages since 13/10 ~19:45 (laptop walks mended, fade back, text fixes); the phone walks are committed but not pushed yet.
- **Text fixes:** the talk's summary scrolls inside the left column on laptops so the buttons stay on the cinema
  screen; programme cards shorten their title, then speakers, until they fit. `tools/ux/overflow.mjs` checks
  every talk and slot.
- WebGL page retired: `site/kino/` deleted, the venue model and credits moved to `data/venue/`.
- Serve locally with `node tools/ux/serve.mjs` (byte ranges; Python's http.server can't seek videos).
- Pushing to main deploys GitHub Pages; ask John first.

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
