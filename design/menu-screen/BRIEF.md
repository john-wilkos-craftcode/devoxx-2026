# The hall screen: brief (round 2)

## What this is

The cinema page (`site/cinema/`) is a photo-real 3D render of the actual Devoxx 2026 venue (Kinepolis Antwerp). You
arrive in the hall and look at its big schedule screen: a 3.6 x 2.25 m LCD on a curtained wall between two potted
trees, ivy hanging above it. That screen is the main menu. See it as it is now:
`design/menu-screen/context/now-in-hall.jpg` (laptop window) and `context/now-in-hall-phone.jpg` (phone: a portrait
totem screen). Pick a talk and you walk to your seat in that room, where the recording plays.

## John's verdict on round 1 (design/menu-variants/, all five rejected)

- "very generic and too information dense at first glance."
- "this is a screen in a 3d render of the actual conference. just come up with some way to make it look good."

So: judge every design **as a screen in that render**, not as a web page. At first glance it must be beautiful and
calm, and read from across the hall: few words, big type, one image or idea. The detail is there, but one step away.

## What it has to let you do (not all at first glance; progressive disclosure)

The talks are over, on YouTube and summarised. The screen tells the conference's story and gets you to a talk:
1. **The story**: what the Java community argued about this week. Data: `MENU.recap.intro` and 8 verdicts
   (`MENU.recap.trends[]`: `title`, `consensus`, `debate` {`question`, `sides[]` {`stance`, `who[]`, `talkIds`}},
   `talkIds`, `count`).
2. **Watch first**: `MENU.picks[]` (8, one per verdict, with `why`).
3. **Search** over the 205 talks (`MENU.talks[]`: title, speakers, company, keywords, themes, tldr, track).
4. **Sort the talks** by `views`, `likeRate` (marked "few votes" when `thin`) or `hearts`.
5. **Open a talk**: `openTalk(id)` (define it; show a small toast "Walking to Room N" when `seat`, else "Opening the
   summary").
6. **Programme by day**, one click away (Mon 5 to Fri 9 October 2026, times in Europe/Brussels; `start` is UTC).
7. **Text version** link: `../../../site/index.html`.
Data file: `design/menu-variants/data.js` (sets `window.MENU`; load it as `../../menu-variants/data.js` from
`design/menu-screen/<folder>/index.html`; don't edit it). Never invent talks, people or numbers.

## Hard constraints

- `#menu` is exactly **980 x 613 CSS px** (laptop); `?shape=phone` makes it **340 x 690** (totem). Centre it on a
  dark page.
- Plain JS + CSS, no build, no framework (the real page is vanilla JS; a winner gets ported). Pinned CDN libs only
  from cdnjs.cloudflare.com / cdn.jsdelivr.net/npm / unpkg.com with an exact version, only if they earn it. Google
  Fonts allowed. Raster images you make yourself (canvas, SVG, or images cut from the venue renders in
  `site/cinema/media/`) are allowed; no stock photos, no fake logos.
- Write only in your own folder `design/menu-screen/<folder>/`.
- Quality: no console errors; visible keyboard focus and full keyboard use; `prefers-reduced-motion` gives a calm
  version; nothing invisible if JS is slow (no content starting at opacity 0); text contrast >= 4.5:1.

## Tools

- `node tools/ux/shot.mjs design/menu-screen/<folder>/index.html design/menu-screen/<folder>/shots/t<N>` (repo root):
  1-rest, 2-hover, 3-keyboard, 4-reduced-motion, 5-phone PNGs of `#menu`, and console errors.
- `python3 tools/ux/inhall.py <menu.png> <out.jpg> [--phone]`: puts a #menu screenshot on the real screen in the
  render, plants and ivy in front, framed as a laptop window (or on the phone totem). **This is the picture that
  counts.**

## Taste

- Restraint reads as premium. Cut gradients, glows, unnecessary containers, redundant labels, random highlights.
- Avoid the AI tells: generic SaaS cards; near-black + one neon accent; cream + serif + terracotta; tracked ALL-CAPS
  eyebrows everywhere; fade-slide-up on everything; one headline word in another colour; decoration without purpose;
  dense dashboards.
- One signature moment, earned by the subject (Devoxx, Java, a cinema, a week of arguing about coding agents, the JVM
  and architecture). Motion should answer the user (hover, keys, drag), not loop for its own sake.
