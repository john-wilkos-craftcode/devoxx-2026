"""Validate summary files: python3 scripts/validate_summaries.py [<id> ...]  (no args = all)"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARIES = ROOT / "data" / "summaries"
THEMES = set(re.findall(r"^- `(.+?)`$", (ROOT / "scripts" / "SUMMARY_GUIDE.md").read_text(), re.M))
TS = re.compile(r"^\d{2,3}:\d{2}$")


def check(path):
    errs = []
    try:
        s = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        return [f"invalid JSON: {e}"]
    if str(s.get("id")) != path.stem:
        errs.append("id does not match filename")
    if s.get("source") not in ("transcript", "abstract"):
        errs.append("source must be transcript|abstract")
    for key, typ in [("tldr", str), ("watchIf", str), ("summary", list), ("keyPoints", list),
                     ("takeaways", list), ("quotes", list), ("chapters", list), ("tech", list),
                     ("themes", list), ("demo", bool)]:
        if not isinstance(s.get(key), typ):
            errs.append(f"{key} missing or not {typ.__name__}")
    if errs:
        return errs
    if len(s["tldr"].split()) > 40:
        errs.append("tldr too long")
    if not s["summary"] or not s["keyPoints"]:
        errs.append("summary/keyPoints empty")
    if not 1 <= len(s["themes"]) <= 3 or set(s["themes"]) - THEMES:
        errs.append(f"bad themes: {set(s['themes']) - THEMES or len(s['themes'])}")
    for c in s["chapters"]:
        if not TS.match(str(c.get("at", ""))) or not c.get("title"):
            errs.append(f"bad chapter {c}")
    for q in s["quotes"]:
        if not q.get("text") or not TS.match(str(q.get("at", ""))):
            errs.append(f"bad quote {q}")
    if s["source"] == "transcript" and len(s["chapters"]) < 3:
        errs.append("transcript talk needs chapters")
    times = [to_seconds(c["at"]) for c in s["chapters"] if TS.match(str(c.get("at", "")))]
    if times != sorted(times):
        errs.append("chapters out of order")
    transcript = ROOT / "data" / "raw" / "transcripts" / f"{path.stem}.txt"
    if transcript.exists():
        marks = [to_seconds(m) for m in re.findall(r"\[(\d{2,3}:\d{2})\]", transcript.read_text())]
        end = (max(marks) + 60) if marks else 0
        late = [c["at"] for c in s["chapters"] + s["quotes"]
                if TS.match(str(c.get("at", ""))) and to_seconds(c["at"]) > end]
        if late:
            errs.append(f"timestamps past the end of the recording: {late}")
    return errs


def to_seconds(at):
    m, sec = at.split(":")
    return int(m) * 60 + int(sec)


ids = sys.argv[1:] or [p.stem for p in sorted(SUMMARIES.glob("*.json"))]
bad = 0
for i in ids:
    p = SUMMARIES / f"{i}.json"
    errs = check(p) if p.exists() else ["file missing"]
    if errs:
        bad += 1
        print(f"FAIL {i}: " + "; ".join(errs))
print(f"{len(ids) - bad}/{len(ids)} OK")
sys.exit(1 if bad else 0)
