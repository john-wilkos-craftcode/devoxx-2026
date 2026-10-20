# jshell: the conference as a REPL

## Palette (named hexes)
- hall-screen  #0B1440  canvas, same blue the real screen glows
- panel        #111C57  raised surfaces (completion popover, hover rows)
- rule         #2B3B8C  the left "feedback rail" and hairlines
- ink          #EEF1FF  body text
- ink-dim      #9CA8DC  meta text (7:1 on the screen)
- devoxx-orange #F6921E prompt, caret, focus ring, the one brand colour
- sky #86BEFF / mint #8FE5B8  syntax colouring ONLY in commands (names / strings); never in output

## Type roles
- JetBrains Mono 16/500: the prompt, echoed commands, command chips. Nothing else is mono.
- Archivo: everything rich. Output title 17/650, verdict headline 19/500, body 15/400, meta 14/400 (floor 14).
- Numbers in signals are tabular, 15/650 over a 14 dim label (no all caps, no tracking anywhere).

## Layout (980x613)
```
+--------------------------------------------------------------------------------+
| DEVOXX Belgium 2026                                   help()   Text version     |  40
+--------------------------------------------------------------------------------+
| | Welcome. 205 talks, 5 to 9 October. Click a command or type one.               |
| jshell> verdicts()                                                               |
| | Devoxx Belgium 2026 was mostly about working with coding agents ... more       |
| |                                   the verdict                 watch first      |
| | 1  The harness outweighs the model     23 talks   > Talk title ................ |
| | 2  Review is the new bottleneck        20 talks   > Talk title ................ |
| |  ... 8 rows, hairline separated, row hover reveals the command it will run     |
+--------------------------------------------------------------------------------+
| jshell> sea|rch("")                      <- input, syntax coloured, ghost suffix |
| [verdicts() the story][watch() watch first][search("") find][sort(views)][programme()] |
+--------------------------------------------------------------------------------+
 completion popover (above the input while typing / hovering a chip):
 +----------------------------------------------------------+
 | search("valhalla")   find talks      [Tab] accept [Enter] |
 | ---- preview: 12 talks match ----                          |
 | rows...                                                    |
 +----------------------------------------------------------+
```
Phone 340x690: same stack; verdict rows collapse to index/title/play-icon (count under title); chips scroll sideways; popover full width.
Alignment: everything left aligned, output hangs off a 2px rail (jshell's own "|" feedback marker).

## Signature moment
Autocomplete that previews the result. Typing (or hovering/focusing a command chip) opens a popover under... above the prompt with the ghost completion inline and a live preview of what the command would print (search hits, a verdict's debate, the top of sort). Tab accepts, Enter runs. Every click types its command into the prompt first, so the menu teaches the language. Plain words become search("word").

## AI-tells check
- near-black + neon: no. Canvas is the hall's own blue, orange is the Devoxx brand, syntax colours confined to the prompt.
- eyebrows / all caps / middle dots / arrows on buttons / em-dash labels: none; labels are sentence case plain words.
- SaaS cards: none. Output is a ruled table hanging off a rail; only the popover is a raised surface (it is functional elevation).
- Mono for data labels: avoided. Mono only where text is code (prompt, commands, chips).
- Numbered markers: only where the number is an argument (debate(3)) or a real rank (sort).
- Revisions after review: dropped a window-chrome dots bar (decoration), dropped idea of glow caret; row-hover shows the command instead of an arrow.

## Log
iter1 (build): critic 8/10. Fixes: phone grid overflow (grid column minmax(0,1fr)), boot banner pushed rows off canvas (moved into top bar), "Everyone agreed"/"Where they split" had two accent colours (now plain weight), picks note capitalised.
iter2: concept 9, craft 8.5, typography 8.5, motion/interaction 8.5, fit 9, clarity 9 = 8.8. Fixes: phone hall button hidden, shorter phone chrome, boot now types verdicts() into the prompt, phone watch icon gets a word.
iter3: concept 9, craft 9, typography 9, motion/interaction 9, fit 9, clarity 9 = 9.0. Stop.
Remove one accessory: the transcript entry + feedback line after openTalk (the toast already says it; the log filled with a dead block and an empty scroll gap).
Critic last notes: rest state is a disciplined table, the wow is in interaction (preview popover, command shown on hover and typed on click), not in the rest picture; pick titles truncate at 340px; 14px meta is at the brief floor, small for the hall.
