# wayfinding: log

## t1 (20/10)

Built the screen from the IDEAS.md build prompt: `index.html`, `style.css`, `menu.js`, plus `states.mjs` for the
detail shots (`--extra` writes review shots to `shots/t1/extra/`).

- **Rest:** eight room numerals (3-10) on the blue field `#1B4F8F`, the event name, a sign line (the week, watch
  first, by day, search) and Text version. That is 6 words plus 8 numerals, and every element is in the HTML.
- **Door:** hovering or focusing a numeral turns it orange. A 6 px orange rule is drawn along its baseline to a room
  card in the right third, which shows the talk count, the most-seen talk, the pick and the room's verdict.
- **Room view:** clicking a numeral folds all eight numerals into a 48 px corridor strip on the left (FLIP, 240 ms).
  The rule then points from the strip to the room's talks, which can be sorted by views, likes or hearts.
- **Second screen:** the sign line opens "the week" (the intro and 8 verdicts; each opens to its consensus, debate
  sides with clickable names, pick and talks), "watch first" (8 picks with their `why`) and "by day" (dates 5-9 set
  as numerals, the day's list in Brussels time). "search" opens a 64 px input with sort by best match, views, likes
  or hearts. "all rooms", Esc or a click on the margin goes back.
- **Keys:** arrows move around the numeral grid and through lists. A digit key walks to that room, and 1 means room
  10. "/" opens search. `openTalk(id)` shows the toast.
- **Data choices:**
  - A room's verdict is the trend with the most overlapping `talkIds`. A tie goes to the room's own pick.
  - Talks with few votes rank last under likes.
  - Talks with no video show "no video yet".
  - BOF rooms can only be reached through search and by day.

Fixes after looking at the shots:
- Re-rendering detached the clicked button, so the margin-click check sent sort and day clicks back to rest. The
  margin check now only fires for clicks on body or html.
- The rows read as "3456" and "78910" in the hall. I cut the numerals to 184 px and widened the columns, and moved
  the card to the right edge so "10" doesn't touch it.
- "all rooms" now sits at the end of the sign line, so the other words don't shift when it appears.
- On the phone, the open state no longer collapses the sign line to the top.
- The native search clear button is hidden.
- Scroll areas fade out over their last 28 px, so a cut-off line reads as "more below".

Open: the right third is empty at rest (calm, maybe too empty?); the room card's verdict rests on 1-4 overlapping
talks, so it is thin evidence; the phone has no hover, so a tap opens a room directly.

## t2 (20/10): a sign that explains itself

The critic gave t1 6/10. Their main point was composition: the rest screen was an index of bare numerals with dead
space on the right, and the story sat in a 20 px footer. I rebuilt the rest screen on one 4-column grid. Columns start
at 48 + n*227 and are 203 wide, so column 4 ends on the right margin. Every inner state is now paged, never scrolled.

**What changed, by the critic's fixes:**
1. **Labels.** The header line reads "Devoxx Belgium 2026 / Pick a room to see its talks / Text version". Every
   numeral now has a caption with its talk count and two subjects. A subject is one of the room's themes that has the
   highest share against the whole week and at least 3 talks, using short theme names. Example: "34 talks / testing,
   architecture". "AI agents" leads in most rooms, so ranking by plain count would have printed the same caption six
   times. Ranking by share says what is particular to each room. The aria-label states this ("more than elsewhere
   on ...").
2. **Grid from edge to edge.** Each numeral is a 227-wide cell button with 12 px padding, so the cells tile the full
   width. The empty right third and the empty band under row 2 are gone.
3. **Story at equal weight.** Four equal panels (The week, Watch first, By day, Search) sit on the same columns. Each
   is 29 px bold with a drawn Aicher arrow (an SVG, not a "→" glyph), split by hairlines. Above them, a band carries the
   week's lead verdict at rest: "The harness outweighs the model." with "Still argued: CLI or MCP?". A click opens it.
   Hovering or focusing a room cuts the band straight to that room's card: its most-seen talk and its verdict. There
   is no animation.
4. **Nothing is cut off.** On inner states the header disappears, the numerals fold into the left strip, and the
   panels shrink to one 52 px line at the bottom. In t1 the footer took about 18% of the screen; now it is 8.5%.
   - Lists (room, day, search, picks) fill a page box until it is full (`paginate`), then show "1–6 of 34 talks" with
     Previous and Next. Arrow keys turn the page at either end, and PageUp/PageDown also work.
   - The week is an overview (the intro and an index of the 8 verdicts), then one verdict per page ("1 of 8").
   - `fit()` steps the type down rather than clipping. On the phone it can fold the stance evidence away and set each
     side as one line (its banner word and names).
5. **The debate is staged.** Each side has a 44 px banner word: CLI / MCP, None / Less / Human, No / One layer, and so
   on. These are hand-picked in `HEADS`, each taken from that side's own stance sentence. Names are bold buttons that
   get an orange underline on hover, instead of five underlines in a row.
6. **Hover and focus geometry.** I cut t1's long leader. I also tried an L-shaped leader from the cell down to the
   band. The long vertical for row 1 ran beside the row-2 numeral and looked as if it selected that room, so I dropped
   it. Now the hovered cell gets its own 6 px orange rule along its foot. The rule spans the cell, starts on the same
   left edge as the 3 px focus ring and draws in 180 ms. It never touches the rest of the row.
7. **One width.** Archivo is set at wdth 100 everywhere; the condensed cut is gone. Every small label is now `--soft`
   #D6DFEB (82% white, about 6:1 on the blue), instead of the light blue.
8. **Sort.** The selected key carries a 4 px orange rule. The white pill is gone.
9. **The "10".** The numerals use proportional figures. The "0" of 10 is pulled in by .035em to close the gap left by
   the 1's flag, and each digit sits optically on its column edge with a -.045em offset. On the phone the right column
   now lines up.
10. **Text version.** It moved into the header line at nav size and sits at the end of the bottom line on inner
    states. I did not make it a focus-only skip link, because the brief requires a visible link and a mouse user would
    never see one that only appears on focus.
11. **Phone.** Every room has a caption, so a tap is an informed choice. The band shows the verdict, the gap above the
    nav is gone and the nav is a 2x2 hairline block. Inner states use a 3x2 nav with a short orange marker. The verdict
    pager shows arrows only, and the buttons keep their names for screen readers.
12. **LCD.** `#glass` is a click-through layer inside `#menu` with two effects: a faint ceiling-strip reflection near
    the top (at most 3% white) and about a 7% edge darkening. There is no glow or bloom. I could not lift the black
    level, because the screen has no black and `inhall.py` is outside my folder. The layer goes wherever the menu goes,
    so the real cinema page would get it too. If the port ever draws the screen glass itself, drop the layer.

**Cut:** the #leader element and its geometry code, the room card's "Watch first" line (the pick is one click away
under Watch first, and the "most seen" line says when the top talk is also the pick), every scroll area and fade
mask, and the narrow font width.

**Checks:** `states.mjs` (now `shots/t2`, `--extra` for 25 review shots) covers all 8 verdicts, the verdict talks,
room page 2 sorted by likes, empty and no-match search, the toast, keyboard paging and 7 phone states. No console
errors.

**Open:** the room subject line depends on a theme-lift heuristic. For example, Room 4 reads "Kubernetes, data" even
though 12 of its 29 talks are on AI agents. That is true, but it is a choice. The banner words in `HEADS` are
editorial, so John should read them once. The verdict pages have air between the names and the footer on desktop. I
left it so the footer line stays in a fixed place across all 8 pages.

## t3 (20/10): one poster, one row of doors, one sign strip

The critic gave t2 6.4/10. Their main point was hierarchy: the verdict, the numerals and the destinations competed as
three equal tiers, and the story lost. The rest screen is now three zones on one 8-column grid (100px columns, 12px
gutters, 48px side margins, column n starts at 48 + n*112):
- **The poster (cols 1-6 | 7-8).** It reads "What the week agreed, 1 of 8 / The harness outweighs the model." against
  "What it still argued / CLI or MCP?". Both sit at the same size on the same baseline, as a typographic face-off. The
  size is measured, not fixed: `fitPoster` picks the largest step (60px today) at which the verdict holds two balanced
  lines.
- **The doors.** The eight numerals sit in a single row at 88px, under the label "Pick a room to see its talks".
- **The sign strip.** The four destinations are third in rank: 21px, medium weight, on one top hairline that runs
  across all four.

**By the critic's fixes:**
1. **Re-rank.** The poster now leads, at about 2x t2's size. The numerals went from 140px to 88px in one row (the
   critic offered either one row of eight or 4x2 at 75%). At this size the 4x2 did not fit beside a 60px poster in
   613px. The destinations dropped from 29px bold to 21px medium.
2. **Grid and margins.** The header's cap line sits at about 47px from the top and the strip's baseline at about 50px
   from the bottom. The strip hairline (`--sign-top`, 527px) is the same line in every state; only the type in it gets
   smaller on inner screens. The vertical rules between destinations are gone.
3. **Each room has its own word.** The caption is "14 talks" plus a word from the room's most-seen talk, taken from
   its own title or keywords: Agentic coding, WebAssembly, Sovereignty, Valhalla, Snake, Modular monoliths, AI
   orchestrator, Project Detroit. `roomWord` checks that the word is really in that talk and falls back to the talk's
   first keyword if not. The hover card leads with that same talk, so the two always agree. The theme-lift heuristic
   (and t2's "Kubernetes, data" doubt) is cut.
4. **One band template.** Rest, hover and focus share the same label row, the same two-line block and the same fixed
   height. The right column always uses the poster size. At rest it holds "CLI or MCP?"; on hover it holds the most-seen
   talk's views ("Views on YouTube / 4,616"). The left title steps down from 60px to 28px until it fits two lines, so
   it never wraps into the doors. The room's verdict line is cut from the card, because the room page states it.
5. **One gesture.** Hover is an orange numeral plus a 6px rule that runs exactly the column's 100px. Keyboard focus
   adds a 2px white line under it, still inside the column. The boxed focus ring is gone. Other controls use an inset
   3px ring (`outline-offset: -3px`), so no mark crosses 48 or 932. The destinations and the poster use the same rule:
   orange on hover, and a white line added for focus.
6. **Detail screen.** The face-off words are set at the numeral size (`--num`). `fit()` steps them down (72, 60, 48,
   36) only when the page would overflow, and `fitWords` keeps every word on one line in its column. The sides take
   `margin: auto 0`, so the face-off sits centred with no dead band. Body text is 18px. The side the watch-first pick
   argues for gets the 6px orange rule and carries the pick under its names. Five of the 8 verdicts have one; for the
   other 3 the pick sits on its own line under the sides. "→ The 6 talks it rests on" is the first and largest footer
   action (22px bold, with an arrow). "1 of 8 / Previous / Next" sits on the right in a quiet 16px.
   - **Where I bent fix 6:** 18px stances, 88px words and the consensus do not all fit in 465px. A side therefore shows
     its claim (the stance's first sentence) by default. "Show the evidence" swaps the consensus for the full stance,
     and the type steps down if it must. All three sides of "Review is the new bottleneck" fit with nothing cut. The
     evidence view hides the pick and its rule, because they belong to the plain view.
7. **Affordances.** Speaker names and the pick title have a hairline underline at rest, which turns into a 3px orange
   underline on hover or focus. "All rooms" has a back arrow and now leads the inner strip. The verdict ends with a
   full stop on every screen (poster, verdict page, verdict-talks page, week index).
8. **Corridor strip.** It sits at x=48. The first numeral's cap top is at y=40, the same line as the headline's cap.
   It has a hairline on its right, and the current room is orange. It is dropped on search (`no-strip`), where the
   panel takes the full width.
9. **Orange means "current" only.** On search, the input rule is white and thickens to 4px on focus. The caret is
   white too. Orange is left for the sort key and the active destination. The count and sort moved up beside the
   query, and the pager row now hides whenever a list fits on one page. "valhalla" shows all 6 results with no pager.
10. **The field.** It is ink blue `#0F3463` (white 12.6:1, soft 9.4:1, orange 5.4:1). The `#glass` layer and its top
    gradient are cut; the reflection belongs to the render.
11. **Phone.** The verdict is balanced to "The harness / outweighs the model.", with no widow. "What it still argued:
    CLI or MCP?" sits under it at 17px. "Pick a room to see its talks" now sits right above the numerals on both
    layouts. Phone captions drop the count and show the word only. The hover title is held to two lines too, after a
    three-line title ran into the label. The phone has no evidence toggle: three sides of evidence cannot fit
    340px, so the totem keeps the claims and names.

**Cut:** `#glass`, the "Pick a room" header slot, the vertical hairlines in the strip, the room-card verdict line,
the theme-lift captions, and the search result bar's separate row.

**Checks:** `states.mjs` now writes to `shots/t3`. It adds evidence shots (`x-verdict1-evidence`,
`x-verdict2-evidence`) and phone verdict shots, and shows no console errors. Fixed after looking at the shots: the
three-sided evidence view clipped its footer, search paged 6 results as 1-4, the phone hover title overlapped the
label, and the phone "Sort by" sat 8px outside the margin.

**Open:** the room words in `WORD` are editorial picks from each top talk's title or keywords. John should read them
once ("Sovereignty" for Room 5 is a keyword of "F*ck The System…", not a word in its title). On the phone's inner
strip, the 6px rule on the second row's top edge sits between two labels, which reads slightly ambiguously.

## t4 (20/10): doors first, then the poster, on a locked rhythm

The critic gave t3 6/10. Their main point was that nothing was the hero: the verdict, the question and the numerals
all had the same weight. The rest screen now ranks two things. The doors come first: eight numerals at 128px, cap
height about 90px, about 1.45x t3. The poster comes second: the verdict at 52px, set against the open question at the
same size in a muted tone.

The grid has 8 columns of 89.5px with 24px gutters (column n starts at 48 + n*113.5). Margins are 48px on all four
sides. The masthead's cap line is at 48 and the strip's baseline rests on 565. Every text box is trimmed to cap height
and baseline, so the spacing is exact.

**By the critic's fixes:**
1. **Numerals.** They are 128px on the 8-column grid. At normal width a "10" fits an 89.5px column only at about 80px.
   So the doors use Archivo's condensed cut (wdth 62), and the words under them use it too. Reading text stays at
   normal width. t2 had cut the condensed cut, but the critic's grid needs it back. "10" measures about 88px wide.
2. **Face-off.** "CLI or MCP?" is set at the verdict's size in `--mute` #8FA6CF (6.3:1). Its label is gone.
   - **Where I bent fix 2:** the question starts on column 6, not 7. In cols 6-8 (316px) "CLI or MCP?" sits on one
     line at 52px. The other verdicts' questions need about 250px per line. Every verdict still holds two lines in
     cols 1-5.
   - The other questions are in `ASK`, cut from each `debate.question` (for example "How much review?", "Layers worth
     it?"). The full question is printed under the poster on the verdict page.
3. **Room words.** Each is 20px bold condensed, on one line, all on one baseline. The counts are off the wall; the
   label row and the aria-label still give them.
   - `WORD` is now Agentic, Kubernetes, Sovereignty, Valhalla, Snake, Monoliths, Orchestrator, Detroit, each checked
     against its room's top talk. Room 4 changed from WebAssembly to Kubernetes, because "WebAssembly" is 93px even
     condensed. Both words are in that talk's title.
4. **Rhythm.** The rest screen uses 64px between zones and 32/16 inside a zone, not 48/24/12. One row of numerals is
   limited by width, not height, so the spare height went into equal zone gaps. A 48 unit would have left a band of
   about 110px again.
5. **Chrome.** "Text version" is a quiet 15px item at the end of the strip, on its baseline. The rest screen has one
   small label, "Pick a room". The "1 of 8" and both block labels are gone.
6. **Focus.** Hover and keyboard focus give the same single signal: an orange numeral and a 4px orange rule at its
   foot, across its column, with the word turning white. The white 2px line is gone.
7. **Where I bent fix 7: hover no longer changes the poster.** Six of the eight top talk titles are over 40
   characters, and none holds 52px in two lines. Shrinking them is what broke the template in t3. So the poster never
   changes on hover. The pointed room's facts go in the one label row above the doors: "Room 3, 14 talks. Most seen:
   **State of Agentic Coding**, 3,323 views", with the views in tabular figures. No headline shrinks, and the profanity
   in Room 5's top title stays at 15px.
8. **Clicking zooms in.**
   - Clicking the poster opens verdict 1 with the poster held at the same size and the same position, with no fold
     and no wipe. The debate opens under it, and the top line becomes the pager ("Verdict 1 of 8", Previous, Next).
     The doors leave the verdict screen.
   - In a room, the doors fold into a rail in column 1 at 22px, the strip's size. The current room is a full orange
     plate with the numeral and its word in ink (6.3:1). That is fix 10's one bold use of orange. The room head
     follows the poster template: "Room 8" in white, then "Monoliths" in the muted tone at 52px.
9. **The detail.**
   - CLI and MCP sit on identical neutral hairlines. Orange appears only on the Watch first pick, as a 4px left rule
     and its label. The current strip destination is marked by a white 4px rule, so orange keeps one meaning on every
     screen.
   - Names are plain bold buttons with no underline; they underline on hover and focus.
   - "Show the evidence" is merged into "The 6 talks it rests on", which is the only primary action. That page shows
     each side's full stance over the paged talk list. It gives the poster's room to the evidence, and the top line
     names the verdict.
   - The footer hairline is gone. Previous and Next moved to the top line.
10. **Colour.** The field is velvet ink #0E2347. Orange is used boldly once, on the room plate.
11. **The glass.** `#glass` is back as a click-through layer: a 2.5% black-level lift, a faint ceiling-strip streak
    across the top fifth (2.6% at most) and 14% falloff at the corners. There is no bloom outside the bezel. That
    needs `inhall.py --glow`, which is outside my folder and not part of the shot command. If the cinema port draws
    its own glass, drop the layer.
12. **Phone.** There is 28px of air under the masthead. "CLI or MCP?" is the third poster line, at the verdict's
    27px in the muted tone. The doors are 2x4 plates at 86px, each with its word beside the numeral on the same
    baseline. The grid ends 39px above the strip, and the strip's baseline rests on the bottom margin.
13. **Search.**
    - While a query is typed, every title is set in the muted tone and the matched words are lit white at weight 800.
    - Day and time are separate tabular columns.
    - The rows are 2px tighter, so six results fill the field down to the pager.

**Cut:** the hover poster swap (`bandRoom`), both block labels, "1 of 8" at rest, the talk counts on the wall, the
evidence toggle, the bottom Previous/Next, the verdict footer hairline, orange on the nav, the theme-share helpers
(`SHORT`, `themeAll`, `subj`), and the rail on every screen except a room. The rail did nothing on the week, Watch
first, By day or search screens.

**Checks:** `states.mjs` now writes to `shots/t4`. `6-detail` is the poster clicked and `7-search` is "spring".
`--extra` adds the verdict talks pages, `x-search-valhalla`, `x-kbd-room` and a phone talks page. No console errors.

Fixed after looking at the shots:
- The phone doors ran into the strip.
- The "10" was tracked so tight that its digits touched.
- The talks pages showed zero or one row under the kept poster. The poster now gives way on that page.
- Verdict 5's sides overflowed the footer. Its "claims" are whole long sentences, so a last fit step hides them; the
  heads and names carry that page and the talks page holds the stances.
- The week overview lost its index on desktop. The page-0 poster is now "Eight verdicts.", on one line.
- Search titles with no word match rendered white, as if lit.

**Open:**
- `ASK` (the short questions) is editorial, like `HEADS` and `WORD`. John should read the eight once.
- On the phone, the week overview keeps the intro and drops the index; the verdicts are one arrow away.
- The rest screen now has no cue that the verdict is one of eight. "The week" in the strip and the click both lead
  there.
