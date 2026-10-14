"""Fetch each recording's chapters as YouTube shows them on its scrubber (from the description, or YouTube's automatic
chapters), so the cinema's laptop can offer the same chapters the player displays.

    .venv/bin/python scripts/fetch_chapters.py

Writes data/raw/yt_chapters.json ({videoId: [[start_seconds, title], ...] or []}). Resumable: videos already fetched are
skipped. Metadata only (no download), through yt.py's guest, rate-limit-aware setup; stops at the first sign of a block.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "yt_chapters.json"
done = json.loads(OUT.read_text()) if OUT.exists() else {}
talks = json.loads((ROOT / "data" / "talks_base.json").read_text())
talks = talks["talks"] if isinstance(talks, dict) else talks
ids = sorted({t["videoId"] for t in talks if t.get("videoId")} - set(done))
print(f"{len(ids)} to fetch, {len(done)} already")
for i, vid in enumerate(ids):
    try:
        code, out = yt.run(["--skip-download", "--no-warnings", "--print", "%(chapters)j", f"https://www.youtube.com/watch?v={vid}"])
    except yt.Blocked as e:
        sys.exit(f"blocked, stopping: {e}")
    except yt.Forbidden:
        continue
    line = out.strip().splitlines()[-1] if out.strip() else "null"
    if line == "NA":                       # no chapters on this one
        line = "[]"
    try:
        ch = json.loads(line) or []
    except json.JSONDecodeError:
        print(f"{vid}: {line[:120]}")
        continue
    done[vid] = [[round(c["start_time"]), c["title"]] for c in ch]
    OUT.write_text(json.dumps(done, indent=0))
    print(f"{i + 1}/{len(ids)} {vid}: {len(done[vid])} chapters", flush=True)
