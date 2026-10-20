# debate-arena: plan

## Idea
The week as eight arguments. Each verdict is one horizontal line between its debate's two sides; speakers are dots on
it, placed by which side's `who` list they are in ("our reading of the talks"). Hover a dot and a thread is pulled to
their talk and to every other line the same person appears on (three people argued in more than one verdict).

## Palette (the hall screen is deep blue; orange is the Devoxx X)
- Hall Blue `#0B1440`  canvas
- Panel Blue `#111C54`  rail, readout, hover cards
- Rule Blue `#2D3E9A`  hairlines, non-text structure
- Paper `#F2F4FF`  text, threads, focus ring
- Mist `#B7C1F0`  secondary text (about 10:1 on Hall Blue)
- Devoxx Orange `#F6921E`  side A (also the wordmark X)
- Tide `#4FD1C5`  side B
- Lilac `#BBA8FF`  side C (only the one verdict that has three sides)

## Type (Archivo, the real page's family; width axis used so labels stay compact)
- Headline 19/1.2, 700, wdth 88
- Verdict title / row title 15/1.15, 650, wdth 92
- Verdict opened: question 20/1.2 700; title 24/1.1 700
- Body 14/1.4 400 (never smaller on the laptop canvas); meta 14 Mist
- Figures: tabular-nums, 14 600
- No all-caps labels except the DEVOXX wordmark; sentence case everywhere.

## Wireframe 980x613
```
+--------------------------------------------------------+------------------+
| DEVOXX  Belgium 2026   Mostly about coding agents: how | [ Search talks ] |
| 5-9 Oct, 205 talks     to check, review, contain them  |                  |
+--------------------------------------------------------+ Watch first      |
| Arguments | All talks | Programme                      | provisional ...  |
| readout: hover a line -> settled ground + the question | 1 pick title     |
|  (hover a dot -> name, company, talk chip) <-thread-.  |   speaker        |
| Title of verdict      o o ----  .....  ---- o o o   23 | 2 ...            |
| ...x8 rows (51px each), spectrum ends = the two sides  | ...x8            |
| legend: dots = speakers, our reading   Text version    |                  |
+--------------------------------------------------------+------------------+
```
## Wireframe phone 340x690
```
DEVOXX Belgium 2026
Mostly about coding agents ... (3 lines)
[ Search talks               ]
Arguments | Watch first | Talks | Programme
Verdict title
o o ------ ..... ------ o o o
Verdict title ...
(scroll)
```
## Signature moment
Dot hover/arrowing: a thread draws from the dot to its talk chip in the readout and across to the same person's dots
on other lines, those lines stay lit, the rest dim. Faint threads for the three cross-verdict speakers are always
drawn at rest, so the idea is visible before any input.

## AI-tells check
- Not cream/serif/terracotta; blue is given by the hall, orange by the brand. Not near-black + neon.
- No identical rounded card grid: rows are a chart; the only boxes are the verdict-open stances, which are columns
  aligned under the side they describe.
- No eyebrows, no numbered markers (verdicts are not a sequence), no one-word colour in headline, no glow/gradient.
- Motion only answers input (thread, open verdict); no entrance fades.
- Changed after review: dropped planned per-row pole labels (truncated text looked sloppy): poles are read in the
  readout and the opened verdict instead.

## Iteration log
(see bottom, filled in as the loop runs)

### iter1 (self-critique: concept 9, craft 6, type 7, motion 8, fit 8, clarity 7 = 7.5)
Bugs: side C colour self-referencing CSS var (lilac dots invisible); opened verdict collapsed (flex shrink) and names
collided with the stance text; thread ended at the left edge of the readout; programme list ran under the footer;
phone tabs clipped, footer ate the list.
### iter2: fixes above; thread now ends under a talk chip placed above the dot; pick hover writes its reason into the
readout instead of a card covering the lines; verdict top row merged (title + All arguments/Previous/Next);
"Watch both sides" became two pills (one per end side); phone shows who-lists instead of colliding names.
(score 8.2)
### iter3: legend names the three ringed speakers from the data; default readout explains the dotted middle;
bigger dots; crowded names stagger. (8.5)
### iter4: threads unspool once on load (the only unprompted motion); reduced motion skips it. (8.7)
Last critic notes: rest state is tidy but quiet at hall distance (dots could carry surnames for the three ringed
speakers); 3-sided verdict clips talk titles to one line; no pre-composed no-JS verdict list (only a link);
the "see it in the hall" toggle was not built.
### Remove one accessory
Removed the row hover background tint: the underline already says "this row", the tint only muddied the dim state.
