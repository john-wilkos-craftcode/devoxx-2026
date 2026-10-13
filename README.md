# Devoxx Belgium 2026, summarised

Every session of Devoxx Belgium 2026 (5 to 9 October, Kinepolis Antwerp), summarised from what the
speakers actually said, as a static site styled like a cinema programme.

Live at **https://john-wilkos-craftcode.github.io/devoxx-2026/**, with the cinema at
[`/cinema/`](https://john-wilkos-craftcode.github.io/devoxx-2026/cinema/): the programme on a screen in
the venue's Hollywood room, a walk to your seat, and the talk on the cinema screen (on phones,
on the schedule totem at the room's door).

Locally, serve the `site/` folder:

```sh
node tools/ux/serve.mjs   # http://localhost:8765 (with byte ranges, so the cinema's videos can seek)
```

## How it's built

1. `scripts/fetch_data.py` pulls talks and the schedule from the public CFP API
   (`dvbe26.cfp.dev`) and matches each talk to its recording on the Devoxx YouTube channel. The
   channel hosts every Devoxx edition, so only uploads after the Belgium 2026 promo are considered.
2. Transcripts go to `data/raw/transcripts/` (gitignored):
   - `scripts/transcribe_whisper.py` (main path): downloads each recording's audio and transcribes
     it locally with faster-whisper on the GPU, primed with speaker names and keywords. About a
     minute per talk on a 4 GB laptop GPU.
   - `scripts/fetch_captions.py` (fallback without a GPU): YouTube's English original auto-captions.

   Both talk to YouTube through `scripts/yt.py`, which follows yt-dlp's current guidance: a JS
   runtime and EJS to solve YouTube's challenges, browser impersonation, the `sleep` request preset,
   guest sessions only (no account cookies), only the `en-orig` caption track (the plain `en` track
   is machine-translated and is the most rate-limited), and stopping at the first 429 with a long,
   doubling back-off instead of retrying.
3. Each talk is summarised into `data/summaries/<id>.json` following `scripts/SUMMARY_GUIDE.md`:
   from the transcript when there is one, otherwise from the abstract. `scripts/talk_info.py <id>`
   prints a talk's metadata; `scripts/validate_summaries.py` checks every file against the schema.
4. `data/recap.json` holds the cross-talk "What we heard this week" synthesis.
5. `scripts/build_site.py` merges everything into `site/data.js`, which the site loads.

```sh
python3.11 -m venv .venv && .venv/bin/pip install -r requirements-whisper.txt   # needs node >= 22 on PATH
.venv/bin/python scripts/fetch_data.py
.venv/bin/python scripts/transcribe_whisper.py      # or: scripts/fetch_captions.py
python3 scripts/validate_summaries.py
python3 scripts/build_site.py
```

The site itself (`site/index.html`, `styles.css`, `app.js`) is plain HTML, CSS and JavaScript with
no build step. Talk pages are addressable as `#talk-<id>`, in both the flat site and the cinema.

The cinema (`site/cinema/`) is the page's HTML pinned onto pre-rendered photoreal stills and walk videos
of the venue, with a CSS perspective matrix per screen. They are rendered in Blender (Cycles) by
`scripts/blender/build_scene.py`, which builds the venue from Loïc Magnette's Kinepolis model in the Devoxx
Robot Games entry [Ghost Light](https://github.com/LoMagnette/ghost-light) (MIT; `data/venue/venue.json`,
regenerated with `tools/venue/`, see `data/venue/THIRD_PARTY.md`), dressed after this year's photos with CC0
textures and plant models from ambientCG and Poly Haven (`scripts/fetch_textures.py`, `scripts/fetch_models.py`).
`scripts/blender/render_rooms.sh` renders every room overnight and `scripts/blender/publish_renders.py` turns
the renders into `site/cinema/media/`. `tools/ux/` serves the site, screenshots the page for the review agents
and checks every talk and slot for text spilling out of its box (`overflow.mjs`).

Pushing to `main` deploys `site/` to GitHub Pages (`.github/workflows/pages.yml`).

Summaries are machine-written from machine transcripts and can be wrong; the recording is the source of truth.
