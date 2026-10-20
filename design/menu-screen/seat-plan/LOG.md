# seat-plan log

## t1 (20/10)

Built "Two Hundred and Five Seats" from the IDEAS.md build prompt: `index.html`, `style.css`, `seats.js`, plus
`shots.mjs` (6-detail, 7-search; `--extra` shoots watch / day / likes / toast / phone states for checking).

What it is
- One button per talk (205), positioned with `transform` on curved rows round a point behind the screen (rows bend
  towards it at the ends, seats turn with the row). Seat = rounded rect + darker seat-back on the side away from the
  screen. Front stalls: 8 verdict blocks (2 tiers of 4) holding the talks each verdict lists in `talkIds`
  (53 talks; a talk listed by two verdicts sits in the first, but lights with both). Back stalls: the other 152 in
  4 sections with aisles. Inside each block and in the back, the current sort puts the best talk in the front row,
  centre seat.
- Rest: 9 words ("205 talks. Pick a seat." + four chrome words) + the sort sentence + "Text version".
- Hover / arrow keys on a seat: it turns orange, its block lights one shade, the verdict title appears at the block's
  front edge, and the reserved band shows title / speakers / room + day / the sort's number. Enter or click walks
  (`openTalk` toast: "Walking to Room N" or "Opening the summary"). Touch: tap selects, second tap opens.
- "front rows: most seen" cycles views / likes / hearts and re-seats everyone (transform transition, delay by row
  and distance from the centre, capped at 300 ms; under likes, "few votes" seats are hollow and rank last).
- the story: on the big screen the eight verdict titles become the names of their blocks, written at each block's
  front edge (the plan is the table of contents); the back stalls are covered by a panel with the intro, or with
  the chosen verdict's consensus, debate question, sides (lead sentence bold, names open their talk) and the pick.
  The pick's seat gets a white seat-back in its lit block. Phone: a list, then the verdict.
- watch first: the 8 picks move to the front-centre of their blocks with white seat-backs, other seats dim; the band
  shows the pick and its `why`; arrows go pick to pick.
- by day / search: the day's talks (time order) or the matches (title/speaker hits first, then the sort) fill the
  hall from the front, the rest dim; a list over the back stalls gives the programme or the results (time, title,
  speakers, room), in sync with the orange seat. Typing anywhere starts a search. Esc / the active word again /
  clicking empty hall returns to rest.

Choices and deviations
- Seats are 18x15 (pitch 26x23) instead of 14x12 with 8 px gaps: read from the back of the hall in inhall.py, and
  the plan fills the screen's top 60%. Phone seats are 15x11 (not 22x18): 205 seats at 22x18 do not fit 340x690 with
  the band and chrome; tap targets are small there, the list modes carry the phone.
- Added the list panel for day and search (shared detail-layer guidance asks for a talk list and programme); seats
  alone made reading 12 results one-hover-at-a-time.
- Bug found by looking: a `.pick` style for the story panel also hit seats with class `pick` (14 px margin); renamed.
- The story panel overflowed with 3-sided debates when it had a verdict list column; moving the verdicts onto the
  blocks freed the width. Scrolling panels fade their last lines only while there is more below.

Open
- Phone story and lists scroll inside the totem; fine for a POC.
- Re-seating stagger is short (~300 ms spread); could be more audience-like if John likes the idea.

## t2 (20/10): critic 6/10, all ten fixes taken

The plan now explains itself before anyone touches it. Rebuilt `seats.js` around one geometry and `style.css` around a
venue palette. `index.html` changed: a `.hall` wrapper, verdict names as buttons, a legend button, and "text version"
as the fifth nav word.

Composition
- One geometry (fix 2): every seat is polar `(d, θ)` round one centre C behind the screen. The screen is an arc of the
  same circle (R0 1350, sagging about 27 px). Two straight side walls and three aisles (one on the phone) of constant
  width cut the hall into sections. The front of each section holds the verdict blocks, all eight on the same 2x4
  footprint, with empty places drawn as faint ghost outlines. The back stalls fill the same sections behind them.
  Seats are shared over all back rows in proportion to each section's room, so no row is ragged. The T and Tetris
  shapes are gone.
- Verdicts at rest (fix 1): the eight titles are printed at each block's front edge at 18 px, max 190 px wide (the
  tier pitch allows 190; measured, no collisions). Verdict seats are lobby sand; back stalls are auditorium slate.
  The names are buttons with roving arrow keys and one Tab stop, and clicking one opens that verdict directly.
  Deviation: names follow their tier's arc instead of a horizontal baseline. On concentric rows a flat baseline would
  float the outer names away from their blocks. Every name keeps the same offset from its block and the same style
  in every state (t1's weight shift caused the uneven baselines).
- Data in the seats (fix 3): seat light = rank percentile of the current sort (views, likes or hearts), mixed in
  oklab from lo to hi. Log-scaled views left most seats dim. "front rows: most seen" is gone; its place is taken by a
  legend ("lit by views" with a 5-seat ramp) that cycles the sort. It sits at the right end of the heading row on the
  big screen and in the empty front corner on the phone.
- Pre-lit seat (fix 4): the top talk by the current sort is orange at rest. Its title (with an orange seat glyph) and
  "speakers, room and time, 23,374 views, the most seen" fill the heading's second line. Hover, arrows and watch-first
  replace only that line, with no third tier. It is also the first seat Tab lands on.
- Locked unit (fix 5): the heading starts 12 px under the plan's lowest seat (`--plan-bottom` from JS), at 56 px with
  -0.032em tracking (1.4x t1; 1.5x did not fit with a two-line hover title). Measured worst case (the 153-character
  title hovered): 9 px clear of the nav; watch-first's longest "why": 14 px.
- Detail state (fix 6): the front stalls stay at full size as the table of contents. Other blocks dim to 0.4, and the
  chosen block's name gets the orange underline. The pick's seat is orange; the white seat-back is gone. Back stalls
  step out, and the panel uses their space. The consensus is the heading of this state (26 px, stepping down to 24
  or 22 px only when the verdict would not fit, which applies to 3 of 8). Then the question, each side as its bold
  claim with a 16 px byline (names open their talks), and Watch first as the only orange action, filled, bottom
  right. Deviation from "claim plus one sentence": the supporting sentence is cut. The critic's own target was "two
  short bold claims", and with it a 3-sided debate cannot fit at 18 px. The evidence is one click away in the talks
  the byline opens. For the JVM verdict there is no short claim (each stance is one 200-character sentence naming its
  speakers), so the sentence is the claim and the byline runs on at its end.
- Search and by day (fix 7): the hall steps aside, scaling to 0.5 at top left with a 560 ms transform. The matches
  re-seat from the front, so it still shows where they sit. The query or day picker and the caption sit under it, and
  the list takes the whole right column. Titles wrap and nothing is ellipsised. The list stops at a whole row (JS fit)
  with scroll-snap, and a quiet "N more below" replaces the fade.
- Phone (fix 8): a deep portrait fan (R0 300) with a centre aisle. The verdict blocks are curved front rows, two per
  tier over four tiers. Only the lit block's name shows (13 px on a field-coloured tab); eight names do not fit 75 px
  blocks. Story, search and day put the hall at 0.5 scale at the top with the content below it.
- Palette (fix 9), sampled from the renders: field `#15120f` (house lights down); back stalls slate `#5b6782` to
  `#b8c4dc` (seat-5.jpg upholstery is `#4b5971` lit; the lowest seat is 3.3:1 on the field); verdict blocks sand
  `#8b8277` to `#f3ebdf` (hall.jpg curtains `#b0a9a1`); orange `#f28c28` only for the chosen seat, its glyph, Watch
  first and underlines. Seats are a flat seat-back shape (radius 8/3) with no lip.
- Chrome (fix 10): "text version" is the fifth quiet nav word, not underlined. Every focus mark is the orange
  underline (seats get a 2 px orange bar under them). The verdict hover label is gone: the names are always there.

Bugs found by looking: `replaceChildren` stringified null children ("nullnull" above the consensus); a specificity tie
kept back stalls visible in the story; the heading block swallowed clicks on the legend; a phone child
`visibility: visible` leaked the verdict tab into the mini hall; a desktop rule with an id beat the phone story's
hide rule; day names wrapped ("Mon / 5"); the toast covered two verdict names and now sits on the heading row.

Open
- Phone story scrolls inside the totem for long verdicts, which puts Watch first below the fold there.
- Under "lit by likes", 149 of 205 talks are "few votes" and drawn hollow, so the hall is mostly outlines. That is
  honest, but a lot of it.

## t3 (20/10): critic 6/10, one auditorium

The critic saw "four jellyfish", not a room. Rebuilt the composition rather than patching it. `seats.js` has new
geometry and modes, `style.css` was rewritten, and `index.html` has a credit on the screen arc, a one-line legend, a
cue line, a pins layer and a hover label. `shots.mjs` gets four more check states.

Composition
- One room (fix 1): the screen and every row are arcs round one centre (R0 2800, flatter than t2's 1350 so names and
  rows tilt at most about 7°). Three radial aisles of constant width run from the front row to the back wall. The
  ghost outlines are gone. The back stalls are one slate field of 5 rows behind the front rows, with no floating
  islands.
- Verdicts are the two front rows (fix 2): 4 + 4 runs across the full width, each a single row of its own talks
  (6 to 8 seats, so the length shows how many talks it holds). Each run starts at its section's left edge, so the eight
  names sit on a four-column grid. Each name sits 8 px above its own first seat, left-aligned to it. The next run up
  is at least 21 px away (about 3x), and no name sits between two runs. Deviation: names are rotated to their run's
  arc (up to about 7°) instead of flat. On concentric rows a flat name over a right-hand run collides with seats that
  rise under it.
- Screen and identity (fix 3): the screen arc is sand at 55% and 3 px wide, no longer the brightest stroke. Under it,
  set along the arc: "Devoxx Belgium 2026, Kinepolis Antwerp, Monday 5 to Friday 9 October" (built from `MENU.event`,
  `venue` and the days in the data). The chosen seat is orange at 1.25x with a thin orange ring. It is now the one
  hot mark on the screen.
- Legend (fix 4): one line under the plan, right-aligned: [sand] the eight verdicts · [slate] the rest of the week ·
  [ramp] brighter: more watched. The last words are the sort switch (more watched, better liked, more hearts) in the
  system's link style. Hollow "few votes" seats are gone too: they looked like t2's ghosts, and few-vote talks
  already rank darkest. The readout still says "few votes".
- Names (fix 5): 15 px, weight 450, in sand type (`--sand-text`), part of the seat system.
- Heading (fixes 6, 8): 52 px, then the cue "Or open one of the eight verdicts named in the front rows." (it says the
  names can be opened without repeating "pick a seat"). The readout is a fixed 98 px slot: title clamped to 2 lines,
  meta clamped to 2. The nav is absolutely placed, so nothing can push into it. On the big screen, hovering or arrowing
  onto a seat shows a small paper label beside the seat, set along its row. It may cover seats but never a verdict
  name. The first attempt above the seat covered names.
- Focus vs current (fix 7): focus is a 2 px off-white outline at a 3 px offset (5 px on seats, outside the orange
  ring). The orange underline only marks the current word or verdict.
- Nav (fix 8): four words at 75% paper ("the story", "eight to watch", "by day", "search"). "watch first" is renamed
  for what you get, and the detail link keeps the "Watch first" name. "text version" is a small underlined link in the
  bottom-right corner, not a fifth equal word. The toast is no longer a filled box: it is an orange seat glyph and
  "Walking to Room 8" in that corner.
- Detail (fix 9): the room stays put. The back stalls fade to 13%, the other runs to 35%, the chosen run stays lit and
  its name is underlined in orange, and the pick's seat is orange. The argument sets over the faded stalls: consensus at
  30 px across the full 900 px, the question, the sides in 2 or 3 columns, then "Watch first: State of Agentic Coding →"
  as an orange text link with the system underline, and "← all verdicts" at the right (Esc also works). Deviation: the
  consensus sets in 3 lines, not 2. It is already at the full measure, and 2 lines would need about 22 px, which loses
  its heading weight. fitStory steps 30 → 22 px only when a verdict would overflow (the JVM one does).
- Search (fix 10): the hall steps to the left column at 0.55 and does not re-seat. Matches light up where they sit,
  which shows which verdicts a topic was argued in, and everything else dims to 20%. The query, caption and the chosen
  talk's tldr fill the rest of the column, so the void is gone. Results are ordered by the current sort only (no
  hidden title-hit rank), and the caption says so ("most watched first"). Each row is numbered and shows its views.
  The matched seats carry the same numbers, but only for the rows the list shows right now (they update on scroll).
  Numbering all 34 "spring" matches piled up into unreadable pins on the phone. By day works the same way: the day's
  talks lit in place, the list in time order.
- Phone (fix 11): four tiers of two runs with a centre aisle. All eight names show, 12 px, at most 2 lines (a left name
  may run into the centre aisle, never over the other column). The t2 collision is gone. The legend is one line under
  the plan ("verdicts", "the rest"). The heading breaks after "205 talks.". The readout is names, room and time on one
  line, then the views on their own line. The nav is a 2 x 2 grid, with "text version" small at the right of the
  second row.

Bugs found by looking: the pins layer swallowed pointer events (the hover shot timed out); a `.seat.dim` rule with
higher specificity held the back stalls at 35% in the story; the phone back stalls had 8 seats too few (a page error);
flex gaps split "the eight verdicts" with a double space; the ring touched the name above at a 7 px gap (now 8 px,
ring scale 1.25).

Open
- The phone back stalls are tight (12x10 seats on a 12.5 px row pitch) to keep the readout and nav clear.
- Search pins at 0.55 scale are about 15 px. They are readable on the laptop but not from across the hall.

## t4 (20/10): critic 6.2/10, one room under a lit screen

The critic still saw four rotated tables, a title fighting the plan for the middle, a dead band above the nav and
verdict names too small to read across the hall. I rebuilt the composition. All three files were rewritten. New:
`glass.webp`, a blurred and mirrored crop of the hall still's curtains and light strip.

Composition
- One auditorium (fix 1): two wings with a single centre aisle. The three radial aisles made four blocks, and that was
  the "tables" read. Every row is a concentric arc round C (R0 2800). The side walls splay out towards the back, as a
  fan does. The back stalls fill from the back wall, so every row runs unbroken from wall to wall. Only the stalls'
  front row is short: what is left over (9 a wing), packed against the aisle. The two verdict rows sit next to each
  other at the normal row pitch as one sand band, four runs a row. The first row's names sit above it and the second
  row's names hang below it in the cross aisle. Nothing sits between them, so the band reads as rows rather than
  labelled boxes.
- Names (fixes 1, 3): set in Big Shoulders 650 at 23.5 px (about 34 px on the 1920 hall frame), never rotated more
  than 3°. JS places each name as close to its own run as the curve allows (6 px clear of the highest seat under it,
  or the lowest when it hangs below), and lays them out again once the font has loaded. Each name's width stops
  before the next run's name.
- Screen = title (fix 2): the screen arc is an 8 px lit band (`--band`). Under it sit "205 talks. Pick a seat." at
  68 px in Big Shoulders 800, centred, and the credit at 16 px (about 24 px in the hall). Band to plan bottom is about
  67% of the height.
- Base band (fixes 2, 6, 7): the readout is anchored to the bottom, with two title lines kept free above the meta, so
  the meta line never moves. Under it is one cue line ("Point at any seat to see its talk. A verdict's name opens what
  was argued." On the phone: "Tap a seat to see its talk, again to walk there."). Then the nav: four words at 30 px in
  Big Shoulders with an orange current bar. The dead band is gone.
- Views (fix 4): the legend is cut. Each stall is one flat colour. Only the top tenth by the current order is a step
  lighter, and they sit front and centre, so the bright patch is where the most watched talks are. No front-to-back
  ramp. The optional "the rest of the week" aisle label was left out: the cue and the readout already say what a
  seat is.
- Naming (fix 5): the eight are "verdicts" everywhere: nav, aria labels and hints. Deviation: the nav reads
  "verdicts / watch first / by day / search", not "... / most watched". The eight picks are a brief function
  (MENU.picks), and "watch first" is the same words as the link in each verdict. The order (most watched / best liked
  / most hearts) now sits in search, where it changes the list you are reading. An empty search lists all 205,
  "most watched first", so "most watched" is one click away.
- Hover (fix 7): the white chip is gone. The orange seat (1.3x, no ring) plus the readout carry it, and the hovered
  run's name lights up.
- Detail (fix 8): the room slides up by `--lift` to its front band, which stays as the table of contents. The back
  stalls go to opacity 0, and the title and readout hide. Nothing is set over seats now. The consensus is at 29 px
  (fitStory steps down to 22 px). The sides sit in columns with a thin rule and "or" on the rule. I used "or", not
  "vs": the debates are questions with options, not fights. "Watch first: ..." is 30 px Big Shoulders in orange with
  a seat glyph, larger than the 15 px speaker links. On the phone, Watch first comes straight after the consensus so
  it stays above the fold.
- Search and by day (fix 9): the mini plan is dropped. The screen band stays; the plan, names and title step out.
  The query (46 px) and the order switch sit under the band, with the results in two columns. Each hit leads with a
  seat carrying its number: sand for a verdict talk, slate for the rest, orange when chosen. So every hit has a
  number, the chosen one too, and none overlap. The repeated tldr and the arrow-key hint are cut. By day: big day
  names, times as the lead.
- Phone (fix 10): "text version" has its own footer line. The fan is curved (R0 650) with a centre aisle, and the
  verdict rows go in pairs with names above and below. Legend cut. The verdict list is gone: the names on the plan
  are the contents there too.
- Type (fix 11): Big Shoulders (Chicago signage, opsz axis) for the title, names, nav, day names, query and seat
  numbers. Public Sans for reading. Tabular figures throughout. Meta grey raised to `#c2baae` (9:1).
- In the room (fix 12): `.glass` adds the curtains and light strip reflected at 7.5% screen blend, a 1 px bezel edge
  and a soft falloff to the corners. The field is lifted to `#1b1814`. inhall.py lives outside this folder, so the
  panel carries it. When porting, drop `.glass`: the real page's `.face.is-lcd` already does this job.

Bugs found by looking: the hall's `.title` wrapper (absolute, full width) also matched the list rows' `.title`, so
every result title vanished; it is now `.marquee`. Names collided with the credit and with each other until they got
a shared gutter. A phone name touched the stalls behind it (back rows moved down 7 px). Metric figures were cut off
by the ellipsis (meta is now flex, names ellipsise, the figure stays). In 2-sided verdicts, Watch first floated
100 px below the debate.

Open
- 3-sided verdicts and the JVM one run the detail close to the nav on the big screen (it fits, with fitStory).
- Phone verdicts still scroll inside the totem below Watch first.
