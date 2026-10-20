# title-card: log

## t1 (20/10)

Built the first full version from the BUILD PROMPT in IDEAS.md (idea 1, "The Week in Eight Cards").

- **Rest**: one flat Bass-red card (`#B6241C`) per verdict, bone type, no boxes on the red. Verdict in Big Shoulders
  Display 800, fitted by JS to 150 px max / 3 lines (phone 72 px / 5 lines). All 8 verdicts fit at 150 px on laptop.
  Card 1 is written into the HTML so the screen reads before JS runs.
- **Deviation**: verdicts are set in sentence case, not caps. Caps would mangle "CVEs", "GPUs" and "JVM" and read
  worse from the back of the hall; Big Shoulders lowercase keeps the hand-cut gothic feel.
- **The cut**: ←/→, a click on the left/right half, a dot, or a swipe on the totem cuts the card with a 40 ms black
  splice frame. A held arrow key runs up from about 3 to 6 cards a second (projector run-up). Reduced motion: no
  splice, no run-up, so one card per key press. The only tween is the 120 ms underline on the verdict when you hover it.
- **One step away** (hard cuts to black, Esc or "back to the cards" returns):
  - *the debate* (Enter, click on the verdict, "the debate ›"): verdict, consensus, the question, sides as columns
    (lead sentence, then speaker names as links to `openTalk`, then the rest of the stance), the pick with `why`, and
    the verdict's talks with the views / likes / hearts sort switch ("few votes" when `thin`, ranked after the trusted ones).
    ←/→ keep cutting through the verdicts on this screen too.
  - *search*: 64 px input; typing any letter on the card opens it too. Empty query = all 205 talks under the sort switch.
  - *programme*: five columns Mon 5 to Fri 9, grouped by Brussels start time (phone: day switch + one list).
  - `openTalk(id)` shows the toast "Walking to Room N" (seat) or "Opening the summary".
- Fixes after looking at the shots: the debate overflowed on the 3-sided verdict (names hidden below the fold), so I
  tightened the type, moved names directly under each lead sentence and stacked the sort switch under the count;
  dropped the hover underline from the line-box bottom to just under the baseline; centred the verdict on the totem.
- `shoot-states.mjs`: 6-detail, 7-search, plus 8-programme and 9-toast (`phone` arg for the totem versions).

Open points: the debate's talk list scrolls and cuts the last visible row; the "From / writing code / to judging it"
break leaves "From" alone on a line (text-wrap: balance).

## t2 (20/10): from web hero to printed poster

Critic t1: 5.8/10. The main points were that the rest state was a web hero with a dead right third, the furniture was generic, it was unclear how to reach the talks, and the identity was lost one click in. Rebuilt the composition, not just the details.

- **Type**: Big Shoulders + DM Sans became one family, **Archivo**, used for both display and furniture. Its width axis (62-125) is the
  point: `plan()` in menu.js tries every way of breaking the verdict into 2-4 lines and sizes the block to the height. It then
  sets each line's width axis so the line runs exactly margin to margin. If a short line can't reach the margin even at 125,
  it gets set a little bigger (wood-type poster logic, never letter-spacing). The score rewards height fill and penalises
  mixed widths and sizes. Card 1 is "The harness / outweighs / the model", filling about 70 % of the frame. Leading is .92,
  plus .1em under any line with descenders, so the g of "outweighs" no longer meets the d of "model". Card 1's setting is
  written into the HTML for a slow or failed JS load.
- **Eight inks** (red, ultramarine, burnt orange, green, magenta, petrol, olive, violet; bone on each is 5.2:1 or more). The hall
  screen visibly turns over: each card holds 9 s. **The hairline is the pager**: 8 segments, and the current one fills over the
  hold. It pauses on hover or focus. With reduced motion there is no turn-over and the segment is drawn static. Hollow dots,
  the duplicate "1 / 8", the caps eyebrow and the half-card click zones are gone.
- **Bottom band**, on one baseline under the hairline: "01—08 · 23 talks, 2 sides" on the left. On the right, "Watch the debate →"
  at 38 px, with programme and search at 16 px. The whole verdict opens the debate too. Hover draws an 8 px bone bar under the
  descenders. Focus is a 3 px bone outline offset by 8 px. The signature is lowercase: "devoxx belgium 2026 — what the week argued".
- **Debate**: the card's ink becomes a header band holding the number, the verdict, the consensus and "Watch first" (with
  `why`). Each side is a 34-40 px condensed statement, then one plain line of names (underlined only on hover) and one
  sentence. The JVM verdict's sides have no short claim, so there the names are the headline and the stance sits under them.
  The talk list is a numbered table with no truncation, the watch-first talk is left out of it, the metric has its own column
  header, and a fade shows while there is more below.
- **Every dark page has an ink foot strip** (back to card NN plus its title, the pages, the text version). The toast takes over
  that strip ("Walking to Room 8"), so it can't cover content. Emoji are stripped from titles everywhere.
- **Programme** is now a schedule board: day tabs in display type, a bold time rail, a fixed room column, full titles
  wrapped, and the speakers. ←/→ change the day.
- **Phone**: verdict anchored at the top and fitted (3 lines for card 1, no orphan "The"), and the vertical dots are gone. The
  totem has height to spare, so the debate's question waits above the hairline pager. "Watch the debate" is a full-width bone bar.

Fixes I changed or skipped, and why:
- *Fix 2* (merge "23 talks" into the call to action): kept "23 talks" as the info line on the left instead. The debate lists
  the 6-8 key talks in `talkIds`, not all 23, so "Watch the debate · 23 talks" would promise talks the page can't show.
- *Fix 12* (only "popular / newest"): the brief requires sorting by views, likeRate and hearts. There is no date to sort by
  "newest" either. I kept all three but named them for what they measure (from `MENU.signals.note`): most watched, best liked
  (likes / 100 views, "few votes" when thin), and most awaited (hearts before the talk).
- *Fix 10* ("now" marker on the current half-day): the conference was 5-9 October and is over, so there is no "now". The
  board shows one full day at a time instead of five columns.
- Some cards set one line bigger than the others ("agents as" on card 3, "From" on the phone's card 8). That is the
  scaled-line rule at work. The ratio penalty keeps it modest.

Shots: shots/t2 (shot.mjs, plus shoot-states.mjs for 6-9 and their phone versions; `cards` also writes all 8 posters).

## t3 (20/10): one poster system, up close and far away

Critic t2: 6.8/10. The main points: the system broke after the poster, the hall card was weaker than the phone card, there was
dead space, the route to the talks was weak, and the programme had no tie to the story. This turn rebuilt the composition
around one object: the card. The debate is that card up close, and every talk carries its card's number.

- **Rest card (980 and 340), the same story at both sizes**: deck row at the top ("Devoxx Belgium 2026 / What 205 talks
  argued, in 8 verdicts" against a 52 px **1/8** bib), then the 3 px pager, the fitted verdict, the debate question directly
  under it, and a full-bleed **bone band of doors** at the foot: "Watch the debate →" | Programme | Search the talks, at 30/24 px
  and 64 px high. On the totem the band has two rows (the CTA, then Programme | Search). "01—08", "23 talks, 2 sides" and the
  hairline are gone.
- **No void**: the verdict sits on the question. When the verdict can't use all the height (its longest word stops it at the
  margins), `fitVerdict` grows the question into the rest. It picks the largest size (up to 1.6x, 1.45x on the totem) that
  doesn't cost the verdict any size or lines. Card 1 is now 133 px over a 47 px question, which is the critic's "a third". The
  phone fitter takes 3-6 lines and favours wide settings, so most totem cards run one or two words a line at width 110-125.
- **Hover = feedback on the target**: the 8 px bar is gone. Pointing at or focusing the verdict turns the CTA cell black with
  bone type (the door it will open). Every door inverts under the pointer or on focus. While paused, the current pager segment
  thickens from 3 to 8 px.
- **Debate = the card shrunk**: an ink header with the verdict fitted by the same rule (one or two lines, about 88 px), the 2/8 bib,
  and the consensus. The bone band returns as "Watch first" (title, speaker and room, why) | "All N talks →", which opens search
  filtered to that verdict. On black: the question in display type, and per side a statement in wide 800, one line of evidence
  (the stance's next sentence, up to its first semicolon), and "N talks:" followed by the speakers as links. It fits 980x565
  for all 8 verdicts, with no scroll and no fade. The talk table moved out of the debate into the filtered search, which has
  the sort switch.
- **The story on the board**: a coloured square with the card number (02, 05…) on every talk of a verdict (its talkIds plus
  the talks its sides cite: 58 talks, 4 of them carry two squares), in search and the programme. "Only the argued talks" filters
  both. Search rows get a "▶ Watch" box ("Summary" when there is no seat), and under the results an "Argued in" strip of the
  related verdicts in their inks (by tag, or by text when no result is tagged).
- **Working screens**: all text bone, 15 px and up, no grey on black (hierarchy by weight). Fades removed everywhere. The toast no
  longer takes the strip: it replaces only the back label, and a 4 px bone line fills along the strip's top edge over the 2.6 s
  "walk" while the page links stay. The phone foot strip is one row (←, the other pages, Text version) and no longer covers content.
- **The display rule** (now written at the top of style.css): the verdict is the only fitted line. Every other display line (bib,
  question, doors, statements, day tabs, query, time rail) is Archivo 700-800 at one width, 115, never condensed. Text is
  Archivo 400-600 at normal width.

Fixes I changed or skipped, and why:
- *Fix 8* (render as light): I only added the part that is the glass itself, a very faint reflection of the ceiling strip
  across the top of the panel (`#menu::after`, 4 % white). I skipped the bloom on the type and the field: the brief's taste rule
  says "cut gradients, glows", and a glow costs edge contrast on the real screen. The red spill on the bezel and curtain is
  outside `#menu`, so it belongs to the 3D page or to `tools/ux/inhall.py` (which already has `--glow`). I can't write there.
- *Fix 1* ("23 talks →" in the band): dropped, as in t2. `count` covers talks the data doesn't list. The debate's "All N talks"
  counts only the talks the page can actually show.
- *Fix 4* (pager "underneath" the numeral): the pager runs full width under the deck row, not at the width of the bib. At bib
  width the 8 segments were too small to hit or to read as a timer.
- *No fade on fixed panels*: the debate, card and search head fit. The programme (32-66 talks a day) and long result lists still
  scroll, now with a hard edge and no fade. A day of the programme cannot fit 1080p at a readable size.
- Mixed widths remain in some verdicts ("The harness" at 112, "outweighs the model" at 62). That is the fitted-line rule: the 3-line
  setting needs more height than the band and question leave.

Shots: shots/t3 (shot.mjs; shoot-states.mjs for 6-9 and their phone versions; inhall, inhall-phone, 6-detail-inhall).

## t4 (20/10): two voices, one colour code, one feedback move

Critic t3: 6.5/10. The main points were: three typographic voices fighting on the rest card, mixed widths inside one verdict,
a colour code nobody is taught, a pager and brand too small for the hall, doors that read like a cookie banner, a detail
page of four stripes, and a toast that signalled the wrong way. This turn rebuilt the type system and the rest card
around two voices, and the debate around the shape of its data.

- **Two voices** (written at the top of style.css). The verdict is always Archivo 800 at the extra-condensed cut (62),
  one size per card, ragged left: poster, totem and debate header alike. `plan()` now tries every line break at that
  one width and keeps the biggest single size that fits the height and the longest line (a lone short word on its own
  line costs 8 %). The per-line width fitting and the "question grows into the gap" logic are gone. Everything else
  in display type (questions, doors, days, numbers) is the wide cut (115).
- **Rest card**: three zones. (1) A deck row: "Devoxx Belgium 2026" in the wide voice at 21 px plus "205 talks, 8 verdicts"
  (computed from the data), with **eight numbered chips 01-08 in the eight inks**. The current chip is outlined in
  bone and a bone fill with the ink number runs through it over the 9 s hold. It freezes while paused and is solid
  bone with reduced motion. The "1/8" bib and the hairline pager are gone. (2) The verdict, centred in its band, so a
  width-capped verdict gets equal air above and below instead of a gap on one side. (3) The doors: **the question is the
  main door** (a bone block holding the question in wide 800 at 29 px, then "Watch the debate →" at 18 px). Programme and
  Search are quiet doors beside it, bone type under a 3 px bone rule, that fill with bone on hover. The free-floating
  question is gone. Card 1 at 980: verdict 131 px in two lines. Totem: 4 lines at about 73 px, the door, then the two
  quiet doors in a row.
- **The debate is two zones**: the ink header (bone chip "02" plus the verdict on one line at 67-80 px; then the
  consensus with "All N talks of this verdict" as a quiet door under it, and **Watch first** as one bone door on the
  right: title in ink, then "Speaker, Room." in bold and the why in black at 16 px), then black with the question and
  **the positions on one axis**. Each column is weighted by its talk count (`minmax(236px, Nfr)`) and topped by a bone
  bar holding the tally ("3 talks"), so the bars together read as one segmented axis from the first position to the
  last. "N talks:" moved out of the name line into the bar. All 8 verdicts fit 980 x 565 with no scroll (checked by
  measurement). The totem tries 4, 3, then 2 lines for the header verdict and keeps the biggest that leaves 16 px of
  the black zone showing above the strip, so the cut reads as "more below", never as a sliced line.
- **One feedback move everywhere**: what you point at or pick inverts. Bone doors go black; quiet doors, chips, search
  rows, programme slots and the "Argued in" verdicts go bone. Search rows lost the outlined "▶ Watch" boxes: the whole
  row is the button, and a single ▶ before the number marks talks with a seat.
- **Toast**: the black strip turns bone, "Walking to Room 8" / "Opening the summary" replaces the back link at the same
  16 px as its siblings, with no arrow, and a 5 px black line fills along the strip's foot over the 2.6 s walk (no line
  with reduced motion). The row, slot, name or pick you opened stays inverted while it runs (`openTalk(id, src)`;
  `openTalk(id)` still works).
- **Foot strip** on every dark page: black with a 2 px bone top rule. The verdict's colour appears only in the small
  "02" chip of the back link. On the totem the strip labels are shortened ("Debate") so "Text version" fits.
- **Removed**: the top-edge sheen on `#menu` (flat fields only), the bib, the hairline pager, the "go" boxes, the SVG play
  icon, and the question-growing fit.

Fixes I changed or skipped, and why:
- *Fix 3* (non-current chips "at reduced opacity"): kept them at full ink. A dark ink at reduced opacity over another
  ink drops its bone number below 4.5:1 and blurs neighbouring codes (orange on red). Full-strength chips with bone
  numbers teach the code better. The current chip is the only bone one.
- *Fix 5* (column width strictly 1 : 2 : 3): strict proportion gives the 1-talk column 150 px, too narrow for its claim
  and evidence. The columns use `Nfr` with a 236 px floor, so the order of weight stays visible and the text stays
  readable. I added no separate axis end labels: the first and last positions' claims are the axis ends.
- *Fix 6* ("a 6-to-10-word reason"): the reason is `picks[].why` from the data, kept whole. Cutting it to a fragment
  would rewrite the source. It is now 16 px black on bone at full contrast, three lines at 980.
- One content rule added for fit: a side's evidence sentence over 140 characters now ends at its first ", then / while /
  because / so" clause after 60 characters (like the existing semicolon rule). This only affected verdict 3's single
  position.
- *Fix 10*: the debate's foot strip is black too, not ink. The debate already has its ink header, and a second ink band
  at the foot would bring back the stripe stack.

Shots: shots/t4 (shot.mjs; shoot-states.mjs for 6-detail, 7-search, 8-programme, 9-toast and their phone versions;
inhall, inhall-phone, 6-detail-inhall). shoot-states runs with reduced motion, so the toast's walk line is not shown.
