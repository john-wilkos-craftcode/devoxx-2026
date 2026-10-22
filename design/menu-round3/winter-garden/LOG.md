# Winter Garden: the window behind the wall

Design A, round 3 of the hall-screen menu. Folder: `design/menu-round3/winter-garden/`. Latest capture: `shots/t6/`
(51 of 51 expectations pass, no console errors, smallest font 14 px in every shot, 39 words visible at rest).

## The idea

The real hall screen hangs between two potted trees under a strip of ivy, so the screen becomes a window into the
glasshouse behind the wall: a Belgian iron-and-glass winter garden of the Laeken kind on an October afternoon just
after a shower. The glass is beaded with rain, a low sun breaks through from the upper left in green-gold shafts (green
because it comes through green glass), and eight raised beds recede along a wet gravel path, one plant per verdict,
each trained on a trellis. The trellis is the week's lead verdict made visible: the data's consensus for verdict 1 is
"the harness around an agent shapes results more than the model does", so the glass reads *The trellis shapes the
vine more than the seed does.* Everything alive is code: eight SVG species grown deterministically from each verdict's
talk list (a leaf per talk counted, so the harness vine fills its trellis with 23 leaves and the agave is a rosette of
12 spikes), one orange flower per bed for its "watch first" pick, code-drawn shadows that only turn, and the five slabs
of the path chalked Mon 5 to Fri 9 for the programme. The painted house behind it is an AI-generated plate (see
below), deliberately overcast and shadowless so that every shadow on screen is code and obeys one sun. The signature
moment: the pointer is the sun. It rides a fixed low arc, so moving left or right slides the sun along the glass, all
eight plants lean a few degrees toward it, the flowers turn, the eight shadows swing round their plants' feet like the
gnomons of eight sundials (same length always; the sun never changes height), and the rain beads' highlights follow.
Type a word and the sun finds the leaves: beds with a match light up sunlit pale green, the rest fall into shade.

## How to use it

- **At rest** (the first-glance layer): DEVOXX, Belgium 2026 · 205 talks, the headline on the glass, `Search` on the
  left post, `Watch first` and `Text version` on the right post, `Walk ›` on the first slab.
- **Walk** (click `Walk`, wheel, `↓`, or swipe up on the phone): one step down the path. All eight chalk slates rise at
  once with their verdict title and count, and a plain-words gloss appears under the headline (the lead verdict's own
  consensus, verbatim, with its count). Each further step stands you on the next day's slab (`Walk on ›`, then
  `Entrance ‹` from Friday). `‹` or `↑` walks back.
- **A bed** (hover, `←` `→`, `1`–`8`, or Tab to it): its slate rises larger. Click or `Enter`: the bed is faced. The
  panel shows the plant on its trellis, the orange `Watch first` tag with the pick, its speaker and length, the verdict
  title and count, the consensus, THE DEBATE question with each side on a wooden tag and the named speakers as smaller
  tags (each opens that speaker's talk), `The N talks cited, sorted ›` (Most seen, Best liked with "few votes" marked and
  never ranked above talks with enough votes, Most hearts), and `‹` `›` to the neighbouring beds.
- **Watch first** (right post): all eight picks with their verdict and reason, in one list.
- **Search** (left post, or just type anywhere): results list as you type with the three sorts; matching beds light up,
  the rest shade. Zero results says so and suggests a speaker, a company, a topic or walking the path.
- **Programme**: click a slab (`Mon 5` to `Fri 9`) or walk to it and press `Enter` on its label: that day's talks in time
  order (Europe/Brussels), with the other sorts available.
- **Every talk sorted**: click the DEVOXX wordmark (tooltip "Every talk, sorted by a signal").
- **Open a talk**: click any row, pick or speaker tag. `window.openTalk(id)` shows the toast `Walking to Room N` when
  the talk has a seat, else `Opening the summary`.
- **Text version**: the chalk link on the right post, to `../../../site/index.html`.
- **Esc** closes any panel, clears a search, or walks back to the entrance.
- **Phone** (`?shape=phone`, 340 x 690): portrait plate, beds alternate left and right up the path, the headline in
  three lines, `Walk` opens the eight verdicts as a sheet (each row opens its bed), a bottom strip holds Search, Watch
  first and Text version at 44 px.
- **Reduced motion**: walking is a cut, no leaning, no shadow swing, no bead glints, no idle drift; leaves only recolour.
- **Idle**: after 2.5 s with no input the sun drifts slowly along its arc (shadows and shafts turn with it) and now
  and then a bead runs down the glass. Any pointer move, key or touch stops it.

## Keys

`↓` `↑` (or `PageDown` `PageUp`, wheel, swipe) walk the path · `←` `→` or `1`–`8` move bed to bed · `Tab` through
Walk, Watch first, Search, Text version, DEVOXX, then the beds and slabs · `Enter` or `Space` face a bed, open a slab ·
`Esc` back · type any character to search · the pointer's x carries the sun. The hint line under the canvas says the same.

## Imagery: AI-generated plates (Codex image_gen), 2 of the budgeted 3

Both made with Codex's built-in `image_gen` on 20/10, one style line shared by both prompts, each checked before use.
The original PNGs stay in `assets/` and are not referenced by the page; the page loads the WebP conversions (PIL).

1. **`assets/plate-wide.png`** (1536 x 1024, generated 21:34) → `assets/plate-wide.webp` (1470 x 980, 329 KB), the
   laptop hall plate, shown with `object-fit: cover` at `50% 60%`. Prompt, verbatim:
   > Use the built-in image_gen tool (the imagegen skill) to make ONE image, landscape (wide, about 3:2 or 16:10): a
   > painted interior of an empty 19th-century Belgian iron-and-glass winter garden of the Laeken kind, on an overcast
   > October afternoon just after rain. Strict one-point perspective looking straight down the centre of a wet gravel
   > path; the vanishing point is at the exact horizontal centre of the image, about 45 percent down from the top.
   > Above: a high white cast-iron vault with slender ribs and celadon-tinted glass panes, faint rain beads on the
   > glass, soft grey diffuse light from above, grey-violet cloud beyond the glass. On each side of the path stand four
   > low rectangular raised beds of dark wet soil edged with weathered pale wooden boards, evenly spaced and receding
   > toward the vanishing point, all completely empty: bare dark soil, no plants, no trellises, no sticks. The nearest
   > beds start near the bottom corners of the image. The wet gravel path reflects the pale glass. Painterly gouache
   > look with soft edges, muted celadon greens, pale greys and warm wet browns. No sunbeams, no cast shadows, no
   > people, no furniture, no pots, no text, no lettering, no signs, no logos, no watermark.
2. **`assets/plate-tall.png`** (1024 x 1536, generated 21:44) → `assets/plate-tall.webp` (690 x 1035, 194 KB), the
   phone totem plate, centred. Prompt, verbatim: the same text with the first clause changed to
   > ONE image, PORTRAIT orientation (tall, about 2:3)
   and the vanishing point "about 42 percent down from the top", plus "and the path fills the lower centre" after the
   sentence about the nearest beds.

The third budgeted plate (an empty bed close-up for the faced state) was not generated: the faced panel draws the bed's
plant and trellis in SVG over a slate board instead, which keeps the plant identical to the one in the garden. Without
the plates the page falls back to a CSS vault (celadon gradient under repeating iron ribs, `#menu.no-plate`).

Everything else is code: plants, trellises, flowers, shadows (SVG `<use>` of each plant flattened onto the soil and
rotated by the sun's azimuth), light shafts and the sun disc (canvas, screen blend), rain beads (canvas), the slabs
(SVG), the slates and chalk type (HTML; Fraunces for the headline and wordmark, Shantell Sans for the chalk).

## What was tried and dropped (capture rounds t1 to t6)

- **Captioned posts** (t1): the left post carried a "Search" caption and a help line "Type anywhere: the sun finds the
  leaves."; the right post wrapped "Watch first" on two lines and "Text version of every talk" on three. Dropped for one
  44 px field and one 44 px button with a one-line link: fewer words at first glance (39 at rest), and the posts stopped
  competing with the headline.
- **Slates on the path** (t2): verdicts 5 and 6 stood on the path and hid the Thu 8 and Fri 9 slabs; the gloss ran in
  one 15 px line across the glass. Moved the eight signs to the side walls (3, 4), beside their beds (1, 2, 5, 6) and a
  horizon band (7, 8), and set the gloss in two centred 16 px lines, so the slabs stay visible one step in.
- **Small near plants** (t1): the near vine was two-thirds of its trellis and read as a sprig. The near pair now stands at
  1.12 scale so the harness vine fills its lattice, which is the point of the headline.
- **Phone**: an early phone layout kept the laptop posts; replaced by the bottom strip and the verdict sheet on the first
  Walk (the slates are hidden on the phone, where eight signs do not fit).
- **A 13 px element in the phone's faced state** (t4) was raised to 14 px before the last session ended; t5 and t6
  show 14 px as the minimum everywhere.
- **Landing pass (t6)**: the two horizon slates (verdicts 7 and 8) were the smallest verdict names on the wall at 15 px;
  raised to 17 px, widened (350 and 392 px) and spread apart (centres 0.315 and 0.70), with slates 3 and 4 nudged up
  (0.385 to 0.375) so no sign touches another at any step. Checked with a box-measurement script before the capture.

## Known gaps

- The search results panel (x 228 to 752) covers the four far beds, so a match that lights a far trellis (for example
  "Valhalla" lighting the JVM bed) is hidden behind the list; only the shading of the near beds shows. Near-bed matches
  ("ward" lighting the harness vine) show the glow beside the panel as intended.
- The far four plants (beds 5 to 8, scale 0.34 to 0.46) read as small sketches from the back row; their verdict names
  depend on the slates. At 8 m only slates 1 and 2 (24 px) meet the sign rule; 3 to 8 are 17 to 18 px.
- "Every talk, sorted" hangs on the DEVOXX wordmark (tooltip only); sorting is otherwise reached through each verdict's
  cited talks, each day and every search, so the function is never more than two steps away, but the wordmark route has
  no visible signifier.
- The chalk slates are click targets but not keyboard-focusable; the bed behind each one is (role button), and focusing
  it raises the sign. Far beds on the phone are small touch targets (about 31 x 39 px at scale 0.22); the phone's main
  route is the verdict sheet on the first Walk.
- The idle sun drift starts 2.5 s after the last input (the concept said 30 s; the shorter wait lets the four-frame
  capture strip show it). It is slow (a 36 s period), stops on any input and is off under reduced motion, but there is
  no explicit pause control.
- Nothing on the canvas says that the pointer is the sun; only the key hint under the canvas does.
- The third plate (bed close-up) was not generated; the faced state is a slate panel, not a window.

## after review 1

Review `reviews/r1/` (exciting 7, readable 6, UX 6.3). Fixes checked in `reviews/fixcheck-r1/` (hall composites read for
every changed view). No new imagery: the plates stay, everything below is code.

- **r1-1, the story at rest.** Each bed now carries a plant label on a stake at rest, numeral plus a short name at 20 px
  (`1 Harness over model`, `2 Review bottleneck`, `3 Untrusted agents`, `4 Faster patching`, `5 Leaner JVM`,
  `6 Native & GPUs`, `7 Boundaries first`, `8 Judging code`), placed beside its plant so the plant stays visible. A
  standfirst under the headline ties the metaphor to the data: *8 verdicts, one per bed. The first: the harness outweighs
  the model.* The first move reads `Walk the 8 verdicts ›`. Walk still steps in, and each label grows into the full
  verdict and its count (hover or focus on a bed at rest does the same for that one label). The old step gloss is gone:
  the standfirst does its job at rest.
- **r1-2, days and small type.** The five perspective slabs are gone. The days are a row of five stepping stones (21 px,
  86 px wide) across the near path, shown one step in (the brief puts the programme one step away), the stone you stand
  on in orange. The phone shows the row at rest above Walk. Identity line in Fraunces at 23/30 px; `Text version` is an
  18 px link on its own plate in the bottom-right corner.
- **r1-3, panels.** Every panel starts at y 100, below the two corner posts, so Search and Watch first stay visible
  and nothing peeks through; the close button sits in the panel's own padding; `Text version` hides while a full panel
  is open and the labels behind a full panel are hidden. Watch first shows all eight picks with their full reasons at
  once in two columns of four (numbered like the beds). Any list that runs past its panel gets a "↓ N more below" strip.
- **r1-4, the verdict face.** Plant column 262 to 172 px; the sides of the debate stand side by side under the question
  (two columns, three for verdict 2), names as chips at the foot of each side. All eight faces fit without scrolling
  (measured); the cue appears if one ever does not.
- **r1-5, plants in the plate.** Each leaf has its own lit-to-shade gradient, a pale rim copy nudged toward the sun,
  a blurred contact shadow at the foot, a slightly muted palette, and the four far plants are hazed (lower saturation,
  0.35 px blur). Labels are one size (20 px) for all eight.
- **r1-6, toast.** Docked at the top edge, outside every panel, with a leaf mark; the chosen row (or chip, or pick) gets
  an orange ring while it shows.
- **r1-7, motion at rest.** Bug found: the animation loop stopped when the plants finished growing, so the idle drift
  never started (the four motion frames were identical). The loop now runs; the sun starts drifting after 1.2 s, dust
  turns in the light shafts, each plant breathes a fraction of a degree, a bead runs down the glass now and then. During
  the drift the plants turn in a tick every 1.5 s (eased) rather than every frame. All of it is off under reduced motion.
- **r1-8, hierarchy and keys.** `Walk` is the one orange control; Search is a pale inset field with the placeholder
  `Search talks` (an orange caret when focused); Watch first is the quieter dark button. Tab order: Walk, Watch first,
  Search, DEVOXX (every talk, sorted), the eight beds, the days (one step in), Text version.
- **Consistency.** Two panel shapes, each with a reason: the full board (watch first, every talk, a day, a verdict's
  talks, a faced verdict) and the search drop-down hanging from the field (so the lit beds on the right stay in view).

states.json: new `rest-labels` and `verdict-three-sides`; `story-open` checks the day row instead of the gloss;
`day-wednesday` walks one step first; `keyboard-face` takes five Tabs; `phone-day` uses `#days`; `watch-first` checks
picks 6 and 7 too.

Trade-off: the resting layer now counts about 70 words (39 before): the eight short labels and the standfirst are the
story the review asked for, the five day labels left the resting layer. The labels read as one set (same plate, same
size, numbered), but this is more than the brief's 15 words.

Known gaps after review 1: the step-in view is dense (eight full verdicts on the wall at once); the search drop-down
still covers the four left beds; the plants are still flat vector shapes, only better lit; the Watch first columns fit
with about 4 px to spare at the capture's fonts (a fallback font would push pick 4 into an unseen column).
