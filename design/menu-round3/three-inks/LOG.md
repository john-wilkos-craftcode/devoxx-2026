# Three Inks: the week as a risograph proof

Final capture: `shots/t8/` (`rest-laptop-hall.jpg` is the picture that counts; 71/71 expectation checks pass, no console
errors, smallest font 14 px in every state, `#menu` 980 x 613 and 340 x 690). Earlier rounds `t1`-`t4` are the first
build, `t5`-`t8` the rebuild described below.

## The idea

A cinema lobby wall is where posters hang, so the hall screen becomes the week's poster: a three-colour risograph proof
on cool newsprint paper, lit from above like a sheet under a lobby spot. The intro gives its own proportion (about a
third of the sessions sat in the agentic track), so the three inks are the three storylines of the intro at their true
size. Fluorescent pink prints the coding-agents story and is exactly a third of the sheet (63 of 205 talks, 188 px of
613); riso blue prints the Java platform (39, 117 px); yellow prints architecture, practices and people (61, 182 px);
the remaining fifth (42 talks in tracks the intro never names) is bare paper, where the search lives. Colour is the
information architecture and the proportions are real data. The ink drum standing at the end of each band is the
band's image and its filter: click it and that ink leaves the print and every list. The stamp is the recommendation.
The venue is in the print: Room 8's seats are halftoned into blue dots on the very screen that stands in that venue,
its cinema screen keyed out to bare paper. The five days are a printer's colour-control strip along the bottom edge,
each patch mixed from that day's real track proportions. Inside the stories, every pick's real YouTube thumbnail is
printed in its storyline's ink (greyed, ink laid over it with `lighten`, a dot screen multiplied on top), so the
photographs obey the same separations as the sheet. Nothing on the sheet has a body: print furniture only (drums, a
stamp, a loupe, a control strip).

## How to use it

- The sheet: the pink headline (the story), the WATCH FIRST stamp (the first move), JAVA and ARCHITECTURE & PEOPLE
  (the other two stories), the ruled search line, the five-day control strip (hover a patch for its count), the text
  version link.
- Click a band, or Enter on it: the sheet floods in that ink (led in from the right like a plate, settling the last 3 px
  into register); its verdicts print as riso headlines with their counts, their debate question (two-verdict stories)
  and their WATCH FIRST pick with its thumbnail. Click a verdict title or "Open the debate" for its consensus, the debate
  question, the sides on paper blocks (stance in bold, the evidence under it, named speakers underlined open their
  talk), and its talks sorted by Most watched, Best liked (thin votes marked "few votes" and never ranked above talks
  with enough votes) or Most hearts; picks carry a WATCH FIRST label in every list.
- Click the stamp or press **W**: all eight picks on bare paper with their thumbnails and reasons, each with the ink
  dot of its story.
- Type in the search line (or press **/**): an index prints as you type (title, speakers, room, Brussels day and time,
  an ink dot per talk), with the same three sorts; Enter moves to the first result; zero results prints "Nothing printed
  for ..." with a next step.
- Click a day patch: that day's talks in time order, grouped by start time; the patches stay at the top to switch days.
- Click a drum, or press **1 2 3**: that ink is pulled out of the print (the plate slides off behind its drum; the
  stamp's orange turns yellow when pink goes, because orange was only pink over yellow) and out of every list, search
  result and day. Click the empty keyline again and the plate comes back 3 px out of register, then snaps true.
- **Esc** backs out one level; the foot of every opened state carries the other inks as strips to switch story.
- Click a talk anywhere: `openTalk(id)` prints a registration-mark tag above the foot, "Walking to Room N" or
  "Opening the summary".
- Keys: **Tab** moves (order: story, watch first, search, the other stories, the days, text version, the drums; focus is
  a thick black ring with a paper inner ring on the sheet, and inverted black-on-paper in lists), **Enter** opens,
  **Esc** back, **/** search, **W** watch first, **1 2 3** pull an ink, up/down arrows move between bands on the sheet.
- `?shape=phone`: the same four bands at the same proportions (212/131/206/141), the headline in three lines, the stamp
  under it, a 44 px search line and 44 px day patches; opened states keep one header row (Back, title, a 44 px search
  button) and scroll as one long sheet, with the signal under each talk and the time slots as headings.
- Reduced motion: no print-in, no flood, no slides; inks cut in and out.

## What I tried and dropped

- Four true multiply ink layers with per-plate offsets (the concept's "produced, not picked" overprints). Dropped for
  plain band fills plus local multiplies where it shows: the stamp (yellow plate 2 px out, pink 50 % plate over it),
  explicit violet and green seams at the band edges, and the thumbnails. Same picture, far less DOM.
- Canvas-2D halftoning in the page: `getImageData` on a `file://` image taints the canvas, so the halftone is
  precomputed with PIL (`tools/halftone.py`): auto-levelled luminance, 45-degree grid, dot radius from darkness, the
  blue-keyed screen chroma-keyed to paper. The first letterbox (510 px) left a flat blue field before the drum; it now
  runs 640 px to the drum's slot.
- CSS `mask-image: url(file)` is fetched with CORS and blocked under `file://`, so the three plates are inlined as
  WebP data URIs in `assets/masks.css` (`tools/inline.py`).
- The first drum drawing (slender, 1:4) was too thin at band height; regenerated stouter and widened 1.3x in the plate
  step. Its mesh, drawn as big black dots, made the drums read as maroon, navy and olive; the ink plate is now the whole
  silhouette and the mesh is weakened to a texture. A soft slot shadow on the plate to the drum's left makes the drums
  stand in front of the print instead of lying in it.
- The yellow 50 % screen read as a second solid in the squint test and fought the pink for the eye; it is a 40 %
  screen now (coverage of the 4 px dot), the drum stays solid ink, and the loupe's magnified dots show the real screen.
- The search was in the foot's DOM order, so Tab reached it after the three stories and the stamp; it is now the third
  stop (story, watch first, search) while staying on the bare paper.
- The control strip sat in the middle of the foot with 14 px day names; it now runs along the bottom edge as a real
  printer's strip, full width, 16 px names, hover prints the day's count.
- Paper on solid blue is 4.1:1, so in the blue story every word below display size (standfirst, counts, "The debate",
  "Open the debate", the sort bar, the search box, the foot strip's count) is black on a paper block.
- Debate stances were clamped to three lines by CSS, cutting words in half; the stance is now its own bold line and the
  evidence is trimmed on a word boundary to the block's room (full text in the title attribute, untrimmed on the phone).
- A full-sheet halftone ghost behind the opened blue story at 50 %: busy under the text; kept at 18 % multiply, below
  the header.
- The toast at the sheet's bottom edge covered the foot strips; it sits above them now.
- Verdict titles on band hover: no room in the pink band without shrinking the headline; the hover prints an "N verdicts
  · N talks · open the story" tag instead.
- Ambient motion: none. A print is still. The print-in at load (plates led in from the right by their drums, 110 ms
  apart, sliding the last 3 px into register) is CSS and done in 0.6 s, so the 4-frame strip shows a still sheet; the
  motion lives in the interactions (flood on open, plates sliding on pull, the toast).

## Codex-generated imagery (AI-generated, labelled)

Model gpt-6-astra, built-in `image_gen`, three generations of the six-per-design budget (none added in the rebuild).
Style line shared by all: "risograph print, flat shapes, coarse grain, no shading, no gradients, no text, no logos,
transparent background".

1. `assets/drum-raw.png` (not used on the page): "the ink drum of a risograph duplicator drawn as a risograph print: a
   tall upright cylinder standing on its end, seen slightly from above so its flat top cap and a small axle stub on the
   cap show, a fine perforated screen (a tiny regular dot mesh) wrapped round its whole wall, a plain black rim at top
   and bottom. Two inks only: fluorescent pink (#FF48B0) for the cylinder body and black for outlines, rim and mesh.
   Style: risograph print, flat shapes, coarse grain, no shading, no gradients, no highlights, no text, no logos,
   nothing else in the picture. Composition: the cylinder centred and filling the frame vertically, lots of empty space
   either side. Transparent background (PNG with alpha)." Came on a black ground with a magenta glow, 1:4 slender.
2. `assets/loupe-raw.png` -> `assets/loupe.png` (black plate mask, used): "a printer's loupe (a small folding magnifier
   used to check halftone dots on a print) drawn as a risograph print in black ink only: seen from above at a slight
   angle, so its round lens frame is a wide ellipse on top of a short tapered skirt below it; a thick black ring for the
   lens frame, the glass inside the ring left completely empty and see-through (pure transparent, nothing drawn inside
   the ring); the skirt a flat black shape with a little grain. Style: risograph print, one ink (black), flat shapes,
   coarse grain, no shading, no gradients, no highlights, no reflections, no text, no logos, nothing else in the
   picture. Composition: the loupe centred and filling the frame, empty space around it. Transparent background (PNG
   with alpha), nothing behind the loupe at all." The lens ellipse is measured by PIL (`tools/assets.py`) and used as
   the clip for the magnified 16 px dot screen.
3. `assets/drum2-raw.png` -> `assets/drum-ink.png` + `assets/drum-key.png` (used, tinted per band): same prompt as 1
   with "a STOUT upright cylinder standing on its end, about twice as tall as it is wide (not slender)" and "no glow ...
   nothing behind the cylinder at all". Came with real alpha; separated by `tools/plates.py` into an ink plate (the
   silhouette) and a black key plate (rims, outline, stub, weakened mesh), widened 1.3x.

Code-made imagery: the Room 8 halftones (`assets/halftone-*.webp`, from `site/cinema/media/seat-8.jpg`), the one-ink
thumbnails (CSS over the real `i.ytimg.com` images, a flat ink block if one never arrives), the grain and paper-fibre
SVG turbulence overlays, the spot-light fall-off, the roller marks on the pink flat, the 4 px yellow dot screen and its
16 px copy under the loupe, the stamp overprint, the seams, the registration marks, the drums' slot shadow, the
control-strip patches (gradients computed from the per-day track counts).

## Known gaps

- The pick's thumbnail halftoned onto the blank screen of the opened blue state (optional in the concept) is not
  built; the blue story keeps the room as an 18 % ghost and the thumbnails sit in the pick blocks instead.
- Thumbnails need the network (`i.ytimg.com`); offline they degrade to a flat ink block, which the capture cannot show.
- Band hover does not print the verdict titles (only the count tag); the titles are one click away in the story.
- Debate evidence is trimmed to the side block on the wall (full text on hover via the title attribute and on the
  phone); the full text is not shown on the wall.
- The 4-frame motion strip is still by design (see above).
- `facts.json` counts rows below the fold of scrolling lists as "outside" text nodes (2-3 in list states): those are
  scrollable lists, not clipped content.
- The X of DEVOXX is black, not orange: on the pink band an orange X would be 1.3:1 against its ground.

## after review 1

Capture: `reviews/fixcheck-r1/` (86/86 expectations pass, no console errors, smallest font 15 px at rest and 14 px in
opened states, no words under 14 px). Where this section and the text above disagree, this section is current. No new
Codex images (still three of the six); the loupe image is no longer used.

What changed, by review issue:

- **r1-1, first move and structure.** Every band now carries a permanent plate label printed in the black plate at its
  lower right: "OPEN 4 VERDICTS →" / "OPEN 2 VERDICTS →" (black block, 24 px display, paper type). Nothing depends on
  hover any more; the old hover tag is gone. JAVA and ARCHITECTURE & PEOPLE now each carry a short finding taken from
  the intro ("Leaner and faster." / "Clear boundaries, kept skills."), so all three bands read as a story with a
  finding, and the labels count the eight verdicts (4 + 2 + 2). The stamp has a second line, "8 talks, one per
  verdict". The visible word count at rest is 57 (it was 58, which included hidden drum labels: the counter now
  ignores them because they are `visibility: hidden` until hover). The about-15-word first-glance layer is the eyebrow
  and the headline (14 words) plus the pink band's label; the rest is set smaller on purpose.
- **r1-2, the drums.** They now stand inside the safe margin (34 px from the right edge, no longer cropped by the
  bezel), each with a permanent printed "PULL" label on the cylinder. Hover/focus prints "Pull the pink ink / it hides
  its 63 talks · key 1" exactly over the band's plate label. Pulling no longer blanks the band: the plate slides off
  and leaves a ghost, a light dot screen of that ink, so the headline (pink), JAVA and its finding (now black) stay
  printed; the band's plate label becomes "63 talks pulled from every list / PUT THE PINK INK BACK", the drum label
  becomes a black "PUT BACK", and the whole band is now the put-back target (clicking a pulled band puts the ink back
  rather than opening the story). The loupe/bowl is removed: the yellow band's room went to its finding.
- **r1-3, the opened states.** No more white boxes: an opened story is its ink's title bar (full pink with roller
  marks, blue with Room 8 knocked out as paper dots, solid yellow) over a light screen of the same ink, and everything
  sits directly on that field under printed black rules. A story shows only its verdict titles (38-50 px) with a
  "N talks →" label, the debate question for the two-verdict stories, and the pick (halftoned thumbnail, stamp, title,
  speaker, room; the reason only where there is room, clamped to whole lines). Stories went from 209-301 to 182-220
  visible words, verdicts from about 320 to about 220, watch first from 448 to 406, days from 256-277 to about 210.
  A verdict shows each side as its stance (20 px bold) and named speakers (16 px links); the evidence moved to the
  tooltip on the wall and stays in full on the phone. Lists never end in a half-cut row: the rows that do not fit
  wait behind a printed "↓ N MORE TALKS · SHOW THEM" edge (`fitLists` in `app.js`), which opens the list for
  scrolling and focuses the first new row. Watch first moved the speaker and room under the picture so the reason
  gets the width, clamped by JS to whole lines (`fitPicks`).
- **r1-4, the programme strip.** Five 46 px patches, the full width beside "PROGRAMME / 5-9 OCT", with the day name
  at 27 px in black inside its own ink mix (black on the blue segment is 4.0:1, above the 3:1 for large text); hover
  prints the count above the patch. The phone patches are 46 px tall with the day name inside at 19 px. "Text
  version" is 19 px (16 px on the phone, with a taller hit area).
- **r1-5, the toast.** A printed ticket centred over the foot, in the light screen of the talk's ink, with a black
  rule and offset shadow: "WALKING TO ROOM 3" at 28 px display and the talk title under it; fades after 3 s. It sits
  over the foot strips, not over the list.
- **r1-6, keys at rest.** Key caps are printed beside what they open: "W" on the stamp, "/" at the end of the search
  line; the drums' 1 2 3 are in their hover labels and accessible names. The phone hides them.
- **r1-7, brightness.** Full saturation is now only on the sheet's bands, title bars and the foot strips; the large
  opened fields are 25-35 % screens of the ink (pink #F6C6DF, blue #BFD7E6, yellow #F5EDA4), with black type at full
  contrast (so the blue story no longer needs paper blocks behind small text).
- **r1-8, motion.** At rest the drums turn one at a time (the screen mesh rolls across the cylinder, 1.5 s, eased,
  about every 2-4 s), which also points the eye at the drums; it stops on any pointer or key input and resumes after
  a quiet minute, and it is off under reduced motion. The four-frame strip now differs at the drums. Opening a story
  is a press: the sheet is led in from the right and settles 3 px into register, then its title prints a hair out of
  register and snaps true (260 ms, ease-out).
- From the reviewer's other notes: the three-ink foot no longer clips "61 talks"; the blue story's title bar carries
  Room 8 as knocked-out paper dots; `tools/halftone.py` makes the narrower band letterbox (400 x 117).

states.json: updated `hover-yellow`, `hover-drum`, `open-talk-walk` (ticket title), `pull-blue`, `pull-pink-key`
(headline still visible, put-back label), `verdict-review` and `verdict-jvm-sorted-liked` (open the "more" edge
first); added `rest-idle-drum`, `verdict-more`, `pull-blue-put-back`.

Not changed, on purpose:

- The opened views keep the search box, the other two inks in the foot and the Esc hint on every layer. They are the
  way out and the way across on a shared wall (the reviewer's own "keep" list praises the foot strips), and a
  persistent search is the familiar pattern.
- The verdict badge says the verdict's count from the recap (for example 20 talks) while its list shows the talks the
  recap links to it (8); both come from the data, unchanged.

Known gaps after review 1: a long first sentence of a side is trimmed on a word on the wall (full text in the
tooltip); the phone rest has 52 visible words (findings and labels added; it is read at arm's length); the idle
drum turn is ambient motion with no on-screen pause control, but it stops at the first touch or key and runs only
while nobody is using the screen.

## design pass 2 (21/10)

Capture: `reviews/final2/`. Where this section and the text above disagree, this section is current. John's notes
(`../JOHN-NOTES.md`): he liked the solid, understandable UI and the colours sorting the talks, found it "too visually
busy", and wants it "immediately parsable" with a limited amount on screen at any time. This pass keeps the concept (the
week as a three-ink risograph proof, the bands at their true proportions, the ink as the category, the sheet flooding in
its ink when you open a story) and cuts everything else. No new Codex images (still three of six; none used on the page
now). Note: an earlier attempt at this pass was interrupted with `index.html` half rewritten; all three files were
rewritten from the `reviews/final/` design.

**The resting sheet, before and after.** Before: 29 separate visible things (eyebrow, headline, tilted WATCH FIRST
sticker over the headline with its W key cap and sub-line, three black "OPEN N VERDICTS" blocks, three ink drums with
three PULL labels, JAVA and its finding, the halftone Room 8 image with its white rectangle, ARCHITECTURE & PEOPLE and
its finding, the search line with its / key cap, PROGRAMME and 5-9 OCT, five striped colour-mix patches, the text link,
plus seams, registration marks and a yellow dot screen). After: 18, and none overlap: the eyebrow, the headline, and per
band a title, a finding and one count ("4 verdicts · 63 talks →" in a keyline that fills with ink on hover/focus,
all three the same width in one right-hand column); on the paper foot one strong search field (white, 3 px black frame,
placeholder #3b3d3a, about 10:1), one orange Watch first block ("8 picks →"), PROGRAMME with five plain day buttons
("Mon 5" ... "Fri 9") and Text version. Cut about 40 %. Removed: the drums, the sticker, the key caps on the sheet, the
halftone image in the blue band (now a clean blue field; fixes the "broken image"), the seams, registration marks, the
yellow dot screen (now solid yellow, so the three inks read as three equal categories), the striped day patches. The
yellow title is smaller (60 px) than the headline (74 px) so the headline wins. Hierarchy: headline, the three bands,
then search and Watch first.

**One clear thing per opened screen** (all opened screens: an ink title bar with "← Back Esc", the title, and a
"Search" button; the foot strips of the other inks and the per-state search box are gone):
- A story shows its verdicts one step in, one row each: a black number, the verdict title, its debate question, "Open
  →" (4 rows for coding agents, 2 for Java and for architecture & people). The watch-first picks and thumbnails left
  this screen.
- A verdict shows one verdict: "Verdict N of 8", the title, the consensus, the debate question, its two or three sides
  (stance and the named speakers, who open their talk), then "See its N talks →" and Previous / Next verdict (arrow
  keys too). The talk list moved one step further, so the debate is no longer crowded by a list.
- A verdict's talks, search results and a day are the same list: a window of about six whole rows (it is sized to end
  on a whole row, never a half-cut row), scrolling inside, "N more below, scroll" under it, and the three sorts as one
  segmented control. Each row carries a solid ink bar at its left edge: its category.
- The colour key sits under every list: four switches (Coding agents, Java, Architecture & people, Other tracks), each
  with its ink swatch. It is the key and the one filter that is left of the drums: switch an ink off and its talks leave
  the list (struck through, dashed). It replaces the drums, the PULL labels and keys 1 2 3 as a filter.
- Watch first shows four picks at a time (page 1 the four coding-agents picks, page 2 Java and architecture), each with
  its verdict and ink swatch, title, speaker, room and Brussels time, and the reason in two lines; Previous / Next picks
  (or arrow keys). The thumbnails are now a plain two-colour print (black and the story's ink, no dot screen on top), so
  the slide can be read.
- Programme: a day's talks in time order, each row with its time; the five days stay at the top as plain tabs, the
  current one inverted.
- No results: "Nothing printed for ..." with three one-click tries (MCP, Valhalla, testing).
- The toast is a small printed ticket at the top right over the title bar, so it never covers a list row.

**Keys** (hint under the screen): Tab, Enter, Esc back one level, / search, W watch first, 1 2 3 open the three stories
(they no longer pull inks), left/right arrows previous/next verdict or picks, up/down move between the bands on the
sheet. Focus: a 4 px black ring with a paper gap everywhere (inverted rows in lists).

**Phone** (`?shape=phone`): the bands keep their 63:39:61 ratio (180/112/174 px) above a taller paper foot with Watch
first, search, the five day buttons (46 px) and Text version; counts are compact keylines at the band's lower right.
Opened states scroll as one column; lists are not windows there, the key and sorts are 44 px.

**Reduced motion**: no print-in, no flood, no hover transitions.

states.json was rewritten for the new states: added `hover-watch`, `verdict-review-next`, `verdict-talks-review`,
`watch-first-next`, `search-hide-ink`, `search-try`, `keyboard-verdict`, `phone-talks`; removed the drum and pull
states (`rest-idle-drum`, `hover-drum`, `pull-*`, `phone-pull-blue`, `verdict-more`, `hover-day`).

Known gaps: the colour key/filter only shows under lists, so the sheet itself has no filter (by design: the sheet's
bands are the key). The verdict count shown is the number of talks the recap links to the verdict (6-8), not the
recap's wider count (12-23) used before, so the number on the button is what the list shows. The halftone and drum
assets in `assets/` are no longer used by the page.

## design pass 3 (22/10): glanceable

Capture: `reviews/final3/` (91/91 expectations pass, no console errors). Pass 2 is kept in `_pass2/`. John chose Three
Inks (22/10) and found pass 2 "a bit cramped and not glancable". Rubric used (list/hierarchy guidance, UXPin and
NN/g-derived notes): one focal thing per screen; rows of two lines (title, one grey line); about five items in view;
whitespace and hairlines over boxes and thick rules; one unit said once; content spread over the height, not packed at
the top.

- **Sheet:** the paper foot is one row: search, Programme, Watch first. The five day buttons and PROGRAMME label moved
  into the Programme view (Monday opens first, the days are tabs; key P). Counts are "N verdicts →" (talk counts stay in
  the aria labels). Text version moved to the pink band's top right. Visible words at rest 58 → 39.
- **Story:** the verdict rows share the full height; the OPEN boxes became a plain arrow; the question and standfirst
  are grey.
- **Verdict:** two zones centred between title bar and foot: the conclusion (60 px title, consensus), then the debate
  on a pale panel (kicker, question, sides; speaker names grey with a light underline). "See its N talks", "Verdict N
  of 8" and Previous / Next sit at the foot.
- **Lists:** five rows of two lines in view (78 px rows); titles and meta cut on one line with the full title as a
  tooltip; one number on the right with its unit once as a column head (VIEWS, LIKES PER 100 VIEWS, HEARTS); the
  Watch first tag sits at the start of the grey line. Sort is three pills, the key/filter is borderless "Show" chips,
  hairline dividers, 6 px ink bars, thin scrollbar.
- **Watch first (wall):** four short rows (verdict kicker, title) on the left; the pick under the pointer or focus on
  the right, large: picture (hq thumbnail), verdict, title, speaker · room · time, the reason (four lines), WATCH IT.
  Up/down move between the rows, left/right page. Phone keeps the card column (no underlines, two-line reasons).
- **Phone:** foot is Watch first, search, Programme, Text version; day tabs fit on one line.

states.json: day states open Programme first; `watch-first` checks the detail's picture; added `watch-first-hover` and
`keyboard-programme`; `keyboard-search` is two Tabs (search now comes before Programme in Tab order).

Known gaps: long titles are cut with an ellipsis on one line in lists (tooltip has them); the detail's title clamps at
two lines; the phone list number has no unit beside it (the VIEWS head is above the list).

**22/10 follow-up (John):** "Most hearts" means nothing to people who weren't there: it counts attendees who saved the
talk in their schedule before the conference (CFP `totalFavourites`). The sort is now **Most anticipated**, its column
head SCHEDULE SAVES, and each sort pill has a tooltip saying where its number comes from. Attendee star ratings: the
CFP API has `GET /api/public/ratings/top` (rating, numRatings, totalFavourites, combinedScore). It returns 204 (empty)
for dvbe26 on 22/10, while dvbe25 still serves 115 talks. The full per-talk lists (`/ratings/{token}`,
`/ratings/{day}/{token}`) need an organiser token.

**22/10 verdict debate (John):** "it is not immediately visually clear that there are 3 competing claims here" (the
sides were three columns under identical black rules, which also read like underlines). Each side is now its own card:
a white card with a 3 px black frame and a hard shadow, a black letter A/B/C beside its claim, and "Argued by" with the
speakers at the foot. A black VS disc sits in the gap between cards (above each card on the phone, where they stack).
The cards fill the height down to the foot (the pale debate panel is gone); claims are 30 px with two sides and 22 px
with three. The Valhalla verdict's stances open with a long sentence of evidence, so `CLAIM` in app.js gives its two
cards short claims ("Yes: it removes Java's last layout handicap." / "Not fully: the measured limits are real."); the
full stance is the card's tooltip. index.html loads style.css/app.js with `?v=N` so the browser can't serve a stale copy.

**22/10 talk card (John):** clicking any talk (a list row, a speaker in a debate card, a Watch first row) opens a
modal card instead of going straight to the talk; **WATCH IT** in the card confirms the walk (or opens the summary).
John first asked for a hover/select pop-up, then (mid-build) for "a modal with the info and a watch it button that you
click to confirm". Watch first's detail panel keeps its own WATCH IT, which goes straight there (its info is on screen).
The card: an ink strip (type · length · level, Watch first tag), the title (34 px display, three lines max), speakers
and company, room and time, the hq thumbnail as a two-colour print, the tl;dr, "Watch if" on an ink bar, views / likes
per 100 views / schedule saves, then WATCH IT with "Walks you to Room N" and Close (Esc). Focus goes to WATCH IT, Tab
stays in the card, Esc or the scrim closes it and returns focus to the talk you came from, and no shortcuts work behind
it. Motion: the scrim fades, the card rises with a slight turn and settles (340 ms), the ink strip wipes in, the title
registers, the thumbnail prints down and the lines come up one after another; it drops away in 160 ms. On the phone it
is a bottom sheet that slides up. Reduced motion: no animation. New states: talk-card, talk-card-mid,
talk-card-speaker, talk-card-esc, phone-talk-card (107/107 pass).
