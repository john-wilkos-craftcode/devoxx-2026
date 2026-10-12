# Where this stands (12/10, 17:00)

Done:
- All 205 sessions summarised (168 from Whisper transcripts, 37 from abstracts: no recording yet).
- Flat site and the WebGL cinema (`site/kino/`) live on GitHub Pages.
- Blender pipeline works end to end: `scripts/blender/build_scene.py` builds the venue from
  Ghost Light's data, keyframes the walk to a room and exports where the LED wall and cinema
  screen land per shot (`shots.json`). Cycles on the A1000: ~25 s per 1080p still, ~30 min per walk.
  Run from WSL against Windows Blender 5.2 (see the docstring); renders in C:\Users\wilkojo\kino-renders.

Next:
1. Art pass on the camera route so it matches the reference photos (they are in the scratchpad of
   the 12/10 session; sources: game.devoxx.be/references.html and the After Dark repo's
   media/other-images/CAPTIONS.md):
   - hall: sloped ceiling with beams, visible track spots and LED lines, raised screen between
     square columns, red tensile funnel, blue glass doors, red side portals, stacked chairs;
     camera from the photo's viewpoint
   - side stair: speckled grey treads, blue-lit wall, one grey rail, red door at the top
   - corridor: vaults, square columns, blue LEDs, orange backlit poster boxes, blue "uitgang zaal" signs
   - room door: red portal + ring handles, big white room numeral with red/orange streaks,
     LASER ULTRA board, schedule screen on a stand, rope stanchions
   - auditorium: black room, blue-grey seats, slatted back wall, lectern, "#DEVOXX" in real type
     with an orange X (replace Ghost Light's box letters)
2. Render the Room 8 walk + seat still, build a test page: <video> transitions, stills, and the HTML
   programme/talk pinned onto the screens with a CSS perspective transform from shots.json.
3. Then all 14 rooms (~7 h of GPU, overnight), and retire the WebGL version.
4. Done: the "What we heard this week" recap (`data/recap.json`) is live.
5. Later: slide-by-slide navigation (`scripts/detect_slides.py` works; prefers H.264).
