# Five ideas for the hall screen (round 2)

Read BRIEF.md first. Judge each idea as the 3.6 m screen in `context/now-in-hall.jpg`, between the plants, from the
back of the hall. Rule for all five: at rest, at most ~12 words, one idea; every one of the 7 functions (story,
watch first, search, sort, open a talk, programme by day, text version) is exactly one step away.

Shared facts (from `design/menu-variants/data.js`, never invent): 205 talks, 8 verdicts, 8 picks, rooms 3-10 plus
BOF 1-2, Mon 5 to Fri 9 October 2026, 185 talks have a seat. Devoxx orange is `#F28C28`-ish, the venue's navy is
the current screen. All five define `openTalk(id)` with the toast from the brief, keep a visible focus ring, start
with content in the HTML (no opacity-0 starts), and give `prefers-reduced-motion` a cut-only version.

Common detail layer (so builders don't reinvent it): a "second screen" that slides or cuts in over the rest state
and holds, in order, verdict text + debate sides, the pick for that verdict, a search field, sort switch
(views / likes, "few votes" when `thin` / hearts), a talk list, and a 5-day programme. Esc or clicking the margin
returns to rest. Each idea below says what the rest state is and what the one step looks like; the second screen's
styling follows that idea's palette and type.

---

## 1. `title-card` — The Week in Eight Cards

**Outside inspiration:** Saul Bass's title sequences (*Anatomy of a Murder*, *Vertigo*) and Pablo Ferro's
*Dr. Strangelove* titles: one flat colour field, one line of hand-cut gothic type, hard cuts, nothing else. The
screen behaves like a title sequence that has been paused on a card; you edit it with the keys.

**Concept.** Eight verdicts, eight cards. Each card is a flat red field with the verdict as one or two lines of
condensed display type and a small card number. The screen only ever shows one card. The story of the week is told
by cutting through them, like titles before the film. The hall becomes a cinema because the screen is a title card.

**FIRST GLANCE** (card 1 of 8, red field, bone type; visible words: 7)

```
+----------------------------------------------------------------------------+
|  DEVOXX BELGIUM 2026                                              1 / 8    |
|                                                                            |
|                                                                            |
|        THE HARNESS                                                         |
|        OUTWEIGHS                                                            |
|        THE MODEL                                                           |
|                                                                            |
|                                                                            |
|                                                                            |
|  23 talks                                                    the debate ›  |
|  ·  ·  ·  ·  ·  ·  ·  ·                                 programme  search  |
+----------------------------------------------------------------------------+
```

Type sits left, about 150 px cap height, three lines max. Bottom-left: the count and eight dots (the card index).
Bottom-right: three quiet words. "Text version" is a 12 px line under the dots.

**One step to the detail.** Right/left arrow or click on the right/left half of the card: hard cut to the next
verdict card (no fade; a 40 ms black frame between cards, like a splice). Enter, Space or "the debate ›": the red
field cuts to black and the same verdict stays in place while the card fills in under it: the consensus in one
paragraph, the debate question and its 2-3 sides as short columns with speaker names (each name opens its talk),
the pick for this verdict ("watch first", with `why`), and a line of talks (`talkIds`, sorted by the sort switch).
"search" and "programme" cut to black screens of their own: a single giant input line (search types in 64 px type,
results list underneath, sort switch at the top of the list); the programme as five columns Mon-Fri, each a
scrollable list of times and titles in Europe/Brussels. Esc cuts back to red.

**Signature moment.** The cut. Typography never slides; it is replaced in one frame, with the black splice frame
and the card number ticking. Holding an arrow key runs through the eight cards at 6 per second like a projector
running up to speed; release and it stops on a card. Hover on the verdict text underlines it in bone with a 1 px
rule drawn left-to-right in 120 ms (the only tween).

**Palette.** Field `#B6241C` (Bass red), type `#F3EBDD` (bone), black `#111111` for the detail layer, dots and
small text `#F3EBDD` at 100% (no transparency tricks; use a muted bone `#D9CDB8` for secondary text). Contrast:
bone on red 5.4:1, bone on black 16:1.

**Type.** "Big Shoulders Display" 800 for the cards (150/130 px lines, letter-spacing -0.02em), "DM Sans" 400/500
for everything else: 20 px body, 16 px lists, 12 px footer line. Card number in DM Sans 500 16 px.

**Reduced motion.** No splice frame, no run-up on held keys (one card per keypress), no underline tween. Cuts are
already instant, so the design is nearly unchanged.

**Phone (340x690).** Same card, type 72 px lines, verdict can take 5 lines; dots become a vertical column on the
right edge; swipe left/right cuts cards; "the debate ›" is a full-width bar at the bottom. Detail layer stacks.

**BUILD PROMPT.**
Build `design/menu-screen/title-card/index.html` (+ style.css, menu.js). `#menu` 980x613 (`?shape=phone` 340x690),
centred on `#0A0A0A`. Load `../../menu-variants/data.js`. Rest state: one red (`#B6241C`) card per
`MENU.recap.trends[i]`: title in Big Shoulders Display 800, 150 px, bone `#F3EBDD`, max 3 lines (phone 72 px);
top-left "DEVOXX BELGIUM 2026" 16 px DM Sans; top-right "i / 8"; bottom-left "`count` talks" + 8 dots; bottom-right
"the debate ›", "programme", "search"; "Text version" link to `../../../site/index.html` under the dots. Keys: ←/→
cut cards (insert a 40 ms black frame, hold = 6/s), Enter opens the debate layer (black field, same verdict stays
put): consensus, question, sides as columns (speaker names → `openTalk`), pick with `why`, talks list with sort
(views/likeRate with "few votes" when `thin`/hearts). "search": black screen, 64 px input, results below.
"programme": five columns Mon 5-Fri 9, times in Europe/Brussels. Esc returns. `openTalk(id)`: toast "Walking to
Room N" if `seat`, else "Opening the summary". Content in HTML first, never opacity 0. Reduced motion: no splice
frame, no hold-run. Visible focus rings. Run `node tools/ux/shot.mjs` and `inhall.py`; no console errors.

**Main risk.** Red can look like an error screen or an ad. Avoid it by keeping the red flat and slightly dark (no
gradient, no vignette), by using bone not white, and by never putting a box or button shape on the red: only type,
dots and a 1 px rule.

---

## 2. `two-voices` — One Question, Two Answers

**Outside inspiration:** lenticular prints and Jean-Luc Godard's split intertitles (*Vivre sa vie*, *Le Mépris*),
plus the double-sided posters for *Marriage Story*. The screen is one argument seen from two angles; where you
stand (the cursor) decides which side you read.

**Concept.** The week was an argument. The rest state is a single debate question across the whole screen, with
the two sides' one-word positions underneath, left and right, in two different typefaces (an upright grotesk and a
serif italic: two voices). A diagonal divide splits the field into two colours. Move the cursor and the divide
follows it, widening the side you lean towards and revealing its argument and its speakers. Eight debates; up/down
moves to the next one.

**FIRST GLANCE** (visible words: 12)

```
+----------------------------------------------------------------------------+
|  forest green field          /          chalk field                        |
|                             /                                              |
|   Should coding agents     /                                               |
|   reach tools through     /      MCP servers or plain CLIs?                |
|                          /                                                 |
|                         /                                                  |
|   CLIs.                /                                 MCP.              |
|   Grall · Charrière   /                      Ward · Tzolov · Petruzalek    |
|                      /                                                     |
|  1/8  harness       /                                   watch · all talks  |
+----------------------------------------------------------------------------+
```

The question runs across both fields in one size (about 56 px) and changes colour where it crosses the divide. The
one-word stances ("CLIs." / "MCP.", first word of each `stance`, builder picks it from the data by cutting at the
first full stop) sit large (96 px) at the bottom corners; speaker names 18 px beneath. For 3-sided debates the third
side is a thin stripe at the far right that opens the same way.

**One step to the detail.** Lean: as the cursor crosses 30% / 70% of the width, the leaning side's full `stance`
text (2-3 lines, 24 px) rises under its one-word position and the speaker names become links (each → `openTalk`).
Click the stance or press Enter with it focused: that side's talks list with the sort switch, the verdict's consensus
as the heading, and the pick ("watch first" with `why`) pinned at the top. "watch" (bottom right) = the 8 picks as
a column; "all talks" = search + sort over 205 and the 5-day programme as tabs (the only tabs in the design).
Up/down arrows or wheel: next/previous debate, the divide snaps to centre. "Text version" sits as a 12 px line under
"1/8". Esc returns.

**Signature moment.** The lenticular divide. It is a skewed line (about 12°) that tracks the cursor's x with a
spring (stiffness such that it settles in ~400 ms), so leaning left reveals green and the serif voice, leaning right
reveals chalk and the grotesk voice; the question's letters flip colour exactly at the line (implemented as two
stacked copies of the text with `clip-path` polygons). Keyboard: ←/→ lean the divide in steps of 20%.

**Palette.** Forest `#173F35` and chalk `#ECE8DF`; type on forest `#ECE8DF`, type on chalk `#173F35`; links
`#F28C28` only on the forest side and `#9A4A12` on the chalk side (both ≥ 4.5:1). No third colour.

**Type.** Grotesk voice "Archivo" 500/700; serif voice "Instrument Serif" italic. Question 56 px (Archivo 500 on
chalk, Instrument Serif italic on forest, same size); stances 96 px; argument text 24 px; names 18 px; chrome 14 px.

**Reduced motion.** The divide does not track; it sits at 50% and jumps to 20% / 80% on hover/focus of a side
without a spring (0 ms). Debate changes are instant.

**Phone (340x690).** The divide becomes horizontal (top voice / bottom voice) and tracks the finger's y; the
question at the top in 30 px, stances 56 px at the top-left and bottom-right; swipe up/down changes the debate.

**BUILD PROMPT.**
Build `design/menu-screen/two-voices/index.html` (+ css, js), `#menu` 980x613 (`?shape=phone` 340x690) centred on
`#0B0E0C`. Load `../../menu-variants/data.js`; use `MENU.recap.trends[i].debate` (`question`, `sides[]` with
`stance`, `who[]`, `talkIds`). Two full-field layers, forest `#173F35` and chalk `#ECE8DF`, split by a 12° line
whose x follows the pointer with a ~400 ms spring (←/→ keys step 20%; reduced motion: no tracking, 50% rest, snaps
on hover/focus). Render the question twice (Instrument Serif italic on forest, Archivo 500 on chalk, 56 px) and clip
each copy with `clip-path` to its side. Each side: first sentence of `stance` at 96 px in its corner, `who` names
18 px (links → `openTalk` of the matching talk), full `stance` revealed at 24 px when the pointer is past 30%/70%.
Enter/click a side: that side's talks + the verdict's consensus + the pick with `why`, sort switch
(views/likeRate "few votes" when `thin`/hearts). Bottom-right "watch" (8 picks) and "all talks" (search over 205,
sort, 5-day programme tabs, Europe/Brussels times). ↑/↓ change debate; show "i/8" + verdict title bottom-left,
"Text version" → `../../../site/index.html`. `openTalk(id)` toast as in the brief. Content in HTML, no opacity 0,
focus rings, no console errors; shoot with `shot.mjs` and `inhall.py`.

**Main risk.** Legibility where the question crosses the divide, and a jittery line. Avoid by keeping the divide
away from the question's x-height at rest (it crosses between words), by springing rather than following raw
pointer position, and by capping the divide between 15% and 85%.

---

## 3. `seat-plan` — Two Hundred and Five Seats

**Outside inspiration:** the Kinepolis seat-picker you use to book a seat, drawn with the austerity of Massimo
Vignelli's 1972 New York subway map and the stillness of Hiroshi Sugimoto's *Theaters* photographs (an empty
auditorium, one luminous screen). The talks are the audience.

**Concept.** The screen shows the plan of the hall we are standing in: a small white "screen" at the top and 205
seats in curved rows below, one seat per talk. Seats are grouped by verdict into eight blocks (two rows of four,
with the aisles between them). Sort decides who sits in front: by views, the most-watched talks fill the front row.
At rest nothing is labelled but one line. You pick a seat the way you pick a talk, and then the page walks you to a
real seat. The screen in the lobby is a plan of the room behind it.

**FIRST GLANCE** (visible words: 8)

```
+----------------------------------------------------------------------------+
|                           ┌──────────────┐                                 |
|                           └──────────────┘                                 |
|      ▪▪▪▪▪▪  ▪▪▪▪▪▪▪  ▪▪▪▪▪▪  ▪▪▪▪▪▪▪▪    ▪▪▪▪▪▪  ▪▪▪▪▪▪▪  ▪▪▪▪▪  ▪▪▪▪▪▪▪    |
|     ▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪▪  ▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪    |
|    ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪   |
|   ▪▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪ ▪▪▪▪▪▪▪▪   |
|                                                                            |
|   205 talks. Pick a seat.                                                  |
|                                                     front rows: most seen  |
|   the story   watch first   by day   search                                |
+----------------------------------------------------------------------------+
```

Seats are 14x12 px rounded rectangles in a muted blue, with an 8 px gap, rows gently curved (CSS transform per row
or SVG). Each verdict block has no label at rest; the heading is one sentence in 40 px. Right-bottom: the current
sort as a sentence ("front rows: most seen"). Bottom-left: four words. "Text version" 12 px under them.

**One step to the detail.** Hover or arrow onto a seat: it turns orange and its title, speakers and room appear as
one line of 20 px type in the empty band under the plan (the band is reserved; nothing jumps). Hovering any seat
also lights its whole verdict block one shade and shows the verdict title at the block's front edge. Click/Enter:
`openTalk` (the toast then the walk). Click "front rows: most seen": cycles views → likes ("few votes" seats drawn
hollow) → hearts, and the seats re-seat themselves. "the story": the plan dims to 30% and the intro plus the 8
verdicts appear as a list over it; choosing a verdict lights its block and lists its debate sides (names →
`openTalk`). "watch first": the 8 picks get a white seat-back and their titles line up in the band one per hover;
"by day": five chips Mon-Fri, the plan re-seats to that day's talks in time order (front = morning) and the band
shows the time; "search": an input in the band; matching seats stay lit, others fade to 25%.

**Signature moment.** Re-seating. Changing sort or day sends every seat to its new place along a straight line with
staggered 20 ms delays (FLIP, `transform` only, ~500 ms total), like an audience shuffling; the selected seat keeps
its orange so you can watch where your talk goes. Hover answers instantly with the title in the band.

**Palette.** Hall `#0F1420`, seat `#2C3A5C`, seat hover/selected `#F28C28`, verdict block lit `#3A4C78`, pick
seat-back `#E9EDF5`, text `#E9EDF5`, secondary text `#AAB4CC` (5.8:1 on hall). The white screen shape `#E9EDF5`.

**Type.** "Public Sans" 400/600 throughout: heading 40 px 600, band line 20 px 400, chrome 16 px, footer 12 px.
Numbers for views in "Public Sans" tabular-nums.

**Reduced motion.** Re-seating is instant; the verdict block tint and the band still answer hover. No stagger.

**Phone (340x690).** The plan rotates: screen shape at the top, rows of 10 seats, 21 rows, seats 22x18 px for
thumbs; the band is a fixed strip above the chrome at the bottom; tap selects, second tap opens. Verdict blocks are
vertical pairs.

**BUILD PROMPT.**
Build `design/menu-screen/seat-plan/index.html` (+ css, js), `#menu` 980x613 (`?shape=phone` 340x690) on `#06080E`.
Load `../../menu-variants/data.js`. Draw a hall plan in SVG: a white screen bar at the top, then one 14x12 px
rounded seat per `MENU.talks[]` (`#2C3A5C`, 8 px gap), rows curved slightly, seats grouped into 8 blocks by the
verdict that lists their id in `trends[i].talkIds` (talks in no verdict go in the back rows). Within a block, order by
the current sort (views → likeRate → hearts, cycled by the bottom-right sentence; `thin` seats drawn hollow under
likes). Heading "205 talks. Pick a seat." 40 px Public Sans 600 `#E9EDF5`. A reserved 20 px band under the plan
shows the hovered/focused seat's title · speakers · room, and the block's verdict title appears at the block edge.
Seats are focusable buttons (roving tabindex, arrow keys move between seats). Enter/click → `openTalk(id)` with the
toast from the brief. Chrome: "the story" (intro + 8 verdicts over a dimmed plan; verdict → debate sides, names
open talks, pick with `why`), "watch first" (8 picks with white seat-backs), "by day" (Mon 5-Fri 9 chips, re-seat
to that day in time order, Europe/Brussels), "search" (input in the band; non-matches fade to 25%),
"Text version" → `../../../site/index.html`. Re-seating uses FLIP transforms with 20 ms stagger; reduced motion:
instant. No opacity-0 starts, focus rings, no console errors; shoot with `shot.mjs` and `inhall.py`.

**Main risk.** It becomes a dot chart. Avoid by making the seats look like seats (rounded, a 2 px darker seat-back
line, curved rows, a visible aisle), by keeping every label out of the plan at rest, and by never adding axes,
legends or counts to the plan itself.

---

## 4. `wayfinding` — Rooms Three to Ten

**Outside inspiration:** Otl Aicher's Munich 1972 wayfinding system and the big painted stairwell numerals of the
Kinepolis corridors: flat colour, one typeface, numbers you can read from 40 m. The hall screen is a sign that says
where to go, which is literally its job.

**Concept.** Eight rooms held talks: 3, 4, 5, 6, 7, 8, 9, 10. The screen shows those numerals, huge, on a single
blue field, nothing else. A room is a door: hover one and the room tells you what was said in it this week; pick one
and you choose a talk from that room and walk. The story, picks, programme and search hang off a single thin sign
line at the bottom, the way a corridor sign lists "Toilets · Exit · Bar".

**FIRST GLANCE** (visible words: 6, plus eight numerals)

```
+----------------------------------------------------------------------------+
|                                                                            |
|      3        4        5        6                                          |
|                                                                            |
|                                                                            |
|      7        8        9        10                                         |
|                                                                            |
|                                                                            |
|                                                                            |
|   Devoxx Belgium 2026                                                      |
|   the week  ·  watch first  ·  by day  ·  search                           |
+----------------------------------------------------------------------------+
```

Numerals 200 px tall, white, two rows, left-aligned on a grid with equal gaps; the "10" is the only two-digit one
and is allowed to run wider. Bottom-left: the event name in 24 px and the sign line in 18 px with the Aicher
middle dot. "Text version" 12 px under it.

**One step to the detail.** Hover or focus a numeral: it turns orange, and in the empty right third of the screen
a short room card appears in 20 px: "Room 8 · 34 talks" and three lines: the room's most-seen talk, its pick if a
pick sits there, and the verdict most of its talks belong to. Click/Enter: the numerals compress to a 48 px strip on
the left (a corridor sign you can still use) and the room's talks fill the field as a plain list sorted by the sort
switch (views / likes "few votes" / hearts), each row: time (Europe/Brussels), title, speakers; Enter walks.
"the week": the intro and 8 verdicts replace the numerals (same 48 px strip stays); a verdict expands inline to its
consensus, the debate sides with names (→ `openTalk`), and its pick. "watch first": 8 picks as 8 lines with `why`.
"by day": five numerals 5 6 7 8 9 (the dates) appear in the same style as the rooms (a nice echo), pick one for the
day's list. "search": the field clears to a single input line in 64 px; results in the list style. Esc returns.

**Signature moment.** The numeral as a door. On hover the numeral does not move; instead a 6 px orange rule draws
from under it along the baseline toward the right third in 180 ms, and the room card lands at its end: the sign
pointing you down the corridor. On click the rule stays and the other numerals shrink into the left strip in 240 ms,
so you feel you have walked through the sign.

**Palette.** Field `#1B4F8F` (Aicher-leaning blue, darker for contrast), numerals `#FFFFFF` (7.6:1), active
`#F28C28` (3.2:1 on the blue, so used only for the 200 px numeral and the rule, never for text under 48 px),
list text `#FFFFFF`, secondary `#C9D8EE` (5.4:1). No other colour. Day numerals use the same white.

**Type.** "Archivo" 700 for numerals (200 px, tabular, letter-spacing -0.03em) and 500 for the sign line; "Archivo
Narrow" 400 for lists (18 px) and the room card (20 px). Event name 24 px Archivo 500.

**Reduced motion.** The rule appears full-length at once; the strip compression is a cut; nothing else moves.

**Phone (340x690).** Numerals 120 px in a 2x4 grid, sign line stacked as four full-width rows at the bottom; the
room card appears as a strip below the grid; lists are full-screen with the numeral strip at the top.

**BUILD PROMPT.**
Build `design/menu-screen/wayfinding/index.html` (+ css, js), `#menu` 980x613 (`?shape=phone` 340x690) on
`#07111F`. Load `../../menu-variants/data.js`. Field `#1B4F8F`. Derive the rooms from `MENU.talks[].room`
(numeric rooms 3-10; keep "BOF 1/2" talks reachable via search and by day only). Show the eight numerals as buttons
in Archivo 700, 200 px (phone 120 px), white, on a 4x2 grid, left-aligned. Hover/focus: numeral turns `#F28C28`,
a 6 px orange rule draws right along the baseline (180 ms; reduced motion: instant) and a room card (Archivo Narrow
20 px) shows "Room N · count talks", the room's top talk by views, its pick if any, and its main verdict (count the
`trends[i].talkIds` overlap). Enter/click: numerals shrink into a 48 px left strip (240 ms, cut under reduced
motion) and the room's talks list fills the field: time (Europe/Brussels), title, speakers; sort switch
views / likeRate ("few votes" when `thin`) / hearts; Enter → `openTalk(id)` with the brief's toast. Sign line at the
bottom: "the week" (intro + 8 verdicts, verdict expands to consensus, debate sides with names → talks, pick with
`why`), "watch first" (8 picks), "by day" (numerals 5-9 in the same style; Mon-Fri lists), "search" (64 px input,
results). "Text version" → `../../../site/index.html`. Content in HTML, focus rings, no opacity-0, no console errors;
shoot with `shot.mjs` and `inhall.py`.

**Main risk.** It reads as a mere door sign with no story; or orange text fails contrast. Avoid by making the room
card say something about the week (its main verdict) and by keeping orange for the big numeral and rule only.

---

## 5. `lightbox` — The Screen Is the Search Field

**Outside inspiration:** backlit cinema marquee lightboxes and Wim Crouwel's Stedelijk Museum posters (one
grotesk, one size, a grid, white paper). Also the Experimental Jetset habit of setting one sentence enormous and
trusting it. The screen is the only white thing in the hall; it lights the plants.

**Concept.** A white screen with one sentence in black, as big as it will go: the week's lead verdict as a plain
statement. Underneath, a thin line says what you can do. The trick: the whole screen is a text input. You don't
find the search box, you just type, and your letters replace the sentence at the same size. Search is the
interface; the story, picks and programme are three words at the bottom. Nothing is decorated; the whiteness and
the size do all the work.

**FIRST GLANCE** (visible words: 11)

```
+----------------------------------------------------------------------------+
|                                                                            |
|   Devoxx argued                                                            |
|   about coding agents:                                                     |
|   how to check,                                                            |
|   review and                                                               |
|   contain them.                                                            |
|                                                                            |
|                                                                            |
|   Type to search 205 talks                      ____________________________|
|   the story · watch first · by day       Belgium, 5-9 October 2026         |
+----------------------------------------------------------------------------+
```

The sentence is derived from `MENU.recap.intro` (the builder uses the exact clause "how to check, review and
contain them" and a short lead "Devoxx argued about coding agents:"; no other paraphrase), set at ~96 px, ragged
right, black on white. A blinking 4 px caret sits after the last word only when the screen has focus. Bottom-left
two lines of 16 px; bottom-right the dates. "Text version" 12 px under the dates.

**One step to the detail.** Type anywhere: the sentence is replaced by your query at the same 96 px (shrinks to
64 px past 14 characters), and the matches appear under it as a list in 20 px: title, speakers, room, sorted by
the sort word at the right of the list ("most seen", click to cycle to "best liked" with "few votes" marked, and
"most hearts"). Backspace to empty restores the sentence. Enter on a result: `openTalk`. "the story": the
sentence is replaced by the 8 verdicts as a numbered list in 40 px (the only time more than one statement is on
screen); a verdict opens inline to its consensus, debate sides with names (→ `openTalk`) and its pick. "watch
first": 8 picks as 8 lines in 32 px with `why` on hover/focus. "by day": the five dates as five words in 40 px;
pick one, get the day's list in time order (Europe/Brussels). Esc clears to the sentence.

**Signature moment.** Typing on the wall. Each letter you type lands in the big sentence's place in black 96 px,
with the match count ticking at the bottom ("41 talks") and the list filling below without any transition; the
caret is the only thing that moves. Hover on a result underlines it with a 2 px black rule.

**Palette.** Paper `#F4F3EF`, ink `#111111` (17:1), grey `#5E5E58` for secondary (6.2:1), orange `#C8611A`
(4.6:1 on paper) only for the sort word and the toast. No other colour, no borders, no boxes.

**Type.** "Inter Tight" 600 for the sentence (96/92 px, letter-spacing -0.03em; 64 px when long), 400 for lists
(20 px) and chrome (16 px), 500 for the 40 px lists. Tabular numbers for counts.

**Reduced motion.** The caret does not blink (solid), nothing else animates anyway.

**Phone (340x690).** Sentence at 44 px; the input is a visible 24 px line at the bottom ("Type to search") because
there is no hardware keyboard; results push the sentence up; chrome as three stacked rows at the bottom.

**BUILD PROMPT.**
Build `design/menu-screen/lightbox/index.html` (+ css, js), `#menu` 980x613 (`?shape=phone` 340x690) on `#0A0A0A`.
Load `../../menu-variants/data.js`. Paper `#F4F3EF`, ink `#111111`, grey `#5E5E58`, orange `#C8611A` (sort word
and toast only). Rest: the sentence "Devoxx argued about coding agents: how to check, review and contain them."
in Inter Tight 600 96 px (phone 44 px), top-left, max 5 lines. A visually hidden but focusable input is auto-focused
on `#menu` click/keypress (phone: a visible 24 px input at the bottom). Any typed character replaces the sentence
with the query at 96 px (64 px past 14 chars) and lists matches below in 20 px (title, speakers, room; search title,
speakers, company, keywords, themes, tldr, track), count "N talks" bottom-left, sort word at the list's right
cycling views → likeRate ("few votes" when `thin`) → hearts. ↑/↓ moves through results, Enter → `openTalk(id)`
with the brief's toast. Chrome: "the story" (8 verdicts in 40 px, expand to consensus, debate sides with names →
talks, pick with `why`), "watch first" (8 picks 32 px, `why` on hover/focus), "by day" (dates 5-9 as 40 px words;
day's list, Europe/Brussels times), "Belgium, 5-9 October 2026", "Text version" → `../../../site/index.html`.
Esc restores the sentence. No boxes, borders, gradients or shadows; only type, one 2 px underline on hover. Content
in HTML, focus rings, no opacity-0, no console errors; shoot with `shot.mjs` and `inhall.py`.

**Main risk.** A white screen can glare in the render and the sentence can read as a slogan. Avoid by using the
off-white `#F4F3EF` (not pure white), checking the `inhall.py` picture early, and keeping the sentence a factual
clause from the intro rather than a tagline.

---

## How to choose between them

- Most cinematic: `title-card`. Most argumentative: `two-voices`. Most about this venue: `seat-plan` and
  `wayfinding`. Most radical in the room: `lightbox` (the only bright screen).
- All five put the story one keypress away and keep search, sort, picks, programme and the text link on a single
  quiet line. If a builder finds the rest state creeping above ~12 words, that is the bug.

## The 20 initial concepts

1. Title cards: 8 verdicts as 8 Saul Bass cards, hard cuts, one line each. (kept)
2. Two voices: one question, two stances, a lenticular split that follows the cursor. (kept)
3. Seat plan: 205 talks as 205 seats in a plan of the hall; sort puts the best in front. (kept)
4. Wayfinding: Aicher-style room numerals 3-10; a room is a door to its talks. (kept)
5. Lightbox: white marquee, one enormous sentence, the whole screen is the search field. (kept)
6. Academy leader: countdown 8..1 with the wipe, one verdict per number.
7. End credits: the week as a cast list you scrub with the wheel.
8. Curtain: a flat red curtain parts on hover to show the programme.
9. Station clock: Hilfiker clock, the 5 days as hours, stop-and-go hand.
10. Scoreboard: hand-operated baseball scoreboard, 23 : 20 : 16 ... per verdict.
11. Bookshelf: 205 spines, hover pulls one out.
12. Star chart: talks as stars in 8 constellations.
13. Punch card: a Hollerith card of the week; the holes are talks.
14. Balance beam: a verdict as a beam that tilts to the side you hover.
15. Ticket stub: the programme as a cinema ticket; tear to open a day.
16. Tide chart: attention over the week as one calm line.
17. One-sentence poster: the intro set as a Müller-Brockmann poster, verdict words as links.
18. Radio dial: a Rams/Braun tuning dial for days and rooms.
19. Heap diagram: compact object headers as a bar of bits; the JVM story as the picture.
20. Chalk tally: 205 marks in fives, grouped by verdict.

Seed strings and why each was dropped: `NOTES-cd.md`.
