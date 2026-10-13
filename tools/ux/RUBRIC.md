# Devoxx cinema: UX and visual review rubric

Used by the review agents that score the cinema page (`site/cinema/`) from screenshots taken by `shoot.mjs`.
Each round, two fresh agents with no stake in the design review the same screenshots: a UX researcher (can people
understand it, read it, get around) and an art director (does it look like real screens in a real room, is it
beautiful and distinctive). The target is 9/10 from both, on laptop and on phone.

## The site
Every Devoxx Belgium 2026 session (205 talks, 5 days), summarised. The page is a photorealistic render of the
Kinepolis venue where the conference happened. The programme is shown ON a screen in the venue's exhibition hall
(laptop: a big screen on the curtained wall; phone: a portrait schedule totem). Choosing a talk walks you (a short
pre-rendered video) to the room where it took place:
- laptop: to a seat; the talk's summary is ON the cinema screen;
- phone: to the room's door; the talk is on the portrait schedule totem beside the door's red portal, with the
  room number on an orange plate on top (a 2.9:1 cinema screen is unreadable in portrait, so this is deliberate).
The aesthetic is deliberate: diegetic, skeuomorphic photorealism (the UI lives on real screens in the room).
Real photos of the venue and its signage this year: `data/references/img/` (contact sheets `_hollywood.jpg`,
`_auditorium.jpg`).

## Standing notes for reviewers
- Walk videos may not be rendered yet; the jump from hall to seat is then a cut. Ignore that.
- Room renders may be half-resolution, low-sample look-dev renders (soft, a little noisy); final renders are full
  resolution and sharp. Judge the room on composition, light and believability, not sharpness.
- Only rooms with a rendered walk have orange cards; other rooms' cards are navy for now and open the summary on
  the hall screen. In the final site Rooms 3-10 are all orange. BOF rooms are downstairs and stay navy.
- A fade at the edge of a list or strip is deliberate: it marks that it scrolls.

## Screenshots (laptop 1440x900, laptop 1280x720, phone 390x844 at 2x)
  1-hall          first view
  2-other-slot    after choosing another start time
  3-search        after typing "kotlin" in search
  4-talk          after choosing a talk with a seat (summary on the cinema screen / door totem)
  5-talk-tab      another tab of the talk
  6-back          after "Back to the programme"
  7-offfloor      a talk with no cinema seat (a BOF), shown on the hall screen
  8-keyboard      after pressing Tab four times on load (focus visibility)
  log.txt         console errors

## Atomic checks (yes/no, laptop and phone separately)
 C1  Within 3 seconds it's obvious what this is (Devoxx 2026 talks) and what to do (pick a talk).
 C2  All text on the screens is comfortably readable at this viewport (body text at least ~14 css px equivalent).
 C3  Day and time navigation is understandable and the current selection is obvious.
 C4  Search is findable, results are clear, and each result shows when and where.
 C5  On the talk view, title, speakers, room/time, summary and the way back are all obvious.
 C6  Nothing is cut off, overlapping, or clipped by the viewport or the screen edges; no stray text.
 C7  Interactive things look interactive; keyboard focus is visible.
 C8  The UI reads as physically ON the screens in the room (perspective, scale, light), not as a sticker on top.
 C9  The room around the screens is believable and supports, not distracts from, the content.
 C10 Typography, colour and spacing are consistent and deliberate; it looks designed, not templated.
 C11 The visual hierarchy guides the eye: the most important thing on each view is the most prominent.
 C12 The language is plain and specific (sentence case, says what happens).

## Output (under 500 words)
- Laptop score /10 and phone score /10 (9 = I'd ship it; 10 = best-in-class).
- The yes/no table for C1-C12 (laptop, phone).
- The top issues blocking a 9, ranked by impact. For each: what's wrong (view, where), why it matters, and a
  concrete fix. Be blunt; don't praise. Judge only what you see.

## Scores so far
| round | UX laptop | UX phone | art laptop | art phone | main change |
|---|---|---|---|---|---|
| 2 | 4 | 6 | 4 | 6 | first redesign |
| 3 | 6 | 5 | 6 | 6 | fixed canvases, cut-out letters |
| 4 | 7 | 6 | 7 | 5 | screen above the letters, letterbox |
| 5 | 7 | 4 | 7 | 4 | phone talk on the door totem (cards collapsed: bug) |
| 6 | 7 | 8 | 6 | 7 | door totem square on |
| 7 | 7.5 | 5 | 7.5 | 5.5 | bigger hall text (phone search box bug) |
| 8 | 8 | 8 | 8 | 7 | round-8 fixes |
| 9 | 7.5 | 7 | 7.5 | 7 | sharp 2D pinning, numeral plate |
| 10 | – | – | 7 | 7.5 | backlit plate, doorway |
