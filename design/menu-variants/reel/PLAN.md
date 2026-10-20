# reel: the projection booth

Concept: the week is a reel of film. 8 verdicts = 8 frames on a strip with sprocket holes, between a countdown leader
(the intro) and an end-credits frame (Watch first). The strip runs through a projector gate in the centre; the frame
in the gate is the only one lit. Search and sort reorder the strip and the talk list; the programme is the schedule.

## Palette (named hexes)
- Screen blue   #0B1440  the canvas, matches the hall screen; also the light coming through sprocket holes
- Film base     #04081F  the strip itself, darker than the screen so it reads as stock
- Unexposed     #131C55  unlit frame face
- Lamp          #FFF1D2  the lit frame in the gate (warm projector white); text on it is Screen blue
- Leader orange #F6921E  Devoxx orange: the X, the countdown, the focus ring, "side A" of a debate
- Dye cyan      #7FD3EA  "side B" of a debate and the links
- Ash           #A9B4E0  secondary text on dark (contrast >= 7:1 on #0B1440)

## Type (Archivo, one family, the width axis does the roles; the real page uses Archivo)
- Title card: Archivo wdth 62, wght 800, 30/30 (frames), 44/42 (versus question), sentence case
- Chapter / consensus: wdth 100, wght 500, 19/26
- UI + body: wdth 100, wght 500-700, 15/21 (min 14)
- Numbers (signals, times): tabular figures, wdth 100, wght 700
Scale: 14 / 15 / 19 / 30 / 44. Left-aligned except the leader and versus cards, which are centred like title cards.

## Wireframe 980x613
```
+--------------------------------------------------------------------------------+
| DEVOXX 2026 Mostly about coding agents: how to check,   [search........] All talks|
| review and contain them.                    Watch first | Programme | Text ver.|
|  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  |
|  | leader |  |  v2  dim |   [   v3  LIT  ]    | v4  dim |  | v5 dim |         |
|  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  ::::  |
|  <  frame 3 of 8  >                                                            |
|  Consensus sentence (19px)                         | WATCH FIRST (credit)       |
|  Versus: the debate question   [Open the debate]   | pick title, speaker, why   |
|                                                    | views / like rate / hearts |
+--------------------------------------------------------------------------------+
```
Talks/search mode: strip shrinks to a ribbon (reordered by hits), below it a sortable table
(title+speakers | views | like rate | hearts). Programme mode: ribbon + day tabs + time/room/title rows.
Versus: the lit frame opens like a projection (clip-path from the gate to full canvas): consensus on top,
question centred, side A | side B with who and talks.

## Wireframe 340x690
```
+----------------------+
| DEVOXX 2026   Text   |
| [search............] |
| All talks|Programme|W|
| ::::::::::::::::::: |
|  |dim| [ LIT ] |dim| |
| ::::::::::::::::::: |
| frame 3 of 8         |
| consensus            |
| versus [Open debate] |
| WATCH FIRST          |
| pick + signals       |
+----------------------+
```

## Signature moment
Drag / wheel / arrow the strip: it runs through the gate. The frame in the gate flips from dark stock to full-bright
lamp white with a tiny gate weave (about half a pixel, 8 fps) and the chapter changes beside it with a claw click
(a 2px vertical step of the whole strip), like threading a projector by hand. Release and it settles on the nearest
frame. Reduced motion: frames snap, no weave, no step, no clip animation.

## AI-tells check
- Near-black + one neon: no. Ground is the hall-screen blue, the lit frame is warm white, two dyes (orange, cyan) have jobs.
- Cream + serif + terracotta: no serif; the warm white is lamp light, used only for the lit frame.
- ALL-CAPS tracked eyebrows: none. Labels are sentence case; "Watch first" is a credit heading, not an eyebrow.
- Fade-slide-up everywhere: none. Motion only answers drag, wheel, key, click.
- One word in another colour: none (the orange X of the DEVOXX wordmark is the brand's own rule).
- Mono for data labels, "A · B · C" strings, "->" on buttons: not used. Numbers are tabular Archivo.
- Cards: the frames are film frames of different content (leader, verdict, credits), not identical cards.
Revision made while planning: first draft had a "countdown" decoration on every frame; kept it only on the leader.

## Critique log
(see bottom, appended per iteration)

### Iteration 1 (first build)
Scores: concept 8, craft 6.5, typography 8, motion 7, fit 8, clarity 7.5. Fixes: panel grid overflowed (nowrap titles widened
the grid and the focus scrolled the menu): minmax(0,1fr) + scroll guard; the debate overlay showed only 2 of 3 sides (verdict 2
has three): render all sides; credits rows overlapped: one-line titles; empty gap in the verdict panel: debate teaser
(first sentence + who for every side); phone panel overlapped: row sizing; phone hides teaser so the pick shows.
### Iteration 2-3
Scores: concept 8.5, craft 8.5, typography 8.5, motion 8, fit 9, clarity 9 (avg 8.6). Critic: lower half is a fairly
conventional two-column UI; the gate is the only cinematic thing, so keep it strong; phone fold hides the pick partly;
arrow stepping used the in-flight position (fixed: steps from the target).
### Iteration 4 and accessory pass
Added thin-vote marking on phone (orange rate + legend). Removed one accessory: the velocity motion blur (invisible at real
speeds, costs paint). Final: concept 9, craft 8.5, typography 9, motion 8.5, fit 9, clarity 9 (avg 8.9).
