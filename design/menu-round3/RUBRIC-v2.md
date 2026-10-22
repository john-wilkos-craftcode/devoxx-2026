# Scoring rubric v2: hall-screen menu, round 3

v2 (21/10) fixes the procedure after a methodology review found that v1 set every score from a flaw quota (anchors defined by
flaws, a forced list of 8 issues, measured misses used as caps), so every design landed at 6-7 whatever was fixed.

For independent reviewers. Judge the picture in the hall (`*-hall.jpg`, plus the phone, reduced-motion, motion-strip
and state shots, and `facts.json`), not the code and not the LOG's promises. Score each criterion separately, 1-10, from
the anchors in section 1, and quote the evidence (file name plus what you saw) for every score. Where a number below is missed, log it in the review with its measurement. A miss lowers a score only when it breaks a
function or makes the main short text (headline, first move, verdict names, search label) unreadable; otherwise it goes
in the polish list and never moves the score. Scores are your own reading of
the picture: do not look at other reviews first.

**Viewing context (John's decision, 21/10):** the screen is judged as a render on a laptop, not as a real wall seen from
8 m. The picture to judge is the 1920x1080 hall shot viewed at normal size on a laptop or monitor (a browser window
about 1440 px wide shows the menu canvas at roughly 1.1x its CSS size). There is no standing-distance reading: ignore
any "from the back of the hall" wording in the brief, and do not mark text down for being unreadable "from 8 m".

Screen facts used throughout: the canvas is 980 x 613 CSS px (the 3.6 x 2.25 m hall screen, shown as a render). The phone totem is 340 x 690 px, held close. Designers may use Codex
`image_gen` for imagery (brief); judge the imagery on what it adds in the render, never on how it was made.

## 1. How to score (read this first)

You place the design on a scale by comparing it with reference pictures and by describing what is on screen. You do NOT
count flaws: a design with several small flaws can sit high if its idea and its resting screen are outstanding, and a
flawless but dull one stays low.

**Calibration references** (look at both first; they are in `design/menu-round3/calibration/`):
- **5**: `live-navy-board-5.jpg`, the programme screen the hall has today. Competent and useful, a kiosk UI, nothing to remember.
- **6.5**: `title-card-6.5.jpg`, an earlier attempt ("The Week in Eight Cards"). A clear idea and bold type, but type-and-shape only; the earlier critics scored it 6.5.
There is no picture for 9; use the descriptions.

**Anchors** (describe what is on screen; half points only, never finer):
- **1-3** Broken or ugly: unreadable, clipped or overlapping, errors visible, or a function missing; the eye has nowhere to go.
- **4-5** Competent but generic or templated: it works, but you have seen it a hundred times; type, colour and layout look assembled from defaults.
- **6** Good but unremarkable: clean and usable, nothing you would remember or photograph.
- **7** A real idea, strong at rest; the opened states are competent but generic, the look does not fully carry into them.
- **8** The idea survives every click: you would photograph it and describe it to a friend; the opened states carry the same world and shapes; only small flaws.
- **9** Holds its own beside the best public-screen work you know: one art direction from the resting screen through every opened state and both shapes, one memorable moment, nothing to subtract.
- **10** Best in class: an awards jury would single it out for one idea executed with discipline.

Do not hand out 7+ for "nice colours" alone or for restraint alone; do not reward restrained-to-dull or assembled-looking
work; do not reward spectacle that costs legibility. Give the score the picture earns, then report in three separate lists:

1. **Blockers** (no limit): a function missing or unreachable, the main short text unreadable, content clipped or
   overlapping, console errors, a bug that produces a wrong result (for example a wrong sort order).
2. **Lifts** (at most 3, ranked): the changes that would move the design up a full level. Concrete, keep the identity.
3. **Polish** (any number, short): everything minor. Never affects a score.

## 2. Criterion 1: exciting and amazing (look at the hall shots)

Why these checks: a visual-appeal judgement forms in about 50-500 ms and then colours judgements of usability and
credibility (Lindgaard; NN/g aesthetic-usability); Norman's visceral level is the immediate reaction to how it looks;
award juries separate "custom with one signature moment" from template work. Seen as a thumbnail and at laptop size.

1. **50-ms impression.** Look at the full hall shot for one second, then look away. Can you name the mood and one thing you saw? A shrug is a finding.
2. **One focal point.** Exactly one element or region wins the eye first (not two competing, not none). Squint (section 3) shows it as a single dominant mass.
3. **Real visual substance.** There is imagery, light, depth or texture that carries meaning, not only type and rectangles. Round 2's main failure was "type and shape only".
4. **Colour world, not palette.** A deliberate dominant colour (about 60 %), a supporting one (about 30 %), one accent (about 10 %), as a rough guide to see whether one colour clearly leads. Colours relate by a visible logic (analogous, complementary, one temperature plus one counter-note) rather than a rainbow of equals.
5. **Colourful yet calm.** Saturation and variety exist, but the eye can rest: large calm fields, saturation spent where meaning is, no vibrating adjacent saturated hues.
6. **Depth and light that read as in a room.** The screen glows, has a lit surface, a layered foreground/background; it does not look pasted onto the wall. Check the hall composite at the screen's edge: bezel, glare, colour spill, brightness against the room (very bright pure white is harsh in a dim hall).
7. **Type with personality and a system.** At most two families plus weights; a clear scale (about three sizes, at most two elements large); the display face has a voice that fits the story, body type is plain and sturdy. Type and image feel made together, not stuck together.
8. **A signature idea.** One thing a visitor would describe to a friend ("the one where ..."). It is specific to Devoxx 2026 and to these talks, not portable to any other event by swapping the title.
9. **Concept fits the content.** The form says something about the story of the week (eight verdicts, debate, 205 talks) rather than decorating it. Metaphors earn their place; clichés (ticket, popcorn, film strip, terminal, radar) only if transformed.
10. **Craft at pixel level.** Aligned edges, consistent radii and strokes, no banding or muddy gradients, imagery cut cleanly, no stretched or low-res artwork, text never over busy image without a calm backing.
11. **Rhythm and surprise.** Scale contrast and pacing across the screen (big, small, empty, dense) that create rhythm; at least one deliberate surprise (a crop, an overlap, a scale jump) inside an otherwise ordered layout.
12. **Delight on interaction.** Hover, focus, open, search, sort and close feel considered in the state shots: a peak moment (a verdict opening, a result arriving) that is memorable and an ending (closing, returning) that is clean. Peak-end: people remember the best moment and the last one.
13. **Motion with intent.** The 4-frame strip shows motion that has a job (guide, reveal, confirm) and arrives with easing, not linear; ambient motion never distracts from reading and nothing flashes.
14. **Memorability test.** After a minute on other things, can you redraw it from memory in three shapes and a colour? If you cannot, it is generic.

## 3. Criterion 2: easily readable and functional

Brief ladder: first glance about 15 words or fewer (what it is, the story in one idea, the obvious first move); one
step away: eight verdicts, the watch-first picks, search; two steps away: debate, talk list, programme, text link.

**3a. Numbers to measure** (use `facts.json` and zoom on the screenshots)

- **Contrast.** Normal text 4.5:1 or more, large text (24 px / 18.5 px bold or more, in CSS px) and UI parts or focus rings 3:1 or more (WCAG 1.4.3, 1.4.11). Check text over imagery at its worst spot, hover and focus states, and the placeholder; "nearly 4.5" fails (not rounded).
- **Smallest font.** Every word of body text at least 14 px (brief). Count how many words are at the smallest size: a screen that needs the minimum for its main content is not designed for a screen read at a glance.
- **Glance text sizes.** The headline, the first move and verdict names are far larger than the minimum: judge them in the hall shot at laptop size.
- **Choices at first glance.** Count distinct clickable or readable items competing at rest. Hick (decision time grows with the number and complexity of choices) and Choice overload argue for few at first glance and a highlighted recommendation; Miller's 7 plus or minus 2 is not a cap on menu items, so judge by grouping (chunks) and by what is one step away. The eight verdicts count as one chunk when they read as one set.
- **Words at first glance.** About 15 or fewer on the glance layer (brief). Count only words set at 24 CSS px or more in the 3-second shot (use `facts.json` and zoom); the eight verdict names count as one chunk; small secondary labels (under 24 px) are logged but do not count against the number.
- **Target size.** Laptop: any control at least 24 x 24 CSS px (WCAG 2.5.8) and the main choices clearly larger (about 28 px or more). Phone totem: at least 44 px (brief), with gaps between neighbours.
- **Margins.** TV guidance keeps primary content inside a safe margin (about 5 %, or 60 pt top/bottom and 80 pt sides on a 1080-high TV, about 34 px top/bottom and 41 px sides on this canvas). Is anything essential on the very edge, next to the curtain or ivy in the hall composite?
- **Line length and density.** About 65-75 characters at most for any paragraph; no wall of text on the first two layers.
- **Responsiveness.** Feedback to a key or click within about 0.1-0.4 s (Nielsen response limits; Doherty); nothing that makes the visitor wait without a sign of progress.

**3b. Procedures a reviewer runs on screenshots**

- **Five-second test (Maze/NN/g method).** Open the 1920x1080 hall shot for exactly five seconds (count aloud), then close it and, without looking back, write answers to three questions: *What is this? What is the story? Where would you go first?* Then add: *where is search? where is a talk worth watching?* Record what you got right. Do not hint to yourself beforehand. A visitor who has slept two hours must find the story, a talk and search; a miss on any is a functional finding.
- **Squint / blur test.** Blur the shot (about 5-10 px at screen size, then 20 px; or squint). At light blur the groups and the one dominant element should still read; at heavy blur there must be one focal mass and no accidental second one (a loud colour that was not meant to lead). If the blur shows a different hierarchy than the content's priority, the visual hierarchy is wrong.
- **Laptop-size test.** View the 1920x1080 hall shot at normal size on a monitor, then once shrunk to about 1000 px wide (a small laptop window). Read the headline, the first move, three verdict names and the search label. What cannot be read at either size is a defect.
- **Keyboard test.** In the Tab strip, is the focus ring visible, 3:1 or more against its surroundings, and not clipped? Is the order logical (story, watch first, search, then the rest)? Can every function in the brief (story, watch first, search, sort, open a talk, programme, text link) be reached and left with keys alone, without a trap? Is the current focus visible from 5 m, not a hairline? Focus should be clear from across the room (scale, inverted colours or a thick border).
- **Reduced-motion test.** Compare the reduced-motion shot with the normal one: content identical, nothing missing or invisible, large scaling and panning gone (these are vestibular triggers), replaced by fades or none. Auto-moving content longer than 5 seconds needs a pause (WCAG 2.2.2); no flashing more than 3 per second (2.3.1). The motion strip must not hide content in an "opacity 0" start.
- **Empty and edge states.** Look at the search-with-no-results shot, a talk with no video (`views: null`), a `thin` like rate ("few votes"), and the long-title worst case. Is there a clear, kind message and a next step, with no broken image or blank panel? Is the like-rate signal shown honestly (never ranked alone when thin)? A sort that puts talks with no data above talks with some is a blocker.
- **State walk.** For each function in the brief, check its `states.json` shot and its `expect*` result: the story opens to consensus and debate (question, both sides, who, their talks); watch-first shows 8 picks with reasons; search shows results as typed; sort by views, like rate, hearts; open-a-talk shows the toast ("Walking to Room N" or "Opening the summary"); programme by day (Mon 5 to Fri 9 October); text link. A missing or unreachable function is a blocker: name it; it lowers the readable-and-functional score.
- **Phone totem.** Not a squashed copy: a portrait layout with its own hierarchy, thumb-reachable controls at least 44 px, no horizontal scroll, the same first-glance answers.

**3c. Observable readability and function checks**

1. The glance layer (text at 24 px or more) answers what, story, first move in about 15 words or fewer, counting the verdict names as one chunk.
2. The most important information is visibly first (size, position, contrast), the ladder in the brief is obeyed.
3. Nothing is visually overloaded: a clear, calm region exists, and spacing groups related items (proximity) and separates unrelated ones.
4. Labels are plain words a visitor knows ("Search", "Watch first"), not internal jargon or cryptic icons.
5. Interactive things look interactive (affordance and signifiers), and the current state (selected, open) is obvious.
6. Every function is reachable in two steps or fewer from the first screen, as the ladder specifies.
7. Back-out is obvious from every opened state, and closing returns to a sensible place.
8. The text is real, in HTML; legibility never relies on a generated image of lettering.
9. Hall composite: text stays legible against the curtain-wall glare, the screen edge is not touching anything essential.
10. No console errors, no content hidden if JS is slow (per `facts.json`).

**Opened states and lists (John's decision, 21/10: "opened lists can be plain, as long as the visual design is clear and cohesive").** A list of 20-205 talks may be a plain, well-structured list: scannable rows, a
clear sort control, a visible way out, about 20 px or more type. Judge it against list best practice (rows aligned, one
line each where possible, the sort visible, long lists paged or scrolled with a cue). What lifts a design from 7 to 8 is
that the list still belongs to the same world as the resting screen (same palette, type, imagery language); a list that
looks like a generic web page next to a rich resting screen is a Lift, not a Blocker.

## 4. Criterion 3: UX heuristics, adapted to a screen in a room

Each check gives the heuristic, then what to look for. Cite the shot.

1. **Visibility of system status (Nielsen 1).** Where am I, what is selected, what happened after my click or key? A visible current state and a response in about 0.1-0.4 s; the toast on open-a-talk says where the visitor is going.
2. **Match with the real world (2).** Language is the visitor's: "what people said at Devoxx", not field names; verdict titles read as findings, and the headline is faithful to `MENU.recap.intro`. Counts shown (205 talks, 8 verdicts) are the real ones.
3. **User control and freedom (3).** A visible way out from an opened verdict, search, sort or programme; Escape works; a visitor who walks away is not stranded in a deep state (the screen is a shared public display).
4. **Consistency and standards, Jakob's law (4).** One interaction language everywhere; search looks like search, a list looks like a list. Be novel in look, familiar in operation: the screen may be inventive, but people carry expectations from other products.
5. **Error prevention (5).** Sensible defaults (a watch-first pick already highlighted, one obvious first move), no ranking on thin data without a caveat, no state that dead-ends.
6. **Recognition rather than recall (6).** Options visible, not hidden behind unlabeled gestures or memorised keys; key hints on screen (outside `#menu` allowed). Nothing the visitor must remember between layers.
7. **Flexibility and efficiency (7).** Mouse, touch and keyboard all work; an expert can type a search immediately; a novice can just pick. Shortcuts accelerate, they are not required.
8. **Aesthetic and minimalist design (8).** Every element is signal: the test is "what would be lost if I removed this?". Decoration that carries no information is noise; negative space has a purpose. Clarity wins over flourish. A busy screen can still comply if every item is relevant; a bare screen can fail it if it does not say what it is.
9. **Error recovery (9).** Zero results explains itself and offers a next step; a missing video gives a summary instead of a dead end.
10. **Help (10).** A first-time visitor needs no explanation; any hint is short, in context, and goes away.
11. **Hick and Fitts.** Few, grouped choices at first glance with a recommended one marked; targets large and close to where attention already is; the primary move is the biggest, nearest and clearest target.
12. **Gestalt grouping.** Proximity, common region and similarity make the groups (verdicts together, picks together, search apart) readable without borders everywhere; unrelated items are not visually equal neighbours.
13. **Von Restorff (isolation).** The thing that matters most differs from its peers, and only that thing; if three things shout, none does. Not by colour alone.
14. **Visual hierarchy.** Scale, contrast and grouping give the order; at most about three contrast treatments and two large elements; hierarchy matches the information ladder in the brief.
15. **Emotion over the pyramid (Walter, Norman).** Functional, reliable, usable first, delight on top: delight that sits on a broken base (surface delight) counts for little; delight on a solid base (deep delight, flow) counts for a lot. All three of Norman's levels: visceral (looks), behavioural (works), reflective (means something about Devoxx 2026, tells its story, is worth remembering).
16. **Aesthetic-usability effect, as a guard.** A beautiful screen can hide usability faults, and observers praise looks over function. Do the tests in 3b before you settle on the Criterion 2 score; do not let looks raise it.
17. **Motion principles.** Motion explains cause and effect, guides the eye, and stays short: about 100 ms for feedback, 200-300 ms for a substantial change, up to about 400 ms for a large movement on a big screen, never linear, ease-out for things arriving; staggered reveals set hierarchy; frequent motion shorter and subtler. Anything about 500 ms or more drags. Decorative parallax and scale pulses are non-essential and must switch off under reduced motion.

## 5. Failure patterns to penalise, and what originality looks like

Penalise when you can name the pattern in the shot. Round-2 critics said the same: "assembled", "pasted onto the wall",
"restrained to the point of dull". Most of these lists are practitioners' checklists, not experiments: look for the
absence of decisions (everything treated the same).

- **Generic cards.** Identical rounded cards with icon, heading, text in a row or bento grid; cards inside cards; the same radius on everything; a thick coloured stripe on one side of a card; thin border plus soft shadow on the same box.
- **Neon-on-black and glow.** Near-black with one neon or cyan/purple-to-blue gradient accent, radial halos behind content, glowing borders, gradient text on headings or numbers.
- **Decoration without purpose.** Grid-line backgrounds, glass blur panels, striped fills, pulsing status dots, blinking cursors, decorative "01 02 03" numbering with no sequence, oversized icon tiles outweighing the thing they introduce, imagery hidden under near-opaque overlays.
- **Assembled-looking type and colour.** One default family (Inter or similar) for everything with sizes barely differing; a small label above every heading that repeats it; an oversized italic serif as a shortcut to "editorial"; cream-and-terracotta as a default; tight crushed letterspacing; palette tokens that were never tested together.
- **Dashboard and kiosk feel.** KPI-style hero numbers, tables, filters and tabs as the first thing seen; a "tool" instead of "a thing in a room".
- **Cliché cinema or tech.** Ticket stubs, popcorn, film strip, terminal prompt, radar sweep, unless transformed into something not seen before.
- **Spectacle over legibility.** Ambient motion behind text, low-contrast text on busy imagery, more than about three type sizes competing, large display type in a thin weight that disappears when the picture is shrunk to a laptop window.
- **Placeholder-grade imagery.** Generic illustrations or mascots, stock-looking AI art with no relation to the content, text rendered inside generated images, broken or stretched thumbnails.
- **Generic copy.** Vague superlatives, forced slogans ("Not X. Y."), labels that repeat each other.

**What originality looks like instead** (from the awards-versus-template comparisons and AI-slop critiques):

- Decisions visible in every layer: a palette built around the event, type chosen for its voice and set at varied size, weight and spacing, spacing that varies by group rather than uniformly.
- One signature, memorable interaction or moment (not five effects), motion choreographed to the content.
- Specific content designed into the layout: the eight real verdicts, real debates, real talk thumbnails (graceful when absent), not placeholder structure.
- A strong constraint pursued fully (a single material, scene, or grid logic) so the whole screen feels made by one hand, and held across states and both shapes.
- Imagery that says something about the subject: a lit scene, a texture, a cut-out with intent; AI-generated art is fine when it is directed (one style line, consistent), cleaned up, and labelled.
- Readability preserved because the type does the information work and the imagery does the mood work.

## 6. Sources (pages opened and read for this rubric)

Heuristics and laws
- https://www.nngroup.com/articles/ten-usability-heuristics/ : the ten heuristics and their definitions, section 4.
- https://www.nngroup.com/articles/aesthetic-minimalist-design/ : signal versus noise, "clarity will always win over visual flourish", progressive disclosure.
- https://www.nngroup.com/articles/aesthetic-usability-effect/ : attractive designs are judged easier; caveats that it masks problems in testing.
- https://www.nngroup.com/articles/theory-user-delight/ : Walter's hierarchy (functionality, reliability, usability, pleasure) and surface versus deep delight.
- https://www.nngroup.com/articles/response-times-3-important-limits/ : the 0.1 s, 1 s and 10 s limits.
- https://lawsofux.com/ : the list of laws and one-line definitions (Gestalt, aesthetic-usability, choice overload, chunking).
- https://lawsofux.com/hicks-law/ : fewer options, highlight a recommended one.
- https://lawsofux.com/fittss-law/ : target size, spacing and distance.
- https://lawsofux.com/millers-law/ : 7 plus or minus 2 is not a menu-item cap; chunk instead.
- https://lawsofux.com/jakobs-law/ : familiar patterns free up attention.
- https://lawsofux.com/law-of-proximity/ : nearby items read as a group.
- https://lawsofux.com/von-restorff-effect/ : the one distinct item is remembered; use sparingly and not by colour alone.
- https://lawsofux.com/peak-end-rule/ : design the high point and the ending.
- https://lawsofux.com/doherty-threshold/ : feedback within about 400 ms.

Large displays, TV and signage
- https://developer.apple.com/design/human-interface-guidelines/typography.md : tvOS default 29 pt and minimum 23 pt; thin weights need larger sizes.
- https://developer.android.com/design/ui/tv/guides/foundations/design-for-tv : viewing about 3 m, lean-back, large text, limited text, instant focus feedback.
- https://developer.android.com/design/ui/tv/guides/styles/typography : avoid decorative body fonts, thin strokes and tight shapes; expressive type for display only.
- https://smashingmagazine.com/2025/09/designing-tv-principles-patterns-practical-guidance/ : 5 % safe margin, Apple 60/80 pt insets, 24 px TV body start, avoid pure white, three focus styles, small type scale.
- https://madegooddesigns.com/signage-design-guide/ : 1 in cap height per 25 ft comfortable and per 50 ft maximum, contrast and vibration advice.
- https://qasigns-blog.signs.com/blog/?p=16381 : 1 in letter height per 10 ft rule.
- https://typography.guru/journal/does-a-large-x-height-make-fonts-more-legible-r16/ : efficient wayfinding faces have x-height about 67-69 % of cap height; very large x-height does not help further.

WCAG 2.2 and motion
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html : 4.5:1 normal, 3:1 large (18 pt, or 14 pt bold), not rounded, check hover and focus.
- https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html : 3:1 for UI components and graphic parts.
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html : 24 x 24 CSS px and the spacing exception.
- https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html : non-essential motion must be switchable; prefers-reduced-motion techniques.
- https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html : auto-moving content over 5 seconds needs a pause control.
- https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html : no more than three flashes per second.
- https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion : scaling and panning are vestibular triggers; replace them with gentler effects.
- https://www.nngroup.com/articles/animation-duration/ : 100 ms feedback, 200-300 ms substantial change, about 400 ms large movement, ease-out, avoid linear.
- https://uxcel.com/blog/12-principles-of-animation-a-guide-to-motion-design-133 : easing, offset and overlap for hierarchy, motion as feedback.

First impression, hierarchy, emotion, colour
- https://www.websiteoptimization.com/speed/tweak/blink/ : Lindgaard's 50 ms and 500 ms ratings, halo effect, limits of the study.
- https://maze.co/collections/user-research/five-second-test/ : how to run a five-second test, sample questions, what it measures and misses.
- https://www.nngroup.com/articles/visual-hierarchy-ux-definition/ : scale, contrast, grouping; at most three contrast treatments; blur test with 5-10 px and 20 px.
- https://www.simonwhatley.co.uk/writing/donald-norman-3-dimensions-of-emotional-design/ : Norman's visceral, behavioural and reflective levels.
- https://www.freecodecamp.org/news/the-60-30-10-rule-in-design/ : dominant, secondary, accent proportions for focal point and harmony.

Award-level versus template-level, AI-interface tells
- https://www.utsubo.com/blog/award-winning-website-design-guide : Awwwards criteria weights; template versus award-level table; one signature moment.
- https://impeccable.style/slop : checklist of visual tells of AI-generated design.
- https://impeccable.style/visual-mode : how critique groups the tells and what fixes them.
- https://www.superdesign.dev/blog/why-ai-design-looks-generic : why defaults converge (Inter, purple gradient, three cards) and that the fix is deliberate direction.

Gaps: NN/g's own kiosk and large-screen articles and Apple's tvOS layout page could not be opened (404, 403 or empty),
so TV margins come from Smashing's summary and the visual-angle arithmetic is the rubric's own, built on the two signage rules above.

## 7. John's notes, 21/10 (override anything above that pushes toward more information on screen)

- A resting screen is not a blocker for showing fewer than all eight verdict names; one step in is fine. Do not ask for
  more at rest. Penalise a screen that is visually busy: the test is that at any moment it shows one clear thing and a small
  number of items (about 5-6 rows, a few controls) and can be parsed immediately. Simplicity that is still pleasing counts
  strongly toward "exciting" as well as toward readable.
- Colour used as a category system that helps the visitor sort talks is a strength.
- A physics toy or direct-manipulation moment that feels good is a strength; one that tangles or misbehaves is a blocker.
