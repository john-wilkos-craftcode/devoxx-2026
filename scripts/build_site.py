"""Merge talks_base.json, summaries and the recap into site/data.js.

data.js (not .json) so the site also works when index.html is opened from disk.
With --artifact, also writes build/artifact/ for publishing as a claude.ai artifact: the page
without its document wrapper (the artifact adds its own), plus the CSS, JS and data files.
Usage: python3 scripts/build_site.py [--artifact]
"""
import html
import shutil
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def abstract_paragraphs(raw):
    text = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.I)
    text = re.sub(r"</?(p|div|li|ul|ol)[^>]*>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]


def main():
    base = json.loads((DATA / "talks_base.json").read_text())
    talks, missing = [], []
    for t in base:
        p = DATA / "summaries" / f"{t['id']}.json"
        s = json.loads(p.read_text()) if p.exists() else None
        if not s:
            missing.append(t["id"])
        talks.append({
            "id": t["id"],
            "title": t["title"],
            "type": t["type"],
            "duration": t["duration"],
            "track": t["track"],
            "level": t["level"],
            "keywords": t["keywords"],
            "abstract": abstract_paragraphs(t["abstract"]),
            "favourites": t["favourites"],
            "speakers": [{k: sp[k] for k in ("name", "company", "image", "bio", "linkedin", "bluesky", "twitter")}
                         for sp in t["speakers"]],
            "start": t["start"],
            "end": t["end"],
            "room": t["room"],
            "videoId": t["videoId"],
            "s": {k: v for k, v in (s or {}).items() if k != "id"} or None,
        })
    recap_path = DATA / "recap.json"
    recap = json.loads(recap_path.read_text()) if recap_path.exists() else None
    checked = datetime.fromtimestamp((DATA / "raw" / "videos.json").stat().st_mtime, timezone.utc)
    out = {"event": "Devoxx Belgium 2026", "videosCheckedAt": checked.date().isoformat(),
           "talks": talks, "recap": recap}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.js").write_text(
        "window.DEVOXX = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"site/data.js: {len(talks)} talks, {len(talks) - len(missing)} with summaries, "
          f"recap: {'yes' if recap else 'no'}")
    if missing:
        print(f"missing summaries: {' '.join(map(str, missing))}")


def build_artifact():
    site, out = ROOT / "site", ROOT / "build" / "artifact"
    out.mkdir(parents=True, exist_ok=True)
    page = (site / "index.html").read_text()
    head = page[page.index("<head>") + 6:page.index("</head>")]
    body = page[page.index("<body>") + 6:page.index("</body>")]
    keep = [line for line in head.splitlines()
            if "<title>" in line or "fonts.g" in line or 'rel="stylesheet"' in line]
    (out / "index.html").write_text("\n".join(keep) + "\n" + body.strip() + "\n")
    for name in ("styles.css", "app.js", "data.js"):
        shutil.copy(site / name, out / name)
    print(f"{out.relative_to(ROOT)}: index.html, styles.css, app.js, data.js")


if __name__ == "__main__":
    main()
    if "--artifact" in sys.argv:
        build_artifact()
