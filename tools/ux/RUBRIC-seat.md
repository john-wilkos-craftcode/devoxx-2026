# Devoxx cinema, the seat: UX review rubric

Used by the review agents that score the seat view on laptops (`site/`, from screenshots taken by
`shoot-seat.mjs`). A fresh agent each round, with no stake in the design. The target is **9/10 on every viewport**,
which this rubric defines as: heuristics total ≥ 36/40, every requirement met, and no P0 or P1 issue left.

Sources the rubric is built from:
- Nielsen's 10 usability heuristics, each scored 0-4 with the strict per-score criteria of the practitioner
  heuristics scoring guide (a 4 is "genuinely excellent", not "good enough"): totals 36-40 excellent, 28-35 good,
  20-27 acceptable, below that poor.
- Nielsen's severity scale, as P0 (blocks the task) to P3 (polish). Tiebreak: would someone ask for help over it?
  Then it's at least P1.
- For the diegetic part (the UI lives on objects in the room), the game-usability heuristics of Desurvire et al.
  (HEP, 2004; PLAY, Desurvire & Wiberg 2009), which are the ones used to judge diegetic interfaces: the player always
  knows where they are and what they can do; controls follow conventions; the interface is unobtrusive and doesn't
  break immersion, but immersion never costs the player the ability to act.

## The site
Every Devoxx Belgium 2026 session (205 talks), summarised, inside a photorealistic render of the Kinepolis venue. You
pick a talk on a screen in the hall, walk (a short video) to a seat in the room where it was given, and sit down. This
review is about **the seat, on laptops and desktops**.

## The brief (the owner's words, condensed). Each is pass/fail.
 R1 The movie screen is not busy: the YouTube player takes up as much of it as possible; the rest of the screen holds
    only the talk's title, who gives it, and why it's worth our attention.
 R2 Everything else (the summary, the key points, the takeaways, jumping to parts of the talk) is on a laptop on your
    lap, and it is readable there.
 R3 The laptop can be opened and closed. Closed, its lid shows a sticker (a head with a coffee cup and wifi waves).
 R4 With the laptop open you can still see the movie screen (the laptop may overlap its edge a little).
 R5 You can jump through the talk from the laptop while the talk plays on the movie screen: both at the same time.
 R6 You can zoom into the laptop and make it full screen, and get back.
 R7 It feels like real life (diegetic), but never at the cost of usability.
 R8 The YouTube video itself can go full screen, and come back.
 R9 While the talk plays, the text beside the video is gone (animated away) and the video takes as much of the movie
    screen as it can; reading on the laptop, its tabs and headers get out of the way (away on scroll down, back on
    scroll up); the UI disappears when not in use; the summary is formatted to be legible and pleasant.
 R10 Closing the laptop moves the view in on the movie screen: the recording fills the window, with just a bit of the
    laptop and its "Open the laptop" button below; opening it pulls back to the usual view. Captions (CC) show.

## Standing notes for reviewers
- The laptop is a **placeholder drawing** for now. It becomes a photoreal render of a Dell Precision 5570 (silver lid,
  black keyboard deck, thin bezels) with the sticker on its lid. Judge its placement, size and behaviour, not its art.
- Black margins round the room (sides, bottom) are where the room render doesn't reach yet; the stills will be
  re-rendered wider and taller. Ignore them.
- The walk from the hall to the seat is skipped in the screenshots.
- Headless screenshots: the YouTube player is real (it plays); hover states are not shown. The test robot scrolls an
  element into view before clicking it, so a list may be scrolled a little in the shots after a click; a person
  clicks what they see.

## Screenshots, per viewport (1440x900, 1280x720, 1920x1080)
  1-seat                   just sat down: laptop open, recording not started (our poster: "Play the talk")
  2-other-tab              another tab of the notes
  2b-summary-reading       the Summary tab, scrolled down a little: the laptop's header, tabs and bar fold away
  3-jumped                 after clicking a chapter: the recording plays (theatre: the column beside it drifts off,
                           the picture takes the screen's full height)
  4-closed                 the laptop closed: the view moved in on the film (tools/ux/closed.mjs shoots the move)
  5-fullscreen             the laptop zoomed to fill the window
  6-fullscreen-jumped      a chapter clicked while full screen
  7-back-from-fullscreen   Esc pressed
  8-no-recording           a talk that has no recording yet
  9-keyboard               three Tab presses after load (focus visibility)
  11-video-fullscreen      the recording full screen (the browser's), with the page's own control bar
  10-player-blocked        "Play" pressed while YouTube is blocked (the console errors in log.txt are this, on purpose)
  log.txt                  console errors
  (tools/ux/closed.mjs: the lid closing and opening, mid-move too; tools/ux/cc-probe.mjs: captions land in view)

## Score each heuristic 0-4 (be strict)
 H1 Visibility of system status (what's playing, which chapter, open/closed/zoomed state, where focus is)
 H2 Match with the real world (a cinema seat, a laptop on your lap: does it behave like one? plain language)
 H3 User control and freedom (open/close, zoom in/out, back to the programme, Esc; nothing traps you)
 H4 Consistency and standards (controls look and work alike; video and laptop conventions respected)
 H5 Error prevention (nothing covers the player's controls; no accidental lid-close; no dead ends)
 H6 Recognition rather than recall (every action visible where you'd look for it)
 H7 Flexibility and efficiency (keyboard, shortcuts, jumping chapters fast, next/previous)
 H8 Aesthetic and minimalist design (the movie screen is calm; the laptop is focused; hierarchy is clear)
 H9 Recognise and recover from errors (no recording, video won't load: says so and offers a way on)
 H10 Help (the view explains itself the first time: you know the laptop is yours to use)

## Output (under 600 words)
- Per viewport: overall score /10 (9 = I'd ship it; 10 = best-in-class) and the H1-H10 total /40.
- R1-R7 pass/fail.
- The issues blocking a 9, ranked, each tagged P0-P3: what's wrong (viewport, screenshot, where), why it matters,
  and a concrete fix. Be blunt; don't praise. Judge only what you see.

## Scores so far
| round | 1440x900 | 1280x720 | 1920x1080 | main change |
|---|---|---|---|---|
| 1 | 7 (28/40) | 6 (26/40) | 7 (28/40) | first mock: player + column on the screen, notes on the laptop, open/close/zoom |
| 2 | 8 (32/40) | 7 (31/40) | 8 (32/40) | own poster, title fitting, controls on the laptop, keys, YouTube's chapters |
| 3 | 8 (34/40) | 8 (32/40) | 8 (34/40) | Overview tab with the chapters, key hints, keys sheet, failure state, first-run note |
| 4 | 8 (35/40) | 8 (34/40) | 7 (33/40) | YouTube chrome off: the laptop has the transport (scrubber, chapter menu, CC, sound) |
| 5 | 7 (30/40) | 8 (33/40) | 8 (35/40) | loading/press-play overlay, list-only scrolling, screen fixed when the lid closes (1440: YouTube frame failed to load in the run) |
| 6 | 8 (34/40) | 8 (33/40) | 8 (35/40) | 10 s fallback, compact chapter button, prev/next icons, tighter small laptop |
| 7 | 8 (35/40) | 8 (33/40) | 9 (36/40) | no More pills, gist in two lines, lid Play/Open, Try again, full-screen fits all chapters |
| 8 | 8 (35/40) | 9 (36/40) | 9 (37/40) | first-run note back, no-recording panel fits, gist more/less, one clock format |
| 9 | 9 (36/40) | 8 (35/40) | 9 (36/40) | compact laptop by its own size, all chapters in full screen, tab kept, lid controls clear of the sticker |
| 10 | 9 (36/40) | 9 (36/40) | 9 (36/40) | playing chapter kept clear of the fade, one-line gist on small laptops, tab order: poster first. UX target met |
| r1 | 9 (36/40) | 9 (36/40) | 9 (36/40) | real renders in (laptop + wide room stills); full-screen video (R8) |
| r2 | 9 (36/40) | 9 (36/40) | 9 (37/40) | Z zooms the laptop, F full-screens the video |
| r3 | 9 (37/40) | 9 (36/40) | 9 (37/40) | R9: theatre while playing, chrome folds while reading, a readable summary |
| r4 | 8 (35/40) | 8 (34/40) | 8 (35/40) | R10 first cut: closed lid moves the view onto the film; captions uncropped (sticker out of view: R3 fail) |
| r5 | 9 (37/40) | 9 (36/40) | 9 (37/40) | sticker re-rendered near the hinge, buttons on the lid, the recording's bar in the big view, poster names the talk |

Art (stage 2), overall per viewport 1440 / 1280 / 1920:
| round | art | main change |
|---|---|---|
| a2 | 5 / 4 / 5 | first laptop render (lit like a product shot) |
| a3 | 6 / 6 / 6 | lid in the room's light, wide stills, glass and projection CSS |
| a4 | 6 / 5 / 6 | screen glow on the keys, darker world, notes overscan |
| a5 | 6.5 / 6 / 6.5 | neutral Titan Gray, black backlit keys, carbon weave, spill on the seats |
Still open (a5): notes read as a panel (clip to the quad with bezel showing, glass layer), info column too flat a blue,
no glints on the chamfers, a radial (CD-like) lid highlight from anisotropy, 1280 shows one key row, 14 frames is coarse
and the notes pop in, sticker reads grey and soft.

## Stage 2: diegesis (after the laptop and the wide room stills are rendered)
Once UX is at 9, the stand-in laptop is replaced by the Blender render and the room by wider stills. Then two fresh
reviewers each round: the UX reviewer above (UX must stay at 9 or better: any drop is a regression to fix first) and an
art director, who scores /10 per viewport on:
 A1 The laptop is believably a Dell Precision 5570 (proportions, Titan Gray lid, black carbon deck, thin bezels,
    keyboard, the shiny ring logo) seen from the eyes of someone sitting with it on their lap.
 A2 Its light belongs to this room: lit by the big screen ahead and the house lights, glints on its chamfers, its own
    screen's glow on the keys; nothing looks pasted on.
 A3 The sticker reads as a real die-cut vinyl sticker on aluminium: the white border, a gloss that differs from the
    lid, a hairline edge, lying flat in perspective.
 A4 The notes on the laptop's screen read as a lit display behind glass (not a web page stuck on); the recording on
    the cinema screen reads as projected.
 A5 The opening and closing motion and the zoom feel physical.
 A6 The room round it: no seams between the stills, the laptop and the HTML; the framing feels like sitting there.
Target: art 9 on every viewport, UX still ≥ 9.
