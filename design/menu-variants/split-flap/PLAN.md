# split-flap: the departures board

## Concept
The hall screen is the venue's departures board. Verdicts are destinations (gate = number of talks, status = the
split of the debate), "Watch first" is the boarding list, search / sort / programme re-flap the same board.

## Palette (named hexes)
- Hall Blue     #0B1440  menu background, same blue the hall glows
- Housing       #060B2A  the board frame, row backs, hinge lines
- Flap Navy     #1B2A6E (top half) / #141F58 (bottom half)  the flaps
- Chalk         #EEF1FA  flap letters and body text (contrast on Hall Blue ~15:1)
- Mist          #A9B4E3  secondary text, labels (contrast ~8:1)
- Devoxx Orange #f6921e  ONLY for "what you asked for": matched letters, active sort/tab, focus ring, the X

Not near-black + neon (the board is blue like the hall, orange is a signal, not decoration); no cream, no serif,
no cards, no gradients except the flap shading that is the object itself.

## Type roles + scale
- Flap: JetBrains Mono 700, 21px in a 13x30 cell (laptop), 18px in a 13x22 cell (phone). Strictly uppercase, strictly
  one cell grid; the only place that is uppercase.
- UI / reading: Archivo (the real page's face) 14-15px, sentence case, weights 400/600. Wordmark Archivo 800 22px.
- Scale: 22 wordmark / 21 flap / 15 intro + detail text / 14.5 announcement / 14 labels. Phone: 13 labels.

## Wireframe 980x613
```
+--------------------------------------------------------------------------------------------+
| DEVOXX Belgium 2026                                              Text version of every talk |
| [The story] [Watch first] [All talks] [Programme]                       [ Search ........ ] |
| Devoxx Belgium 2026 was mostly about working with coding agents: ... contain them.          |
|  Talks  Verdict                                   Debate                                    |
| |[23 ][THE HARNESS OUTWEIGHS THE MODEL          ][2V3     ]                               |
| |[20 ][REVIEW IS THE NEW BOTTLENECK             ][3V1...  ]      (8 rows of flaps)         |
| | ...                                                                                       |
| Announcement bar: what the focused/hovered row says (consensus, why, tldr)    [<] 1-8 [>]   |
+--------------------------------------------------------------------------------------------+
```
Open verdict replaces the board: back, flap title, the debate question as two flap lines, consensus, two/three
sides (stance, speakers, talk buttons), the pick.

## Wireframe 340x690
```
+--------------------------+
| DEVOXX         Text version
| [Story][Watch][Talks][Prog]
| [ Search ............... ]
| Mostly about working with
| coding agents: ...
| [23][THE HARNESS         ]
| [  ][OUTWEIGHS THE MODEL ]   rows = 2 flap lines (8 verdicts fit)
| ...
| [<]   1-8 of 8   [>]
+--------------------------+
```
Talks on the phone add one small plain meta line (views, like rate, hearts) under the 2 flap lines.

## Signature moment
Every change of content (tab, typing, sort, page, programme day) re-flaps the same cells. Each cell is its own
mechanical flap that steps through the drum alphabet toward its target (2-7 flips, 36 ms each), with a stagger by
row and column, a flap shadow on the lower half, and the cells that match what you typed land in orange with a
flash: you see your letters being found mid-flip. A tab is retargetable mid-flight (typing fast never queues).

## AI-tells check
- no eyebrows / tracked caps: labels are sentence case Archivo; uppercase only on the flaps (the object).
- no single accent word in headings: wordmark X is the brand's own.
- no fade-slide-up: only the flaps move, and only in answer to input (and once on load).
- no cards: one board, rows are rows. Numbers are real data (gate counts), not 01/02/03 decoration.
- no near-black + neon: hall blue + orange only as meaning.
Revised: first idea was black flaps with amber letters (the cliche). Now blue flaps that belong to the hall.

## Log
- iter1: first build. Looked good at rest; phone settle slow; phone verdict detail overlapped (flex shrink); story right side empty.
  Scores 8/8/8/9/9/8 (clarity: picks lacked verdict context, programme paging clunky, search chips wrapped).
- iter2: detail flex fix, phone 6 rows/page + meta spans, picks meta shows verdict, programme jump chips (Morning/Lunch/Afternoon/Evening),
  legend shortened. Scores 9/8.5/8.5/9/9/8.5.
- iter3: story board gets bigger flaps (16x32) to fill the width and read from the hall; detail text 15px. Ann clipped at the bottom.
- iter4: story row spacing tightened, shorter flip chains for a faster load settle. Scores concept 9, craft 9, typography 8.5,
  motion 9, fit 9, clarity 8.5 = 9.0 overall. Critic's last notes: "Split 2V3" is cryptic (explained in the announcement bar);
  flap titles truncate with ".." in talk lists (full title in announcement); phone story drops the split.
- remove one accessory: removed the dashed border on the programme jump chips (decoration, no information).
