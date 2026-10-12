# Where this stands (12/10, 17:00)

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
     Still to do: the carpet's pebbly pattern is weaker than the photo's; fewer ivy clumps.
   - upstairs foyer: as before (sloped ceiling, LED lines, track spots, screen between dark columns,
     red side portals), but the tensile funnels are white fabric lit blue this year, not red
   - entrance: navy walls, blue "uitgang zaal 6/7" signs, glass front, white desks, stanchions
   - side stair and corridor (older references, no 2026 photos): speckled grey treads, blue-lit wall,
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
2. Render the Room 8 walk + seat still, build a test page: <video> transitions, stills, and the HTML
   programme/talk pinned onto the screens with a CSS perspective transform from shots.json.
3. Then all 14 rooms (~7 h of GPU, overnight), and retire the WebGL version.
4. Done: the "What we heard this week" recap (`data/recap.json`) is live.
5. Later: slide-by-slide navigation (`scripts/detect_slides.py` works; prefers H.264).
