# two-voices log

## t1 (20/10): first build

What I did:
- Files: `index.html` (it has a static first frame so the screen is never blank before JS runs), `style.css`, `app.js`,
  `shots-extra.mjs` (6-detail / 7-search shots).
- Rest state: one debate question set twice (Instrument Serif italic on forest `#173F35`, Archivo condensed on chalk
  `#ECE8DF`). Each copy is clipped to its field by a 12° divide, so the question changes voice where the line crosses
  it. Every word gets the same box in both copies (the serif is sized to match the grotesk's total width), so the two
  copies line up. The divide's rest position is searched within ±6% of centre so that it falls between words. The big
  answers ("CLIs." / "MCP.") are short excerpts of each stance (map `ANSWERS` in app.js, with a fallback to the first
  sentence) and are fitted to two lines, up to 112 px. Surnames sit under each answer.
- The divide is a spring (k 190, c 26, settles in about 400 ms). With the pointer it moves away from the cursor, so
  the voice you point at gets wider. Past 62% of the screen that side opens: the full stance, full names as links
  (→ `openTalk`) and "See the talks". The side that gets narrower scales down to 0.4 and the divide crops the rest,
  like a lenticular print.
  Focus on a side or ←/→ (steps of 20%) leans the same way. ↑/↓, the wheel or the chevrons change the debate: the new
  one wipes in from the screen edge. On phone the divide is horizontal: tap leans, a second tap opens, swipe changes
  the debate.
- 3-sided debate (review): the third voice is a forest wedge at the right that opens the same way.
- Chrome (i/8 + verdict, Text version, Watch first, All talks) is copied into every field, so it changes colour with
  the divide too. Only the last field's copy is in the tab order, and when one copy has focus every copy shows the ring.
- Second screen: the chosen field sweeps across the whole screen (a clip-path from the side's polygon to full
  screen). Side = the verdict's consensus as heading, the pick + why, a sort switch (views / likes per 100 views with
  "few votes" when `thin` / hearts), this side's talks, then the rest of the verdict. Watch first = recap intro +
  8 picks. All talks = search over 205 talks (all words must match, accents ignored), a sort switch, and tabs
  All / Mon 5 to Fri 9 (Brussels time). Esc or Back returns to the debate.
- Reduced motion: no tracking spring (snaps), no wipes, no sweep, no transitions.

Fixed while shooting: 24 talks have null views/likeRate (now "no video", sorted last). Answer fitting measured
mid-transition sizes (transitions are now off while fitting). Receding voices had been shrunk until they could not be
read (minimum is now 0.4 and the divide crops the rest). Edge antialiasing showed a sliver under the sheet. The
native search clear button was blue.

Open points: in lean states the grotesk copy has wider gaps between words than the serif copy. Long answers in the
serif voice ("Only where change justifies them.") come out at about 50 px. At rest the divide can still clip one
letter of the question. The phone rest has a large empty forest area.

## t2 (20/10): the answers are the poster

The critic (6.5/10) was right that t1 read the wrong way round: the question was the hero, it was sliced mid-word,
and nothing said the answers were the way in. This turn rebuilds the composition rather than patching it.

Composition
- The question is no longer one sentence set twice and clipped. It is cut into parts (`QSPLIT` in app.js), one per
  voice, and each part is set only in its own field: serif italic on forest, condensed grotesk on chalk. The lines
  are broken in JS against the divide's rest position with a 32 px gutter on each side, so the divide always runs
  through a gutter and never through a letter. Each part starts on the row where the previous one ends (a
  staircase that follows the slant), so it reads in order: "Should coding agents reach tools / through plain CLIs"
  then "or MCP servers?". Only debate 1 is reordered ("plain CLIs" before "MCP servers", so each phrase sits with its
  own side). Screen readers get the question exactly as written (an sr-only h1). Size: 34 px grotesk / 40 px serif,
  about 65% of t1, so it works as a header.
- The answers are the hero. They are fitted to one shared size (up to 260 px) and both sit on one locked baseline.
  The width check runs against the slanted field over the answer's real height, with up to 4 balanced lines. Short
  words are tied with no-break spaces so no line holds "A" or "it." on its own. "CLIs." / "MCP." come out at about
  200 px, with a cap height around 25–30% of the screen. Long answers ("Volume is not security.") fill the field in
  three lines, which closes the empty middle band.
- Entry at rest: under each answer, the surnames at full contrast plus "2 talks" (underlined, with an arrow), in that
  side's own voice, at 30 px serif / 25 px grotesk. The whole voice is one button.
- Rail: all chrome moved to one deep-forest band (`#0F2C25`) under both fields, 58 px tall, 20 px type: ↑ ↓,
  "1 / 8", the verdict title, then Watch first and All talks on the right. The divide no longer crosses any chrome,
  so it can move freely. "Text version" left the rest frame: it is in every second screen's top bar, plus a link in
  the rail that only shows when it has keyboard focus.
- Two colours only. The orange and rust are gone. Interaction inverts (the Watch button, focus rings in the field's
  own text colour) or underlines (tabs, sort, entry, search focus).

Lean
- Divide travel is capped at 35–65%, so the losing side keeps at least 35% of the width. Its question part and its
  voice scale down to fit, with a floor of 0.42. In practice they land at about 0.5–0.7, still a voice, with the
  answer on the shared baseline.
- The leaning side's argument is now its own element at reading size (21 px serif / 17.5 px grotesk), placed
  between that side's question part and its answer. The answer shrinks to make room, not the text. In t1 the
  argument was inside the scaled voice and dropped to about 10 px. A wrapped answer is measured by its ink (the
  union of its line rects), not by its max-width box, so the losing side does not shrink more than it has to.
- Three-sided debate (review): rest at 35.5% / 68%. Leaning gives a side about half the width. Entry type is smaller
  there.

Second screen
- You stand inside the voice you chose. A wedge of the other field stays in the bottom-right corner (10 px at the
  top, 140 px at the bottom, same 12°). It holds "Back to the debate" and the other side's answer, and it is the
  back button (Esc still works). The wedge always sits bottom-right, not on the side the opponent was on, because a
  12° strip on the left edge would be 140 px wide at the top and push the header aside. Watch first and All talks
  use the same wedge.
- Side screen: crumb (n / 8 + verdict title), the answer in its voice with the side's stance beside it, then Watch
  first as the hero (32 px condensed title, meta, an inverse "▶ Watch" button, or "Read the summary" when the talk
  has no seat, then the why). The verdict sentence comes second under it. The pick is removed from the list.
- Index: one metric column. Its header is the sort switch (Views / Likes per 100 views / Hearts, underlined when
  active), so no "views" label repeats under each number. Groups: "This side (n)" and "More on this verdict (n)".
  Titles in the condensed grotesk, so the screen keeps two faces. Lists fade out at the bottom (a mask) instead of
  cutting a row. "Esc" hint removed.
- All talks: one selection idiom. Day tabs and sort are both underlines. Tabs carry live counts for the current
  search ("Fri 9 (3)"). The search field's focus is a 5 px underline, not a rounded box.

Phone (totem)
- No lean on touch: a tap on a field opens that side, and a swipe up/down changes the debate. The fields stack:
  verdict title and the whole question (serif) at the top of the forest field, "CLIs." flush left, the divide in the
  gap, "MCP." flush right on the rail. One answer size, up to about 165 px, so each answer is about 25% of the
  height. The divides are placed in the gaps between the voices with the gutter measured where they are tightest.
- Rail on one row: ↑ ↓ 1 / 8, Watch first, All talks. The verdict title does not fit in that row at 340 px, so it
  moved to the top of the forest field (one line, cut with an ellipsis).

Not taken from the critique, and why
- Question words in the voice of the side they "belong to": only debate 1 has two named options. The other seven
  are cut where the phrase allows, and their words belong to the field they sit in, not to an option.
- Answers at a 35–40% cap height: the answers share one size and the longest one sets it. "CLIs." / "MCP." reach
  about 30% and multi-word answers fill their field in 2–3 lines. Going bigger means unequal sizes across the debate,
  which would take a side.
- On the phone the question is not split between the fields. Split, it would read question, answer, question,
  answer.

Tools: `shots-extra.mjs` now also writes 8-watch, 9-side-3way, 10-day, every debate at rest, and both lean states
with `--debates` (review only, not part of the shot set).

## t3 (20/10): the voice survives the click

The critic (6.5/10) was right that the concept ended at the first click: the side view was a dashboard in a green
frame, and its "Watch first" talk came from the other side. This turn rebuilds the second screen around the voice and
tidies the poster's way in. All 12 fixes are taken; two only in part (see the end).

Rest
- Question: both halves now share one size (grotesk at 1.04 × 1.18 qs against the serif's 1.18 qs, so the x-heights
  match), and "or MCP servers?" sits on the baseline of the left half's second line. The divide splits one sentence.
- Optical balance: the serif answer runs 8% larger and the grotesk dropped from 700 to 600. Blurred in the hall frame,
  CLIs. and MCP. now carry about the same mass.
- The way in is the people: under each answer only the surnames, underlined, with an arrow ("Grall, Charrière →").
  The "2 talks" count is gone (both sides said 2, so it said nothing). The whole voice is still one button.
- Topic: the verdict title left the rest screen. The poster is the question and its two answers. The verdict now
  appears where it explains something: in the side view's "Back to" line and as the heading of a verdict's talk list.
- Rail: left, "Debate 1 of 8" with "Next: <the next question>" under it, so the chevrons have a meaning. Right, one
  confident exit, "All 205 talks →" at 29 px (1.45× t2), with "8 picks to watch first" and "Text version" stacked
  small beside it. Text version is now in the rail on every view, not in each screen's corner.
- Rest position per debate: the divide's rest is picked from a few candidates by which lets the shared answer size
  grow largest (cached per debate). Three-voice debate 2 went from 62 px to about 100 px answers.
- Bug fixed: after a slow layout, rAF's timestamp preceded the spring's last time, the step went negative and the
  divides flew off-screen, so hovering the left of debate 2 opened the right voice. dt is now clamped to [0, 32 ms].

Side view (one step away)
- You stand inside the voice. Its answer stays at rest size (CLIs. at about 216 px), cropped a little by the frame's
  top-left, with the side's stance beside it in the same voice (serif italic on forest, grotesk on chalk).
- Start-here talk: always from this side. It is the verdict's pick when the pick is on this side (with the pick's
  why), otherwise this side's most-watched talk (with its own `watchIf`). CLIs now opens on Grall, not Petruzalek.
  No label: title at 30 px condensed, speaker, room and time, "Watch →" as a text link (no boxed button).
- The short list: this side's other talks, then one label in the voice ("Also on this verdict", serif italic, full
  contrast) and the verdict's talks that sit on no side. The other side's talks are not listed here; they are behind
  the wedge. Rows are added only while they fit, at most 4, so nothing scrolls or fades. "All 6 talks on this
  verdict →" always closes the list and opens All talks scoped to that verdict, with its consensus as the lead.
- Grey scaffolding removed: no "Watch first", "The verdict", "This side (n)" or "More on this verdict" headers, no
  grey regular body text, no condensed roman serif. Two faces: the serif for stance, why and the one label; the
  grotesk for titles, meta and controls.
- Wedge: 84 px wide at the top and 202 px at the bottom (about 14% of the width, 12° like the divide). It holds
  "Hear the other side →" and the other answer as large as the strip allows (MCP. at about 90 px). It opens that side,
  which grows out of the wedge. A three-voice debate shows "Hear the other sides" and both answers. "Back to the
  debate" moved to the rail ("← Back to debate 1" over the question), and Esc still works.
- Sort: one control, the number column's own header. It names the unit ("views ↓") and cycles views → likes per 100
  views → hearts. That also puts the unit over the column once. In All talks the day tabs have their row to
  themselves, and the sort sits over the numbers below a rule.
- Dates never break: "Thu 8, 13:50" and "Room 5" use no-break spaces.

Phone
- The question is split by voice here too: field 1 reads "Should … plain CLIs" then CLIs.; field 2 reads "or MCP
  servers?" then MCP. The small grey verdict eyebrow is gone. If the voices cannot fit, the question steps down a
  size (three-voice debate). If nothing fits, the fields stack from the top instead of being left unplaced (debate 2
  used to render as a pile at the top).
- Rail on two rows: ↑ ↓ "Debate 1 of 8" and "All 205 talks →" on top, "8 picks to watch first" and "Text version"
  below.
- Side view: answer, stance, start-here talk, the rows that fit, and the wedge as a slanted band above the rail.

In the hall
- Chalk lifted from #ECE8DF to #F2EFE7. Against the curtains (mean luma about 110 in the frame) the cream field is
  about 240, so the panel reads as lit.

Taken in part, and why
- "Cut likes per 100 views": the brief requires sorting by views, likeRate and hearts. It stays, folded into the one
  cycling column header instead of a three-tab bar.
- "Faint specular on the bezel": the bezel belongs to the venue render and `tools/ux/inhall.py`, both outside this
  folder. A fake reflection inside #menu would be a UI gradient that the real 3D screen would show twice. Only the
  emissive lift (chalk) is done here.
- Lists with no scrolling: done for the side view. Watch first (8 picks, each with its why) and All talks (up to 205
  rows) are indexes and still scroll, with no fade mask. They are reached on purpose from the rail.
- Search wedge: dropped instead of narrowed. Watch first and All talks have no wedge, because the rail's "Back to
  debate" now does that job and a 40 px strip would only be decoration.

Shots: `shots/t3/` (1–5 from shot.mjs, 6-detail and 7-search from `shots-extra.mjs`, plus the three in-hall
composites). Console: no errors.

## t4 (20/10): one poster in a series of eight

The critic (6.5/10) was right that the rest screen never said what it was, that the series navigation was a web pager
stuck on a poster, and that the question was set like a caption, away from its answers. This turn recomposes the
poster around question-half → answer pairs and turns the rail into the series index.

Rest
- Masthead: "Devoxx Belgium 2026: the week in eight arguments" (grotesk, 17 px, top left). It is set in every field
  at the same place, so when a lean moves the divide across it, the line changes colour and still reads as one line.
- Question halves now sit right on top of their answers (20 px gap, scaled with the voice) instead of in a band at
  the top. The dead band is gone and "or MCP servers?" sits over MCP. The question is set larger: the size is
  picked per debate from 52 down to 32 px (the serif sets it at 1.18x). Debate 1 lands at about 1.4x t3. The rule is
  the largest size that still leaves the answers at 3.4x the question (2x for three voices). Lines are balanced
  (narrowest measure with the same line count) and broken against the narrowest part of the field the half can
  land in, because its height is only known after the answers are fitted.
- Balance: the grotesk answer dropped to weight 460 and the serif got a stroke of 1.8% of the size. I measured ink in
  1-rest: CLIs. 14.2k px against MCP. 15.2k px (t3 was about 13k against 16k). Light on dark reads a little heavier,
  so in the hall frame they read as equal.
- Way in: "Watch Grall + Charrière  2 talks →" and "Watch Ward, Tzolov + Petruzalek  2 talks →". The critic wrote
  "3 talks" for MCP: the data has three speakers but two talks, so the screen says 2. Each surname is kept whole (no
  break inside "van de Ven").
- Lean: a side moves as one unit. Its half of the question scales and moves with its answer, so the question and its
  answer stay together. The argument is now roman (serif 22 px on forest, grotesk 18.5 px on chalk). Italic is
  kept for display only. The same goes for the stance, the why and the picks text in the second screens.

Rail
- Index 01 to 08 (grotesk 19 px, sage at 5.9:1, current one at weight 800 in chalk), with a 4 px chalk bar on the
  rail's hairline over the current number. The bar slides when the debate changes. It is the progress bar, and every
  number is a jump link. The index is one tab stop: ←/→, Home and End move along it, Enter jumps, and ↑/↓ still step
  through the debates. Hovering or focusing a number shows that debate's full question to the right (serif, up to two
  lines, never cut).
- Three items: the index, "8 picks to watch first" (serif italic) and "All 205 talks →" (grotesk 29 px). The rail is
  the poster's forest under one chalk hairline. The third green (#0F2C25) and the third, wider grotesk are gone.
- Text version is a skip link that shows at the top right when it has focus. It comes right after the answers in the
  tab order, not first: `shot.mjs` hovers the first link or button in #menu, and a hidden link there would make that
  hover fail. Second screens add "← Back" in front of the index, and the index also takes you back to any debate.

Detail (a side)
- One reading column on x = 48, the same edge as the mast: the cropped answer (top crop only), then the stance in
  roman, the talk to start with (title, meta with "Watch →" on the same line), the side's other talks (up to 3, as
  many as fit), then "All 6 talks on this verdict →". The other talks get room before the hero's why; the why only
  returns if it still fits. View counts and the sort control are gone from this screen. Sorting stays in All talks.
  That removes the "views ↓" contradiction. The "Also on this verdict" group is gone too, because listing talks under
  a side they did not argue for misled.
- The wedge is the full height and wider (226 px at the top, 344 at the bottom, still 12°). The whole wedge is the
  button. "Hear the other side →" sits on one line above MCP., which now fits at about 140 px (t3: 90).

Search (All talks)
- A forest sliver (26 to 144 px, 12°) stays at the right edge. It is a button back to the debate, so it does a job.
  Watch first gets a chalk one.
- The field is a framed box with a magnifier, a caret in the ink colour, a placeholder, and "Clear" while there is
  a query. It takes the same focus ring as everything else.
- Every result that argued a side carries that side's answer as a tag in that side's typeface ("Measured limits." in
  the grotesk, "Valhalla removes it." in the serif).
- One right edge (x 814) for the field, the rule, the numbers and the rows. The scrollbar is hidden, so the numbers
  line up with the rule.

Phone
- The forest field now ends just under the names (the divide sits 14 px below the block). The leftover space goes
  under the masthead (up to 40 px) and into the chalk field. The question gets 20 px above CLIs. (t3: 8). Answers are
  fitted first, then the largest question (27 down to 20 px) that still fits.
- Rail: two rows on purpose. The index runs across the full width as the first row, and "8 picks to watch first" and
  "All 205 talks →" share the second row at the same size. Not taken: "one row with the index plus All talks". Eight
  numbers at a 34 px touch target plus a readable way to the talks do not fit in 296 px.
- Detail: the wedge band at the bottom had its text at the top of the band (clipped and tiny). It now sits at the
  bottom, so MCP. reads at about 50 px.

Focus: one ring everywhere: 3 px in the field's own ink, 4 px offset, 4 px radius, drawn around the hit target. The
index numbers are 40 x 40 targets. The wedge rings its answer, and the sliver shows an inset ring because a clip-path
would cut off an outline.

Fixed while shooting: the no-break spaces in `tie`/`NB` had been lost (names broke as "Jan / Schrijver"), and they are
now written as  . The rail's watch button shared the `.picks` class with the picks list. The phone rail sized its
grid column to its content.

Not taken or changed from the critique
- Fix 2, "50% chalk" for the other numbers: on forest that is 3.7:1, under the brief's 4.5:1. They use sage (5.9:1).
- Fix 12, "3 px chalk": the ring uses the field's ink, so it shows on chalk fields too (chalk on chalk would vanish).
- Fix 11, one-row phone rail: see Phone.

Shots: `shots/t4/` (1–5 from shot.mjs, 6-detail and 7-search from `shots-extra.mjs`, plus the three in-hall
composites). Console: no errors.
