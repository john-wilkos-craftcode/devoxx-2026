#!/usr/bin/env python3
"""The shared data for the main-menu variants (design/menu-variants/*): every talk with its summary fields and its
public signals, the conference recap (headline, verdicts, debates) and provisional "watch first" picks. Read-only
inputs: site/data.js (talks, summaries, recap) and the newest talk-metrics snapshot from the workNotes vault (YouTube
views and likes, Devoxx hearts).
  python3 design/menu-variants/make_data.py   ->  design/menu-variants/data.js  (window.MENU)
"""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = Path("/mnt/c/Users/wilkojo/OneDrive - Cronos/Documenten/workNotes/CraftCode/Devoxx 2026/data/dvbe26")
THIN = 20                                       # under this many likes the like rate is noise (talk-metrics note)

src = (ROOT / "site/data.js").read_text()
site = json.loads(src[src.index("{"):src.rindex("}") + 1])
snap_file = sorted(SNAP.glob("*.json"))[-1]
snap = {t["talkId"]: t for t in json.loads(snap_file.read_text())["talks"]}

vids = [t["video"] for t in snap.values() if t.get("video") and t["video"].get("views")]
avg = sum(v["likes"] or 0 for v in vids) / sum(v["views"] for v in vids)
P = statistics.median(v["views"] for v in vids)


def room_no(room):
    try:
        return int((room or "").split()[-1])
    except ValueError:
        return None


talks = []
for t in site["talks"]:
    s, m = t.get("s") or {}, snap.get(t["id"], {})
    v = m.get("video") or {}
    likes, views = v.get("likes") or 0, v.get("views") or 0
    n = room_no(t.get("room"))
    talks.append({
        "id": t["id"], "title": t["title"],
        "speakers": [{"name": p["name"], "company": p.get("company") or ""} for p in t.get("speakers", [])],
        "room": t.get("room"), "start": t.get("start"), "end": t.get("end"), "type": t.get("type"),
        "track": t.get("track"), "level": t.get("level"), "minutes": round((t.get("videoLength") or 0) / 60) or t.get("duration"),
        "keywords": t.get("keywords", []), "themes": s.get("themes", []),
        "tldr": s.get("tldr"), "watchIf": s.get("watchIf"), "takeaway": (s.get("takeaways") or [None])[0],
        "videoId": t.get("videoId"),
        "hearts": t.get("favourites") or m.get("hearts") or 0,
        "views": views or None, "likes": likes if views else None,
        "likeRate": round(100 * (likes + P * avg) / (views + P), 2) if views else None,   # likes per 100 views, pulled to the mean
        "thin": bool(views) and likes < THIN,
        "seat": n is not None and 3 <= n <= 10,   # rooms 3-10 have a seat to walk to; the others open as a summary
    })
by_id = {t["id"]: t for t in talks}


def score(t):   # provisional: like rate where it means something, else reach; no video sorts last
    if not t["views"]:
        return -1
    return (t["likeRate"] if not t["thin"] else avg * 100) * 2 + min(t["views"], 20000) / 4000


picks = []
for tr in site["recap"]["trends"]:
    ids = [i for i in tr["talkIds"] if i in by_id and by_id[i]["views"]]
    if ids:
        best = max(ids, key=lambda i: score(by_id[i]))
        picks.append({"verdict": tr["title"], "talkId": best, "why": by_id[best]["watchIf"]})

out = {
    "event": "Devoxx Belgium 2026", "dates": "5-9 October 2026", "venue": "Kinepolis Antwerp",
    "signals": {"snapshot": snap_file.stem, "avgLikeRate": round(avg * 100, 2), "thinBelowLikes": THIN,
                "note": "views = reach; likes per 100 views = approval, noise under 20 likes; hearts = interest before the talk"},
    "recap": site["recap"], "picks": picks, "picksNote": "provisional, from the signals; editor's picks to follow",
    "talks": talks,
}
(Path(__file__).parent / "data.js").write_text("window.MENU = " + json.dumps(out, ensure_ascii=False) + ";\n")
print(f"{len(talks)} talks, {len(picks)} picks, snapshot {snap_file.stem}")
