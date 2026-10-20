# sonar: the practice radar

## Palette (named hexes)
- Hall navy #0B1440 (screen ground, given), Panel navy #0F1A4F, Ring line #2A3E8F
- Ink #EEF2FF, Mute #A9B8EA (8:1 on navy)
- Sweep orange #F6921E (Devoxx X; used only for the arm, selection, active tab underline, link underlines)
- Sector hues, used only as the sector key: Agents #7CCBF5, Security #F58BA0, JVM #A6DE8A, Architecture #C9A8F7

## Type
Archivo (variable width). Wordmark: wdth 125 / 850. Headlines: wdth 108-112 / 700-800 (22-20 px). Panel titles 15-16 px / 650-700.
Body and labels 14 px / 400-600, arc sector names 16 px / 700 on the rim, ring names 14 px / 600.

## Wireframes
980x613                                              340x690
+-----------------------------+------------------+   +------------------------+
| What the talks told you...  | DEVOXX [search ] |   | DEVOXX [search]        |
|  Our reading of the talks   +------------------+   +------------------------+
|     (arc: Architecture)     | Sweep Verdicts.. |   |   radar R=128          |
|        ,-"" ring labels ""-.| Headline         |   |   (arc names, arm)     |
|      /   o  <>   o   o      | Start with ...   |   +------------------------+
|     |  o   < arm >   o  <>  | feed: 5 blips    |   | Sweep Verdicts Watch.. |
|      \   JVM    Security   /| + their talks    |   | headline + 3 feed rows |
|  hint            [Pause]    | Text version     |   | Text version           |
+-----------------------------+------------------+   +------------------------+

## Signature moment
A slow sweep arm (one turn a minute) that you can grab and drag. As it passes a practice the mark pings and its name lights;
the side panel lists the last five practices it passed, in sweep order, each with its talks. Arrow keys step the arm blip to blip.
Search makes matching marks glow and dims the rest.

## Data
blips.js: 46 practices, each with source verdict (`v`), debate side where it is one side of a debate, and source talk ids
(check.mjs validates them against MENU). Ring and sector are our reading of the talks, labelled as such in the UI.
Diamond = debated, circle = agreed; hollow circle = push back.

## AI-tells check
Not cream/serif/terracotta; not near-black + neon (navy hall colour from the brief, orange only for the sweep). No cards grid,
no eyebrows, no fade-slide-up, no gradient filler (the one gradient is the sweep trail, which encodes the 70 degree memory window),
no mono labels. Revised: sector colours stay a key (not decoration); removed always-on labels (clutter) in favour of sweep-lit labels.

## Critique log
- iter1: 6.5. Labels piled up inside the trail, ring labels clash, phone hit areas overlapped (test could not click). Fixed: label
  window 30 degrees, collision relaxation, phone smaller labels.
- iter2/3: 8. Bugs: talk list array stringified, titles inline. Added start line (verdicts / watch first), dot size by ring, ghost
  labels hidden while searching. Calm mode labels cleaned.
- iter4: concept 9, craft 8.5, typography 8.5, motion 9, fit to app 8.5, clarity 8: overall 8.6. Last notes: ring names on the
  vertical axis still collide with lit blip labels near 12 o'clock; panel is plain next to the radar; blips are small for
  the hall viewing distance.
- Remove one accessory: the glow halo around lit marks (glow as filler). Removed.
