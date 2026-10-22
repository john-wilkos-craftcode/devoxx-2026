# Shadow Strings: who holds the strings

## The idea

The week's lead verdict is that the harness outweighs the model, so the agent is a puppet and the visitor holds the
bar. The hall screen becomes one lit panel of the hall's own pleated curtain: a lamp behind the cloth, a cut-leather
puppet pressed against it, eight coloured gel strings running from its joints up to a control bar, and the shadow of
a hand lying over the bar. The eight strings are the eight verdicts (the pegs carry their numbers; hover or focus a
peg and the verdict title hangs off it as a tag). Pull a string (click or drag a peg, press 1-8, Enter on a peg) and
the limb snaps up, the lamp slides right so every shadow leans, the puppet is carried into the left 40 % and the
verdict prints on the brightened right 60 %: title, consensus, watch-first pick, the debate with its sides and
speakers, and the verdict's talks with the sort switch. Everything that must be read is HTML type set as cut-card
shadows on the cloth; everything that is light, shadow or leather is canvas 2D. One point-source model drives every
shadow: a thing pressed on the cloth is crisp and true to size, a thing further back is larger, softer and displaced
away from the lamp (the hand is the furthest and softest; a swinging limb goes soft while it moves and snaps crisp
when it settles). The puppet hangs on a verlet rig (limbs as distance constraints, strings as ropes), so taking the
bar swings it with real weight and letting go drops it with a bounce. Nothing moves until somebody takes the bar; at
rest only the flame breathes.

## How to use it

- Pointer: hover a peg for its verdict and watch-first pick; click or drag a peg down to open the verdict; drag the
  bar itself to swing the puppet; "Watch first" and "Programme" are the two hanging cards; the dark slot bottom-right
  is search (results print as you type); "let go" or Esc closes.
- Keys: `1`-`8` pull a string, `W` watch first, `D` programme, `/` search, `←` `→` tilt the bar, `↑` `↓` lift or lower
  it (inside an opened panel the arrows scroll the list instead), `Tab` walks pegs 1-8, Watch first, Programme,
  search, then the open panel ("let go" first); `Enter` on a peg pulls it, `Esc` lets go and hands the focus back to
  the peg or card that opened the panel (from the search field it clears the field and leaves it, so `1`-`8`, `W`,
  `D` and `/` work again at once). Focus ring: cobalt with a bone inner ring, and the focused string lights in its
  gel colour.
- In a verdict: the pick, each debate speaker and each listed talk are buttons that call `window.openTalk(id)`
  (toast "Walking to Room N" when the talk has a seat, "Opening the summary" when it has none). Sort: most seen
  (views), best liked (likes per 100 views, talks under 20 likes listed last and marked "few votes"), most hearts.
- Programme: Mon 5 to Fri 9 October in Brussels time, "all talks", and the "Text version" link
  (`../../../site/index.html`).
- Phone (`?shape=phone`, 340 x 690): the bar has two tiers of four 44 px pegs, the puppet stands full height, the
  headline sits across the lower third, the cards and the search slot are in the foot; a verdict rises as a bottom
  sheet, and in search the slot moves to the top of the sheet beside "let go".
- Reduced motion: no flame breath, no swing, no lamp slide; poses, light and panels cut in.

## What I tried and dropped

- Verdict titles printed along the strings: the strings are steep, so the text would be nearly vertical and unreadable
  from the hall. They became horizontal tags hanging off the peg instead, and the eight picks became a column on the
  right ("Watch first") rather than eight tags on eight strings, which overlapped.
- A fist gripping the bar at rest: at the hand's depth and blur it read as a blob, not a hand (shots t1-t2). The open
  hand with spread fingers lying over the bar reads as a hand from the back of the hall; the fist now appears only
  while the bar is being dragged or steered with the arrow keys.
- The hand following the pointer everywhere: over the panel it smeared the text people were reading, so the pointer
  hand fades out on the right 56 % of the screen and over the phone sheet.
- Per-frame blur filters on every part, the bar and the full-size gel glow ran at 8 fps in software rendering; the
  cloth is now baked and re-baked only when the lamp moves, the glow is drawn at quarter size, the bar is crisp, and
  only parts within a few millimetres of the cloth get no filter at all.
- The panel across the search slot: the slot now sits below the panel (the panel fades out 90 px above the slot),
  so nothing is ever read through the slot.
- A verdict's strings mapped to the limbs by meaning (agent verdicts to hands, JVM to legs): kept loosely, but pegs
  are assigned to joints by their angle from the bar so the fan does not cross itself.
- Blur proportional to any movement: a limb still swaying slowly a second after a verdict opened stayed soft in every
  state shot (the lowered forearm in the t5 programme and search shots), which read as a smudge rather than motion.
  Now only a real swing (above a speed threshold) lifts a part off the cloth; a slow sway stays crisp.

## Landing pass (t5 -> t8)

The build was cut off by a usage limit after t4. The landing pass captured t5 unchanged (48/48 expectations, no
console errors), then fixed what the code review found: `close()` handed the focus back to the search field, whose
focus handler reopened the search, so Escape from a search (and Tab away from an empty one) bounced straight back
into it; arrow keys tilted the bar even with the focus inside an opened list; the debate's speaker-name buttons were
under 44 px on the phone. The headline moved 54 px down onto the lamp's hotspot, between the hanging cards and the
slot, so the lower right of the rest screen no longer reads as an empty quarter. Two states were added to prove the
focus fixes (`search-esc`, `keyboard-search-tab`) and `close-esc` now asserts the rest mode, not only the hint text.
The rig and the eases now run on wall-clock time (up to four 60 fps steps per slow frame, the lerps raised to the
same power): the t6 stills, taken at 16 fps in software rendering, caught every pulled limb still flying a second
after the pull, which a 60 fps browser never shows. With honest timing the capture's drag (90 px in 220 ms, then
let go) flung the puppet under the headline, so the rig got a little more damping (0.975 -> 0.965) and the bar
drifts home after a drag instead of snapping; t8 is the capture of the final version.

## Codex-generated imagery (AI-generated, labelled)

Both images were made with Codex's built-in `image_gen` (gpt-6-astra), one at a time, first try, no retries; the
PNG originals are kept in `assets/` and are not loaded by the page. They were sliced with PIL/SciPy into flat RGBA
WebP silhouettes (leather #2B1407, perforations transparent), one file per connected piece, 3-13 KB each, in
`assets/parts/`. The rivet holes in the pieces were detected automatically and are the rig's joint anchors.

1. `assets/parts-sheet-1.png` (1536 x 1024), eleven pieces -> `p-head, p-torso, p-hips, p-armA, p-armB, p-foreA,
   p-foreB, p-thighA, p-thighB, p-shinA, p-shinB.webp`. Prompt: "ONE image, landscape: a cutting sheet of the separate
   pieces of a jointed shadow-theatre puppet of a slender human figure in a long coat, laid out in a neat grid on a
   plain pure white background, none of the pieces touching or overlapping, generous white space around every piece.
   Exactly eleven pieces: (1) a head in profile facing right, with its neck; (2) a torso in a long coat; (3) a hip
   piece; (4) and (5) two upper arms; (6) and (7) two forearms ending in open hands; (8) and (9) two thighs; (10) and
   (11) two lower legs ending in feet. Each piece has one small round rivet hole near each joint end. Every piece is a
   flat cut-leather shadow-puppet part: a solid very dark brown, near-black leather silhouette pierced with fine
   perforated filigree holes in a delicate lace-and-circuit-trace pattern, crisp clean edges, straight-on view, no
   shading, no gradients, no 3D effects, no shadows, no text, no numbers, no labels, no logos, pure white background."
2. `assets/hand-sheet-1.png` (1536 x 1024), two pieces -> `hand-open.webp` (the forearm's top 42 % faded so the
   pointer hand dissolves mid-cloth) and `hand-grip.webp`. Prompt: "ONE image, landscape: two separate silhouettes
   side by side on a plain pure white background, not touching, with generous white space between them. Left: a human
   hand with its forearm reaching straight down from the top edge of the image, open, fingers gently spread, seen flat
   palm-on, the forearm cut by the top edge. Right: the same hand and forearm reaching down from the top edge, closed
   in a fist gripping a short horizontal straight wooden rod, the rod passing through the fist and sticking out a
   little on both sides. Both are flat cut-leather shadow-puppet silhouettes: solid very dark brown, near-black, crisp
   clean edges, straight-on view, no filigree, no shading, no gradients, no 3D effects, no shadows, no text, no
   labels, no logos, pure white background."

Everything else is code: the cloth (radial lamp, flame halo, cool shade at the top, pleats at the hall curtain's
rhythm and a grain, baked once), the orange gel glow through the perforations (the parts' union, blurred), the
strings with their bloom, the bar and pegs, and the shadow model. If a WebP ever fails to load, each part is drawn
as a cut capsule with holes so the figure still exists.

## Known gaps

- The strings converge on a narrow figure, so two or three of them still cross near the shoulders; a real marionette
  does the same, but a reviewer may read it as untidy.
- The first-glance layer counts 22 words by the tool (headline 10, wordmark 4 as text nodes, two cards, the "8
  verdicts, pull a string" hint), 20 as a person reads it: over the brief's "about 15", by the hint and the second
  card. Kept: the hint is the one line that says what the pegs are.
- An empty search left open with Tab (focus on "let go", then out of the menu) stays open on the shared screen until
  someone presses Esc or clicks; a typed search closes with Esc.
- Opened panels scroll: the debate sits below the fold of a verdict (the states scroll to it), and long lists such as
  Wed 7's 57 talks need scrolling. The measure tool counts the scrolled-out rows as "text outside the menu" (clip 1-3)
  although nothing is visibly clipped.
- Headless software rendering runs the swing at about 16 fps; a browser with GPU canvas is expected to run it at 60.
- The crossing bar on the phone hangs from two cords that are drawn but not simulated; pulling a peg on either tier
  behaves the same.
- No YouTube thumbnails: the design does not need them and the hall shot stays calmer without them.

## after review 1

One fix round on the r1 review (7.1 / 5.9 / 6.5). No new imagery: no Codex run, the same two AI-generated sheets
and parts. Where this section disagrees with the text above, this section is current.

What changed, by issue:

- **r1-1 verdicts not named at rest.** Each peg now carries its verdict's short name as a leather tag that hangs on a
  cord from the top of the cloth down to its knob ("Harness", "Review", "Untrusted", "CVEs", "Leaner JVM",
  "Native & GPUs", "Boundaries", "Judging"), 18 px, in two staggered rows above the bar so no tag ever covers a gel
  string. A tag's bottom edge is its string's gel colour. The tag is part of the peg button (a 90-150 px target
  instead of a 30 px dot); the focus ring wraps the tag. The bar is longer (knobs 80-508 px) and lower (y 146) to make
  room, and the puppet is a little smaller (0.32) and lower. When a view opens the tags are hoisted up out of the
  frame and the pegs draw in to the old spacing, so every string stays left of the opened side; hovering a knob there
  hangs the verdict's name above it, never over the puppet's face.
- **r1-5 what this is.** A kicker above the headline: "DEVOXX Belgium 2026 · 205 talks · 8 verdicts" (Devoxx in the
  wordmark style, X in #F6921E). It replaces the small mark in the corner, so the sign cords no longer cross the
  logo. Under the headline a 22 px line says the first move: "↖ Pull a string to open a verdict".
- **r1-6 static rest, empty band.** An idle demonstration: 4 s after load (and 25 s after the last pointer, key or
  touch) one string at a time is tugged slowly for 3.6 s, its tag is pulled down a few pixels, the knob rings in its
  gel, and the band under the headline prints "String N of 8 · count", the full verdict title and its watch-first
  talk. Any input stops it at once; reduced motion has none. Hover and keyboard focus print the same band. The hand
  shadow no longer lies over the bar at rest (cropped by the frame it read as a smudge): it appears only when a
  pointer is over the screen or the bar is being steered, lighter while it rests behind the tags.
- **r1-2 verdict hidden debate.** A verdict is now three fixed screens, none of which scrolls: (1) the verdict:
  title, consensus, then two cards side by side, "Watch first" (the pick) and "The debate" (its question and who is on
  each side, "Grall, Charrière vs Ward, Tzolov, Petruzalek"); (2) the debate: the question, the sides as two columns
  with each stance's claim in bold and every speaker a button; (3) its key talks with the sort. Every verdict page
  ends at least 2 px above the search slot (measured for all eight). The two cards side by side are the reviewer's
  "fixed screen" within the space; the full stances (200-230 characters, two or three sides) cannot sit on screen 1
  at a readable size, so they are one click away instead, with their question and people on screen 1.
- **r1-3 / r1-4 scroll boxes, small list type.** Lists never scroll on the wall: they are cut into pages of whole
  rows that fit, with a pager (◂, "1–3 of 57", ▸, 50 px targets) beside the search slot, so nothing runs under the
  slot and there is no fade. ← → or PageUp/PageDown turn pages when the focus is in a view. Type: list titles 21 px
  Fraunces, speakers and rooms 17 px, sort and day chips 19 px, eyebrows 17 px, consensus 17 px, stances 16 px; the
  smallest words on the wall are 16 px (was 15). The per-row signal is a bare number; its unit is said once above the
  list ("views on YouTube", "likes per 100 views; few votes (under 20 likes) listed last", "hearts: favourites in the
  Devoxx app before the talk"); "few votes" and "no video" stay on the rows they qualify. "reach" and "likes per
  views" are gone. Watch first shows two picks side by side per page (4 pages), and both of their strings lift.
- **Honesty fix found on the way.** A verdict's `count` (14-23) is the talks behind it, but `talkIds` names only 6-8
  key talks. The old list said "23 talks in this verdict" above 6 rows; it now says "6 key talks" and the eyebrow
  "Verdict 1 of 8 · from 23 talks".
- **r1-7 craft.** Cords no longer cross the wordmark (it moved into the kicker). Strings are thicker (2.8 px) and one
  family: warm gels for the agent and people verdicts, a cool pair (steel blue, teal) for the two Java-platform
  verdicts (5, 6). The open-view tag hangs above the bar, not over the face. The toast is a 28 px Fraunces sign that
  drops into the empty top-left of the cloth (where the tags were hoisted from), no longer on the puppet's feet, and
  stays 3.2 s.
- **r1-8 phone.** Kicker on two lines at the top, knobs drawn 40 px (44 px targets), the hint under the puppet
  instead of over its head, headline 27 px with 16 px clear of the buttons. The phone keeps its scrolling bottom sheet
  (held in the hand, a sheet that scrolls is the familiar pattern; the reviewer liked it), with the same three verdict
  screens; its head row wraps clear of "let go".
- **Other.** "let go" is now a hanging sign in the row with Watch first and Programme; Tab order is pegs 1-8, Watch
  first, Programme, search, let go, then the open view. An open view lets go by itself after 90 s without input (a
  shared wall). The idle demonstration tugs slowly and parts only go soft above a higher speed, so stills no longer
  catch a blurred limb.

Kept on purpose: the headline "Less what agents *can do* than who holds the strings." The reviewer asked whether it
still follows the intro ("less what agents can do than how to check, review and contain them"). It keeps the intro's
first half word for word and turns "check, review and contain" into the image the whole screen is built on; the
literal wording would lose the tie between the story and the puppet. The band, the kicker and the verdict names now
carry the plain facts the headline leaves out.

Known gaps after this round: the first-glance layer is longer than the brief's 15 words (tool count 43: kicker 8,
headline 10, hint 6, the eight names 10, cards and search); the names read as one set and were what the review asked
for. On the phone the knobs stay numbered (no room for eight names at 44 px per target); its band names a verdict
during the demonstration and after a tap. The second tier of phone knobs still sits over two of the first tier's
strings. Debate 2 has three sides, so its debate screen has two pages (1–2, 3).

Verified with `node tools/ux/menu-capture.mjs design/menu-round3/shadow-strings design/menu-round3/shadow-strings/reviews/fixcheck-r1`
(states.json updated: 35 states, new ones for the idle demonstration, each debate screen, debate 2's third side, the
last page of a like-rate sort, Watch first page 4, search paging, a speaker search and PageDown in the programme).

## design pass 2 (21/10)

John tried all three menus by hand. On this one he said: "I liked the physics based toy ... and the visual simplicity
of the menu. It was a bit wonky in that the puppet gets immediately tangled and the numbers on the strings aren't
anchored to their labels ... Not sure about the functionality of the menu." This pass fixes those three points and
adds nothing to the resting screen. No new imagery, no Codex run. Where this section disagrees with the text above,
this section is current.

**1. The puppet can no longer tangle.** The rig is now a clean marionette, not a figure with strings to random joints.
- The eight strings run, left to right, to the left hand, left elbow, left shoulder tip, the back and front of the
  crown, the right shoulder tip, right elbow and right hand. The fan has the same order as the pegs, and no string
  crosses the body. The knee and hip strings are gone: they ran down across the torso. The legs now hang and swing
  from the hips.
- The torso is rebuilt as one rigid piece every step. A triangle held only by distances could fold into its mirror
  image, which was the main source of the "immediately tangled" look.
- It leans at most 0.18 rad from upright.
- Every joint has a hard angle range:
  - Shoulders keep the arms outward, so a hand stays outside its elbow and an elbow outside its shoulder.
  - Elbows bend one way.
  - Hips swing within a small range.
  - Knees bend only backwards.
- The puppet hangs in a cone under the bar. It can swing 44 px aside and rise 34 px (30 and 26 on the phone). Hitting
  the edge of the cone absorbs 65 % of the throw. No part moves faster than 8 px per 60 fps step.
- The bar has weight: it follows the hand closely and drifts home after a let-go.
- The bar's own range is clamped: sideways -110 to +150 px, up 22 / down 24 px, tilt ±0.10 rad at rest. That tilt is
  the most the two rows of name plates can take without touching.
- It is still a toy: verlet with a little damping (0.958). It swings, bounces and settles in about a second, and a
  pull now lifts a hand by about 100 px instead of nudging it.
- Rest pose: arms held out and a little down, legs straight.
- No more ghost limbs. Every part lies flat on the cloth (no depth blur, no speed blur), and both shins use the same
  piece, so both feet point the way the figure faces. The softened far arm and the "doubled" leg are gone.
- Proof. The page measures itself every frame (`window.__rig`): every pair of strings, and every string against every
  limb it is not tied to. The worst result since load is kept on `#menu[data-rig]` as "clean" or "tangled".
  - The states assert `#menu[data-rig='clean']` after each scripted drag: `drag-bar`, `drag-fast-right`,
    `drag-fast-left-up`, `drag-shake` (five hard drags in different directions, shot mid-swing), `drag-slow` (five
    small drags), `tilt-keys`, `tilt-extremes`, `pull-every-string`, `pull-then-drag`, `phone-drag`. All pass.
  - A separate stress run (scratch script, not in the folder) also passed on both shapes and seven random seeds. Each
    run did 40 random drags (2-step and 30-step, three legs each, up to ±350 px), the arrow keys to every extreme,
    all eight pulls in a row, and ten drags while a verdict is open. Result: 0 string crossings, 0 strings over a limb.
  - The first cut of the new rig, before the rigid torso, the cone and the eyelet changes, gave up to 5 crossings and
    6 strings over limbs on the same run.

**2. Number and name are one tag.** Each peg is a single button that the bar carries as one piece.
- The number sits in a medallion on the knob, where its string is tied, ringed in the string's gel colour.
- The name plate is fixed straight above the medallion. Every second plate sits a row higher on a stem in the same gel
  colour, so string, knob, stem and plate's edge read as one line.
- The ceiling cords and the sideways nudges that separated plates from their knobs are gone. When the bar moves or
  tilts, the tags move with it.
- When a view opens, the plates rise away and the numbered medallions stay on their knobs. Hovering one hangs its full
  verdict title from that knob.
- Names are plain two-line findings, never one word: "Harness over model", "Review: the bottleneck", "Untrusted
  agents", "Faster CVE patching", "Leaner, faster JVM", "Native Java & GPUs", "Boundaries first", "Judging, not
  writing". Screen readers get the full title.

**3. Less clutter.**
- Watch first and Programme are plain buttons now: no tilt, no empty cords that looked like missing items.
- The ghost arm and doubled leg are gone (see 1).
- The rest screen holds the puppet with its eight tags, the kicker, the headline, one hint, two buttons and search.
  That is the same set as before, minus the cords.
- Dragging the bar no longer selects text on the page.

**4. Clearer function, no added density.**
- The hint reads "Pull a string to open its verdict".
- The pulled string's limb visibly rises when its verdict opens.
- In Watch first, pointing at or focusing a pick lights its own string on the bar. So the toy and the list stay one
  thing.
- Lists scroll instead of paging two or three items at a time:
  - Watch first is one list of all eight picks. Each row has the verdict's numbered medallion, the talk and its reason
    (two lines). About four and a half rows are visible.
  - Programme and search show five to six one-line rows.
  - A verdict's talks scroll the same way.
  - A soft fade at the foot (and at the head once scrolled) shows there is more.
  - Arrow keys, PageUp/PageDown, Home and End scroll a list from inside it; PageUp/PageDown also work from the chips.
- The pager is gone.
- The opened verdict is unchanged: one verdict, its consensus, its watch-first pick and its debate (both sides one
  click in, now on one scrolling screen).
- In open views the bar draws in further (68 %) and shifts 74 px left, so knob 8 no longer touches the panel's first
  line.

**states.json** keeps every function reachable and adds the drag proofs above, `tags-one-object`, `watch-first-hover`
(a pick lights its string) and scroll states (`watch-first-scrolled`, `search-scrolled`, `story-debate-2-side-3`,
`verdict-5-sorted-liked`). Page-count expectations ("1–2 of 8", "of 57") became count expectations ("57 talks",
"88 talks for") plus `.scroller.more`.

Verified with `node tools/ux/menu-capture.mjs design/menu-round3/shadow-strings design/menu-round3/shadow-strings/reviews/final2`.

Known gaps:
- The rest screen has about ten more small words than before (the eight two-line names), at 16 px.
- On the phone the knobs stay numbered without names (no room at 44 px per target); the band names a verdict after a
  tap.
- The phone's knob 1 sits 12 px from the left edge.
- Watch first shows about four and a half picks at once: the reasons take two lines and were kept.
- Long talk titles in lists are cut with an ellipsis on one line; the full title is in the button's text.
