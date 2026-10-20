# lightbox log

## t1 (20/10)

Built the idea as specified in IDEAS.md #5: `index.html`, `style.css`, `app.js`, `states.mjs` (extra shots).

- Rest: the sentence in HTML (no JS needed), Inter Tight 600 96 px, five set lines, on paper #F4F3EF. Two 16 px lines
  bottom-left, dates + "Text version" bottom-right. No boxes, borders, gradients or shadows.
- The input is invisible and lies over the whole stage, so pointing at the wall shows a grey caret (that is the hover
  state) and clicking puts a black blinking caret there. Typing anywhere (even with focus on a link) lands on the wall.
  The caret holds solid while you type, like an editor; reduced motion never blinks it.
- Search: query replaces the sentence at 96 / 64 / 44 px by length; one-line rows (title, speakers, metric, room);
  orange sort word cycles most seen / best liked / most hearts. Best liked puts trusted rates first, "few votes" after;
  the 24 talks with no view count (views/likeRate null in data.js) sort last as "no count yet". Up/down + Enter.
- Story: 8 verdicts at 40 px; one opens to consensus, the debate question, sides with names as links (each name opens
  that person's talk in the side, else their talk anywhere), and the pick with its `why`.
- Watch first: 8 titles at 24 px (not 32: titles run to 69 chars and must fit one line); `why` + speakers + room in a
  slot below on hover/focus. By day: five day words at 40 px with counts; a day lists its talks in Brussels time,
  showing the time only where a new slot starts (timetable convention).
- `openTalk(id)`: the toast replaces the dates in orange ("Walking to Room N" / "Opening the summary") for 2.8 s.
- Bottom-left line 1 always says where you are and offers the way back (also Esc; Esc from a verdict goes to the list).
- Phone: inline-flowing sentence at 44 px, visible 24 px input with a 2 px rule, nav, dates; status hidden at rest so
  "Type to search" is not said twice; short status texts and "Back".
- Fixes after looking: shot.mjs hovered the input first and timed out when it was a 1 px clipped field (now it covers
  the stage); status spans split by flex gap; null likeRate crashed sorting; pick/why pushed to the bottom left a hole.

Open: white screen in the hall reads strong and calm, but check whether it glares next to the real render lighting;
the day and search lists clip their last row at the stage edge (scroll cue, no fade by rule).

## t2 (20/10): critic 6.3, rebuilt on three sizes

Composition: one type system for every state: wall 96 px (the sentence, a typed query, a verdict), menu 30 px (the
ways in, every list, the debate claims) and small 16 px (dates, counts, names, the way back, Text version). No grey
text anywhere. One accent, `--you` #C0380C, used only for your input and position: the caret, keyboard focus and the
toast. The "most seen" sort is now an ordinary hairline link.

- Rest: the sentence is broken by meaning ("Devoxx argued about / coding agents: / how to check, review / and contain
  them."), with line-height 0.99 so no descender touches the next line. A permanent cap-height caret in the accent
  follows "them.". It holds solid for 2.4 s when the screen wakes, then blinks between full strength and 20% (dimming,
  not vanishing, so it can be seen at any moment from across the hall). Under reduced motion it stays solid.
- Second level: "Search 205 talks  The story  Watch first  By day" at 30 px in ink, hairline-underlined, as the one
  menu row. "Search 205 talks" is the field's label. Pointing at the wall thickens its underline, and keyboard focus
  on the hidden field draws the focus ring around it. The old two-line status block is gone.
- Bottom band: the menu row and a two-line small block on the right (dates, or the way back such as "All 8 verdicts",
  over "Text version") share the last baseline (`align-items: last baseline`).
- Link grammar: a 0.06em underline at rest, 0.14em on hover or when current (aria-current or aria-pressed), and keyboard
  focus as a 3 px square outline in the accent. No radius. Result rows are underlined only on hover or arrow-key
  selection.
- Verdict: the title is a 96 px sentence with a full stop. Under it are the debate question (small) and one column per
  side, headed by the stance's own first sentence at 30 px with the names as inline links ("A, B and C"). It ends
  with "Watch first: <title>" at 30 px, pushed to the bottom. The consensus left the verdict page: it now shows under
  the story list when you point at or focus a verdict.
- Fix 3 said to head the columns "CLI" / "MCP". That would mean writing new labels, and the brief says never invent,
  so the heads are the first sentence of each stance from data.js. The JVM verdict's stances have no short opening
  claim, so that verdict shows the full stance at the small size.
- Search: the query stays at 96 px (a long one scrolls so its end and the caret stay visible; no shrinking sizes).
  Under it, title at 30 px, then "first speaker + N" over "Wed 7, 44 min" (Room N dropped), then the metric in ink.
  Lists stop at the last row that fits whole (`fitList`), so the wall never shows half a title; the rest scrolls.
- Watch first: 8 titles at 30 px on full width; on hover or focus, the speakers, length and `why` show at the small
  size at the bottom. By day: opens on Mon 5 straight away (no empty state); day words at 30 px with counts.
- Phone: the field sits right under the sentence (accent caret before the placeholder), with The story / Watch first /
  By day as a 30 px stacked list below it, and dates + Text version at the foot. In other states the field moves to
  the top and the ways shrink to one row.
- Fix 9 (emissive panel): the paper is cooler (#F3F5F4) with a soft backlight falloff to #E7EAE9 at the corners, done
  inside `#menu`. Bloom into the bezel happens outside the canvas, in the 3D page or `inhall.py --glow`, both outside
  this folder, so the port should handle it there.
- Cut: the numbered verdict markers, the grey colour, the orange sort word, the status line ("Verdict 1 of 8, from 23
  talks") and the 64/44 px query sizes.
- `states.mjs --all` writes extra states (story, picks, days, 3-sided verdict, toast, empty and long query, phone
  states); I checked them in the scratchpad. No console errors.

Open: rest leaves ~130 px of air between the sentence and the menu (deliberate, but it could take a bigger lead);
search shows only 3-4 results at 30 px; the emissive falloff barely shows in `inhall.jpg` without `--glow`.

## t3 (20/10): critic 6.5. One door, three marks, a typeface with a voice

Composition: the screen is now three fixed bands on every canvas and in every state: the wall (whatever is being
said), the field (the one door, always in the same place, the only home of the caret), and the menu row (the other
ways in, the date or your place, Text version). Only the wall changes its text, so rest, verdict, search and lists
feel like one object.

- Fix 1: the 48 px field (caret, then "Search 205 talks" on a full-width 2 px rule) sits under the sentence, with
  The story / Watch first / By day as 30 px secondary links under it. The sentence ends on its full stop. The caret is
  drawn by us (4 px, orange, placed by measuring a mirror span) and lives only in the field. Typing anywhere still
  lands in it. The 96 px query on the wall is gone: your letters stay in the field at 48 px and the results take the
  wall, so the caret never jumps.
- Fix 2: one hover/focus state: an ink block with paper text (`box-decoration-break: clone`). The orange focus ring is
  gone. The field's hover/focus state is its rule going from 2 to 4 px. Orange now means only "your typing goes here":
  the caret and the search result that Enter will open (a 4 px bar in the left gutter, fix 9).
- Fix 3: the menu row is weight 500 in every state. The current section gets a 4 px underline (aria-current).
- Fix 4: the verdict's talk line is "Start with <title>", the same words as on the rest screen.
- Fix 5: the question is 30 px in the one grey (#5C5D59, 6.4:1), with a gap before the claims. Speaker names are plain
  ink and invert on hover/focus. The talk title is the only underlined thing in the content area. The mono slot says
  "← 1 / 8 →" (←/→ keys too). A verdict title steps down 96, 84, 72, 64 px only if the argument would not fit.
- Fix 6: Familjen Grotesk (Google Fonts; Söhne, Diatype, Unica and GT America are not free to load) at -0.03em for
  display. Compared on a sheet with Inter Tight, Schibsted, Host, Funnel, Hanken and Golos. It has the most voice, and
  it is narrow enough to keep "how to check, review" at 96 px. JetBrains Mono (the IntelliJ face) for every number:
  dates, minutes, views, "23 talks", "1 / 8", times, "+3 more".
- Fix 7: the dead band is gone. Under the sentence: the Start line, the field, then the row. The meta is one mono line
  ("Belgium, 5–9 Oct 2026", 19 px), on the row's baseline. Text version is a mono link at the far right.
- Fix 8: rest shows "Start with State of Agentic Coding  Daniela Petruzalek, 48 min" (the critic wrote 51 min; the
  data says 48). It is built from the pick of the lead verdict, not hard-coded.
- Fix 9: search rows are one column: a title capped at two lines, then name (grotesk) and "Fri 9  51 min  6,147 views"
  (mono) under it. A mono "+N more ↓" line counts the rows below and updates as you scroll. Count and sort sit at the
  field's right end ("6 talks, most seen first"); on the phone only the sort word shows.
- Fix 10: underlines are 2 px (4 px current) with offset 0.2em and `skip-ink: none`, so a line runs whole under 30 px
  descenders instead of breaking up.
- Fix 11: the paper is a faintly warm lit white (#F6F5F1, with a radial falloff to #ECEAE4), and the caret has a
  small bloom (the only glow). Spill onto the bezel and curtains is outside `#menu` (3D page / `inhall.py --glow`),
  so I left it to the port. I tested a dark ground (`?ground=dark`; `shots/t3/x-dark-inhall.jpg`). It reads more like
  an LCD, but I kept white as the default for three reasons: the idea is literally the lightbox, the white panel
  that lights the plants. Near-black with one orange accent is the brief's listed AI tell. And among the five
  concepts, this is the light one. The switch is one attribute, so John can pick.
- Fix 12: phone breaks follow the meaning ("Devoxx argued / about coding / agents: / how to check, / review and /
  contain them.", using `br.w`/`br.p`). The Start line fills the space above the foot.
- Cut: the full-stage invisible input, the 96 px query, the focus ring, underlines on list items (lists invert on
  hover/focus), the "Back to the start" step out of a verdict (The story link or Esc does it), the room column.
- Checked: all states of `states.mjs --all` in the scratchpad (story, picks, days, 3-sided verdict, sort, toast, empty,
  long query, and every phone state). No overflow, no console errors.

Open: rest is fuller now (sentence, Start line, field, row). It reads in the hall, but watch for density. Should the
placeholder be 500 or 600? (500 now, so it sits under the sentence.) Dark versus white is John's call.

## t4 (20/10): critic 6.4. Two layers, two marks, and the week's three arguments as a marquee

Composition: the screen now has two layers. The argument is on top: the sentence and its "Start with" talk, which
belong together because they change together. The instrument is below: the field, then the three ways in. The insets
are the same on all four sides (46 px, measured optically from the cap line of the wall and the baseline of the ways).
The rhythm is fixed: sentence, 31, Start (title over mono meta), 32, field, rule, 18, ways. The critic's suggested
rhythm (80 px insets, 48/40/16/24 gaps) adds up to about 710 px on a 613 px panel, so I kept its order and ratios and
cut the sizes: the wall goes from 96 to 84 px.

- Fix 10, the signature: at rest the wall cuts every 9 s between the week's three arguments, each with its own Start
  talk (the pick of that verdict). All three are set in four lines and share line 1 ("Devoxx argued about"). The cut
  is a hard vertical edge that wipes left to right in 1.2 s (clip-path, no fade, no glow), so line 1 never seems to
  move and only the argument changes. Wording: the intro's own clauses joined to the verdict titles ("...the JVM: a
  runtime that keeps getting leaner and faster.", "...architecture: clear boundaries before services."). Nothing is
  invented. It holds while the pointer is on the sentence, while anything in the screen has focus, outside rest, or
  in a hidden tab, so a talk never changes under your hand. Reduced motion: no cuts, it stays on the first argument.
  The first argument is plain HTML, so nothing is blank while JS loads.
- Fix 2, one link language: the ways are plain ink at 38 px, the strongest thing you can click after the sentence.
  The only underline left is the link inside a sentence ("Start with <title>"). Mono meta, Text version, the sort
  word and the way back are plain. Hover and focus are always the ink block, now with 0.12em on each side
  (horizontal box-shadows only), plus a 0.07em margin so the block keeps the word space before it. The section you
  are in, the pressed day and the search row Enter will open use the same block ("this one"). Focus on an item that
  is already inverted adds a 2 px ring, so the keyboard is never lost.
- Fix 3, the field: placeholder in grey at 30 px (below the ways). Its grey is #625F59, not the critic's #8A8781,
  because #8A8781 is 2.9:1 and the brief sets 4.5:1 for all text. Now 5.1:1. The orange slab is gone. In its place
  is a true 2 px caret at cap height before the S, solid for 2.4 s when the screen wakes, then blinking. It holds
  still while you type and is solid under reduced motion. The rule spans only the field (a fixed 580 px on every
  screen), so it reads as an input and not as a divider. Orange now marks only the live caret.
- Fix 4 and fix 1: the order is Start, field, ways at every size. The layout ranks them, not extra styling.
- Fix 5, the room: the default ground is a white with lower emission (#E8E5DE, falling off to #E0DDD6), with a
  faint diagonal glass sheen (a 10% white band, about 2.5% brighter) over the whole panel. I kept white rather than
  the dark ground. This idea is the lightbox, and near-black with one orange accent is a tell the brief names.
  `?ground=dark` still works. I could not do the light spill onto the curtain and ivy here: it happens outside
  #menu (in the 3D page, or `inhall.py --glow`) and outside this folder. Leave it for the port.
- Fix 6, phone: sentence at 40 px in 5–6 lines broken by meaning ("Devoxx / argued about / coding agents: / how to
  check, / review and / contain them."), then Start (label, title, meta), the field, and the ways stacked at 32 px
  in the thumb zone. The foot reads "Devoxx Belgium, 5–9 Oct" and "Text version" (the year is dropped so both fit
  in 292 px). The old dead band is gone. The architecture argument is 5 lines, so its slide keeps one line of air
  above Start: the slides share one cell, so the field never moves during a cut.
- Fix 7, verdict: each claim is a door to its side's first talk (ink block on hover). The question is #4A4844
  (7.3:1). The sides share rows (subgrid) and the claims are bottom-aligned with `text-wrap: balance`, so the last
  lines of the claims and the names line up across columns. Names never break inside (nbsp). The names stopped
  being links (the claim is the door now, which cuts the link count). The tiny mono pager became "Verdict 1 of 8
  Next" in grotesk at 30 px. It sits in the field row's right slot, which always holds the context of the wall:
  the dates at rest, the count and sort in search, the day count in By day, the position in a verdict. ← → still
  page through verdicts.
- Fix 8, search: titles use `text-wrap: balance` (no more "the JDK" orphan). Speaker, day, minutes and the count
  are one mono line. "N more, scroll" sits under the last whole row. The selected row is the ink block, not the
  orange gutter.
- Fix 9: en dashes in "5–9 Oct" and in titles at render time (" - " becomes " – "). The foot reads "Devoxx Belgium,
  5–9 Oct 2026". Long titles with a subtitle show their main title on the wall ("Taming Microservice Overload"); the
  full title is the accessible name.
- Cut: the orange slab and the gutter bar, the caret's bloom, every underline except one, the name links in a
  verdict, the arrows in the pager and in "+N more ↓".
- Checked: `states.mjs --all` (all states plus `s-arg-2/3`, `s-wipe`, and their phone versions) in the scratchpad.
  No overflow and no console errors.

Open: the 84 px wall leaves the right fifth of the panel empty. That is deliberate (left-aligned and ragged, with
the mono meta holding the right edge), but a critic may want the sentence wider. Showing the marquee in a still
needs `s-wipe.png`. Spill light onto the room belongs to the port.
