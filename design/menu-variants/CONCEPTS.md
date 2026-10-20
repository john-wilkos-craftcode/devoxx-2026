# Five concepts

Each is a different metaphor for the same content (see BRIEF.md). Not palette swaps.

## 1. `split-flap`: the departures board

- **Persona:** a senior creative developer specialising in typographic motion and physical-interface simulation
  (Solari boards, mechanical counters), obsessive about timing curves and monospaced grids.
- **Concept:** the hall screen becomes the venue's own departures board. Each verdict is a "destination" row with its
  talk count as the gate and its debate as the status ("DISPUTED"); "watch first" is "now boarding"; search, sorting
  and the programme re-flap the board. The board's job during the week (where to go next) turns into its job now
  (what to watch next).
- **Signature moment:** typing in search or changing the sort makes the rows re-flap character by character into the
  new results, with staggered mechanical timing and a faint flap shadow; the letters you typed are found mid-flip.
- **Reduced motion / fallback:** rows swap instantly (a 120 ms cross-fade at most); without JS a static board of the
  8 verdicts in the HTML plus the text-version link.

## 2. `debate-arena`: where they stand

- **Persona:** a senior data-visualisation designer from editorial newsrooms (The Pudding, FT Visual Vocabulary),
  specialising in making disagreement legible and in honest annotation.
- **Concept:** the conference as its arguments. The front shows the 8 verdicts as 8 horizontal "tug" lines, each a
  spectrum between its debate's two sides, with speakers placed as dots ("our reading of the talks"). What everyone
  agreed on sits above each line as the settled ground. Pick a line to open it: the two stances, the evidence, and a
  "watch both sides" pair. Picks and search sit in a right rail.
- **Signature moment:** hovering or arrowing onto a speaker's dot pulls a thread to their talk and lights every other
  verdict line that speaker appears on, so you see who argued across the week.
- **Reduced motion / fallback:** no thread animation, the links just highlight; without JS, the 8 verdicts with
  their questions as plain text.

## 3. `sonar`: the practice radar

- **Persona:** a senior creative technologist specialising in canvas/WebGL instruments and HUD design, who has built
  data radars for newsrooms and cockpit-style dashboards that stay readable.
- **Concept:** a Thoughtworks-style radar of what speakers told you to do: rings "do it now / try it / watch it / push
  back", sectors for agents, the JVM, architecture and security. Blips are the practices and tools from the verdicts
  and talks (derive placements from the data you have: consensus statements and the talks' takeaways and themes; label
  them "our reading"). Selecting a blip opens the why, the debate if it's contested, and the talks.
- **Signature moment:** a slow sweep arm that you can grab and drag: as it passes over blips they ping and their talks
  appear in the side panel in sweep order; search makes matching blips glow and others dim.
- **Reduced motion / fallback:** no sweep, static radar, selection by click/keys; without JS a text list of the
  practices by ring.

## 4. `reel`: the projection booth

- **Persona:** a senior motion and title designer for film (title sequences, trailers) who also builds interactive
  web experiences; thinks in frames, gates and cuts.
- **Concept:** we are in a cinema, so the week is a film reel. Each verdict is a frame on a horizontal filmstrip with
  sprocket holes: the frame shows the verdict as a title card, its debate as a "versus" card. "Watch first" are the
  credits (who to see). Search and sort reorder the strip; the programme is the "screening schedule".
- **Signature moment:** drag or scroll the strip and it runs through a projector gate in the centre: the frame in the
  gate lights up full-bright with a tiny gate weave and the verdict's chapter appears beside it, like threading a
  projector by hand; arrow keys advance one frame with a click of the claw.
- **Reduced motion / fallback:** frames snap without weave or blur; without JS the frames are a static row of
  verdict titles plus the text-version link.

## 5. `jshell`: the conference as a REPL

- **Persona:** a senior developer-experience designer who builds terminal UIs and IDE features (JetBrains, Warp),
  fluent in what makes a command line delightful and discoverable for non-experts.
- **Concept:** the hall screen is a jshell session about the conference: it boots with a greeting and the verdicts as
  the result of `devoxx.verdicts()`, then you explore with commands (`watch()`, `search("valhalla")`,
  `sort(views)`, `programme(tuesday)`, `debate(3)`) or simply click the suggestion chips and results, which type the
  command for you. Results render as rich, clickable output, not walls of monospace.
- **Signature moment:** autocomplete that previews the result: as you type, a ghost of the result appears under the
  prompt (search results, a verdict card), and Tab accepts it. Clicking anything shows the command it ran, so you
  learn the language by using the menu.
- **Reduced motion / fallback:** no typing animation, output appears at once; without JS a static transcript showing
  the verdicts and the text-version link. Must stay usable by mouse alone for people who never type.
