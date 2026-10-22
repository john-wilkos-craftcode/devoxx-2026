# The hall screen, round 3: the brief

> **NOTICE TO FIXERS (coordinator, 20/10 22:05, John's decision, his usage window is nearly spent):** exactly ONE
> fix round is wanted per menu. If the review you were handed has issue ids starting `r1-`, fix as instructed. If its
> ids start `r2-` or `r3-`, do NOT change any file and do not run Codex or a capture: return at once with summary
> "skipped: one fix round only", fixed [], notFixed [], newCodexImages 0. Builders and reviewers: ignore this notice.

## What this is

The cinema page (`site/cinema/`) is a photo-real 3D render of the actual Devoxx Belgium 2026 venue (Kinepolis
Antwerp). You arrive in the hall and look at its big schedule screen: a 3.6 x 2.25 m LCD on a curtained wall between
two potted trees, ivy hanging above it. **That screen is the main menu.** See it as it is now:
`design/menu-screen/context/now-in-hall.jpg` (laptop window), `context/now-in-hall-phone.jpg` (phone: a portrait totem
screen). Pick a talk and you walk through the venue to your seat in that room, where the recording plays.

The talks are over; they are on YouTube and summarised. The menu's job is to tell the conference's story and get a
visitor to a talk they will enjoy.

## What John wants this round (20/10, evening)

"The highest quality, most inventive and best UX menu screen. Attempts have been made, but now I want to try
something new." Highly original and inventive; good menu screens; **original and colourful**; **the most important
information first**; **nothing visually overloaded**. Judged by two questions only: *does it look exciting and
amazing?* and *is it easily readable and functional?* (plus what the research in `RUBRIC.md` adds for UX).

## What failed before (do not repeat, do not drift back to it)

- Round 1 (`design/menu-variants/`): a terminal/JShell table, a debate arena, a reel, a sonar/radar, a split-flap
  board. John: "very generic and too information dense at first glance."
- Round 2 (`design/menu-screen/`): Saul Bass title cards in red; "two voices" split screen; a white lightbox with one
  big sentence and a search caret; a 205-seat plan; Aicher-style room numerals. All plateaued at 6.0-6.8/10 under
  fresh critics. What the critics kept saying: they were *type-and-shape* designs without any imagery; the type and
  colour looked assembled rather than designed; not legible enough from across the hall; the screen looked pasted onto
  the wall; restrained to the point of dull.
- The current live programme (navy board, orange cards, 13 time chips): a kiosk UI, not a thing in a room.

**So this round: bold colour and real visual substance** (generated or illustrated imagery, rich colour worlds,
light, depth, texture, a true focal point), still calm to read. Not "near-black plus one neon accent", not cream +
serif + terracotta, not generic SaaS cards/bento/glassmorphism, not a dashboard, not ticket-stub/popcorn/film-strip
cinema clichés unless you transform them into something nobody has seen.

## The information priority ladder (what to show first)

1. **First glance** (3 seconds, from the back of the hall, about 15 words or fewer): *what this is* (Devoxx Belgium
   2026, 205 talks summarised) + *the story of the week in one idea* (a headline faithful to `MENU.recap.intro`) +
   *the obvious first move*.
2. **One step away**: the 8 verdicts (the story), the "watch first" pick for each, search.
3. **Two steps away**: a verdict's consensus and debate (sides, who, their talks), the talk list sorted by a signal,
   the programme by day, the text-version link.

Everything exists; only the order and the weight differ. A first-time visitor who has slept two hours must find the
story, a talk worth watching and search within five seconds.

## Functions every menu must have (all real; never invent talks, people or numbers)

Data: `design/menu-variants/data.js` sets `window.MENU` (load it as `../../menu-variants/data.js` from
`design/menu-round3/<slug>/index.html`; do not edit it). Fields: `MENU.recap.intro`; `MENU.recap.trends[]` (8
verdicts: `title`, `body`, `count`, `talkIds`, `consensus`, `debate` {`question`, `sides[]` {`stance`, `who[]`,
`talkIds`}}); `MENU.picks[]` (8: `verdict`, `talkId`, `why`); `MENU.talks[]` (205: `id, title, speakers[{name,
company}], room, start, end, type, track, level, minutes, keywords, themes, tldr, watchIf, takeaway, videoId, hearts,
views, likes, likeRate, thin, seat`). Signals, shown honestly: `views` = reach, `likeRate` = likes per 100 views
(`thin: true` means under 20 likes: mark "few votes", never rank on it alone), `hearts` = Devoxx-app favourites
before the talk (interest, not quality). 24 talks have no video (`views: null`).

1. **The story**: the intro (or a headline derived from it, faithful to it) and all 8 verdicts, each opening to its
   consensus and its debate (question, both sides, who, their talks).
2. **Watch first**: the 8 picks with their reason.
3. **Search** over title, speakers, company, keywords, themes, tldr, track; results as you type.
4. **Sort the talks** by views, like rate (with the "few votes" caveat) or hearts.
5. **Open a talk**: define `window.openTalk(id)`; it shows a small toast ("Walking to Room N" when `seat` is true,
   else "Opening the summary"). The real page will start the walk.
6. **Programme by day**: Mon 5 to Fri 9 October 2026, times in Europe/Brussels (`start` is UTC). One step away.
7. **Text version** link: `../../../site/index.html`.

## Hard constraints

- `#menu` is exactly **980 x 613 CSS px** (the laptop hall screen); `?shape=phone` makes it **340 x 690** (the phone
  totem, portrait; design it properly, not as a squashed copy). The page itself is a dark stage with `#menu`
  centred. A tiny key hint *outside* `#menu` is fine.
- Plain HTML/CSS/JS, no build step, no framework (a winner gets ported into a vanilla-JS page). Pinned CDN libraries
  only from cdnjs.cloudflare.com, cdn.jsdelivr.net/npm or unpkg.com with an exact version, only when they earn it
  (three.js, a shader helper, GSAP are fine). Google Fonts are fine.
- Imagery: make it yourself (canvas 2D, WebGL/shaders, SVG, CSS 3D, procedural patterns, generative scenes), or cut
  from the venue renders in `site/cinema/media/` (`hall.jpg`, `seat-N.jpg`), or the real YouTube thumbnail of a talk
  (`https://i.ytimg.com/vi/<videoId>/mqdefault.jpg`; optional, must degrade gracefully, never required for the
  design to work). No stock photos, no fake logos. The Devoxx wordmark is "DEVOXX" in type with the X in orange
  `#F6921E`; you may use the name in type.
- **Codex can generate images for you (John OK'd it).** Codex's built-in `image_gen` tool needs no API key; it makes
  one ~1586x992 PNG in about 50 s (verified 20/10). Use it for backgrounds, illustrations, textures, scenes, cut-outs
  and mood art; never for text or UI (generated lettering is unreliable), and keep anything that must be legible in
  real HTML type. One image at a time (three designs share this machine and John's Codex plan: budget ~6 generations
  per design plus retries; check each result before asking for more). Recipe, from the repo root:
  ```
  /home/kevlarrelic/.nvm/versions/node/v24.13.0/bin/codex exec -m gpt-6-astra -c model_reasoning_effort="low" \
    -s workspace-write -C /home/kevlarrelic/code/CRAFTCODE/devoxx-2026 -o <scratch>/last.txt \
    "Use the built-in image_gen tool (the imagegen skill) to make ONE image: <your prompt: subject, style, palette,
     composition, lighting, 'no text, no logos'>. Then copy the generated file from ~/.codex/generated_images/ into
     /home/kevlarrelic/code/CRAFTCODE/devoxx-2026/design/menu-round3/<slug>/assets/<name>.png and print only that path."
  ```
  Never use danger-full-access. Look at the result (Read the PNG) before using it. Convert what the page uses to
  WebP/JPEG at the size it needs (a menu asset should be well under 400 KB; PIL is installed) and keep the original PNG
  out of the page. Ask for a transparent background when you want a cut-out. Reuse one "style line" across your prompts
  so the set looks like one hand made it. Write each prompt and filename in your LOG.md (it is AI-generated imagery and
  must be labelled as such). Code-made imagery (canvas, WebGL, SVG) is just as welcome and is free; mix both.
- Write only in your own folder `design/menu-round3/<slug>/`.
- Quality bars: no console errors; keyboard-complete with a visible focus ring; `prefers-reduced-motion` gives a calm
  version; nothing invisible if JS is slow (content is in the HTML, no opacity-0 starts); text contrast >= 4.5:1 and
  every word of body text >= 14 px (headline-level text far larger: it is read from several metres); phone targets
  >= 44 px.
- Motion answers the user (hover, keys, drag, typing); ambient motion is allowed when it earns its place, and must not
  hurt legibility.

## How it is judged: the picture in the hall is what counts

`node tools/ux/menu-capture.mjs design/menu-round3/<slug> <outDir>` photographs `#menu` at rest (laptop, phone,
reduced motion, a 4-frame motion strip, after 4 Tabs), photographs every state you list in
`design/menu-round3/<slug>/states.json`, writes `facts.json` (visible word count, smallest font, `openTalk` defined,
expectation checks) and composites every shot onto the real screen in the rendered hall (`<name>-hall.jpg`, 1920x1080
for laptop). Read the `*-hall.jpg` files; that is the picture a reviewer judges. Header of the tool lists the
`states.json` step vocabulary (`click`, `hover`, `press`, `type`, `fill`, `wait`, `mouse`, `drag`, `scroll`,
`expectVisible`, `expectText`). Every function above must be reachable by a state, and its `expect*` steps are how a
reviewer verifies it works. Memory is limited on this machine: run one capture at a time, never leave a browser open.

## Deliverables in your folder

`index.html` (+ css/js/assets), `states.json`, and `LOG.md` (the idea in a paragraph, how to use it, keys, what you
tried and dropped, known gaps). Reviews will be written to `reviews/` beside it.

## Decisions (John, 21/10 00:34; they override anything above that says otherwise)

- The screen is judged as a **render on a laptop**, not as a real wall seen from 8 m. Ignore "from the back of the
  hall" and "read from several metres" wording above: the picture that counts is the 1920x1080 hall shot at laptop size.
- **Opened lists may be plain**, as long as the visual design is clear and cohesive (they should still belong to the
  same world as the resting screen). The glance-layer word budget counts only text at 24 px or more, with the eight
  verdict names as one chunk. See `RUBRIC-v2.md`.
- **John's notes after trying the menus (21/10) override the rankers' advice:** see `JOHN-NOTES.md`. He prefers visual
  simplicity and a limited amount of information on screen at any time, immediately parsable. The eight verdicts do not
  all need to be visible at rest (one step in is fine); a resting screen is not marked down for hiding them.
