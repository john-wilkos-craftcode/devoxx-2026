# Devoxx Belgium 2026, summarised

Every session of Devoxx Belgium 2026 (5 to 9 October, Kinepolis Antwerp), summarised from what the
speakers actually said, as a static site styled like a cinema programme.

Open `site/index.html` directly, or serve it:

```sh
python3 -m http.server -d site 8765   # http://localhost:8765
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
no build step. Talk pages are addressable as `#/talk/<id>`.

Summaries are machine-written from machine transcripts and can be wrong; the recording is the source of truth.
