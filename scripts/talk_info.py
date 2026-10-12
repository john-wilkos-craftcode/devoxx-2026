"""Print metadata for one or more talks: python3 scripts/talk_info.py <id> [<id>...]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sources_file = ROOT / "data" / "raw" / "transcript_sources.json"
sources = json.loads(sources_file.read_text()) if sources_file.exists() else {}
talks = {t["id"]: t for t in json.loads((ROOT / "data" / "talks_base.json").read_text())}

for arg in sys.argv[1:]:
    t = talks[int(arg)]
    tr = ROOT / "data" / "raw" / "transcripts" / f"{t['id']}.txt"
    print(f"# {t['id']}: {t['title']}")
    print(f"Type: {t['type']} ({t['duration']} min) | Track: {t['track']} | Level: {t['level']}")
    for s in t["speakers"]:
        print(f"Speaker: {s['name']} ({s['company'] or 'n/a'})")
    print(f"Keywords: {', '.join(t['keywords'])}")
    print(f"Transcript: {tr if tr.exists() else 'none'}"
          + (f" ({len(tr.read_text().split())} words, from {sources.get(str(t['id']), 'unknown')})"
             if tr.exists() else ""))
    print(f"\nAbstract:\n{t['abstract']}\n")
