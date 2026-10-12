# Devoxx Belgium 2026, summarised

Every session of Devoxx Belgium 2026 (5 to 9 October, Kinepolis Antwerp), summarised from what the
speakers actually said, as a static site styled like a cinema programme.

Open `site/index.html` directly, or serve it:

```sh
python3 -m http.server -d site 8765   # http://localhost:8765
```

## How it's built

1. `scripts/fetch_data.py` pulls talks and the schedule from the public CFP API
   (`dvbe26.cfp.dev`), matches each talk to its recording on the Devoxx YouTube channel, and downloads
   the auto-caption transcripts into `data/raw/transcripts/` (gitignored). YouTube rate-limits this
   aggressively, so it goes slowly and backs off when blocked; re-running only fetches what's missing.
2. Each talk is summarised into `data/summaries/<id>.json` following `scripts/SUMMARY_GUIDE.md`:
   from the transcript when there is one, otherwise from the abstract. `scripts/talk_info.py <id>`
   prints a talk's metadata; `scripts/validate_summaries.py` checks every file against the schema.
3. `data/recap.json` holds the cross-talk "What we heard this week" synthesis.
4. `scripts/build_site.py` merges everything into `site/data.js`, which the site loads.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PATH=.venv/bin:$PATH python scripts/fetch_data.py
python3 scripts/validate_summaries.py
python3 scripts/build_site.py
```

The site itself (`site/index.html`, `styles.css`, `app.js`) is plain HTML, CSS and JavaScript with
no build step. Talk pages are addressable as `#/talk/<id>`.

Summaries are machine-written from auto-captions and can be wrong; the recording is the source of truth.
