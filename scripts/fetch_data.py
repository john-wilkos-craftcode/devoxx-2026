"""Fetch Devoxx Belgium 2026 talks and schedule, and match them to their YouTube recordings.

Outputs:
  data/raw/talks.json            CFP talks
  data/raw/schedule.json         all schedule slots (Mon-Fri)
  data/raw/videos.json           Devoxx channel videos (id, title), newest first
  data/talks_base.json           joined talk records (no summaries yet)

Transcripts are a separate, slow step: scripts/fetch_captions.py.
Usage: python scripts/fetch_data.py [--skip-videos]
"""
import argparse
import difflib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import yt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CFP = "https://dvbe26.cfp.dev/api/public"
CHANNEL = "https://www.youtube.com/@DevoxxForever/videos"
BOUNDARY = re.compile(r"Devoxx Belgium is Next Week|Speaking next week at Devoxx Belgium", re.I)
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_cfp():
    talks = get_json(f"{CFP}/talks")
    slots = []
    for day in DAYS:
        slots += get_json(f"{CFP}/schedules/{day}")
    (RAW / "talks.json").write_text(json.dumps(talks, indent=1))
    (RAW / "schedule.json").write_text(json.dumps(slots, indent=1))
    return talks, slots


def fetch_videos(limit):
    """One flat listing of the channel: a handful of requests, no per-video calls."""
    _, out = yt.run(["--flat-playlist", "--playlist-end", str(limit), "--no-warnings",
                     "--print", "%(id)s\t%(duration)s\t%(title)s", CHANNEL])
    videos = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            vid, dur, title = parts
            videos.append({"id": vid, "title": title, "duration": int(float(dur)) if dur not in ("NA", "None") else None})
    (RAW / "videos.json").write_text(json.dumps(videos, indent=1))
    return videos


def be26_uploads(videos):
    """The channel hosts every Devoxx event, newest first. Belgium 2026 recordings are
    everything uploaded after the pre-conference promo, so cut the list there; older
    editions often have talks with the same title and speakers."""
    for i, v in enumerate(videos):
        if BOUNDARY.search(v["title"]):
            return videos[:i]
    return videos


def video_talk_title(title):
    """'<talk title>  by <speakers>': split on the last ' by ' (titles can contain 'by')."""
    parts = re.split(r"\s+by\s+", title, flags=re.I)
    if len(parts) == 1:
        parts = re.split(r"\s+[–-]\s+", title)  # some use '<title> – <speakers>'
    return " by ".join(parts[:-1]) if len(parts) > 1 else title


def score_match(talk, video):
    t, vt = norm(talk["title"]), norm(video_talk_title(video["title"]))
    score = difflib.SequenceMatcher(None, t, vt).ratio()
    if len(vt) > 15 and (t.startswith(vt) or vt.startswith(t)):
        score = max(score, 0.95)  # truncated or extended titles
    # A session given twice (e.g. Tools-in-Action, then Conference) has one title for two slots:
    # prefer the slot whose length fits the recording.
    slot, length = (talk.get("sessionType") or {}).get("duration"), video.get("duration")
    if slot and length:
        score -= 0.05 * min(1.0, abs(length / 60 - slot) / slot)
    surnames = [norm(s.get("lastName") or "") for s in talk["speakers"]]
    if any(sn and sn in norm(video["title"]) for sn in surnames):
        return score + 0.1
    return score if score >= 0.9 else 0.0  # loose title match with other speakers = different talk


def twins(talks):
    """talk id -> id of the same session in another slot (same title and speakers)."""
    key = lambda t: (norm(t["title"]), tuple(sorted(s["id"] for s in t["speakers"])))
    groups = {}
    for t in talks:
        groups.setdefault(key(t), []).append(t["id"])
    return {i: next(j for j in g if j != i) for g in groups.values() if len(g) == 2 for i in g}


def assign_videos(talks, videos):
    """Greedy one-to-one assignment, best-scoring pairs first. A repeated session's other slot
    stays unmatched (its recording may not be uploaded yet); see twins()."""
    pairs = sorted(((score_match(t, v), t["id"], v["id"]) for t in talks for v in videos), reverse=True)
    by_vid = {v["id"]: v for v in videos}
    out, used = {}, set()
    for score, tid, vid in pairs:
        if score < 0.8:
            break
        if tid not in out and vid not in used:
            out[tid] = (by_vid[vid], score)
            used.add(vid)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-videos", action="store_true")
    ap.add_argument("--video-limit", type=int, default=600)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    talks, slots = fetch_cfp()
    print(f"{len(talks)} talks, {len(slots)} slots")
    by_proposal = {}
    for s in slots:
        if s.get("proposal"):
            by_proposal.setdefault(s["proposal"]["id"], []).append(s)

    videos = (json.loads((RAW / "videos.json").read_text()) if args.skip_videos
              else fetch_videos(args.video_limit))
    print(f"{len(videos)} channel videos")

    videos = be26_uploads(videos)
    matches = assign_videos(talks, videos)
    unmatched = [v["title"] for v in videos if v["id"] not in {m[0]["id"] for m in matches.values()}]
    print(f"{len(videos)} Belgium 2026 uploads; not matched to a talk: {unmatched}")

    twin_of = twins(talks)
    records = []
    for t in talks:
        sl = sorted(by_proposal.get(t["id"], []), key=lambda s: (s.get("overflow", False), s["fromDate"]))
        main_slot = sl[0] if sl else None
        video, score = matches.get(t["id"], (None, 0.0))
        records.append({
            "id": t["id"],
            "title": t["title"].strip(),
            "type": (t.get("sessionType") or {}).get("name"),
            "duration": (t.get("sessionType") or {}).get("duration"),
            "track": (t.get("track") or {}).get("name"),
            "trackIcon": (t.get("track") or {}).get("imageURL"),
            "level": t.get("audienceLevel"),
            "keywords": [k["name"] for k in t.get("keywords") or []],
            "abstract": t.get("description") or "",
            "cfpSummary": t.get("summary") or "",
            "favourites": t.get("totalFavourites") or 0,
            "speakers": [{
                "name": s.get("fullName"),
                "company": s.get("company"),
                "country": s.get("countryName"),
                "image": s.get("imageUrl"),
                "bio": s.get("bio"),
                "linkedin": s.get("linkedInUsername") or None,
                "bluesky": s.get("blueskyUsername") or None,
                "twitter": s.get("twitterHandle") or None,
            } for s in t.get("speakers") or []],
            "start": main_slot["fromDate"] if main_slot else None,
            "end": main_slot["toDate"] if main_slot else None,
            "room": main_slot["room"]["name"] if main_slot and main_slot.get("room") else None,
            "videoId": video["id"] if video else None,
            "videoTitle": video["title"] if video else None,
            "matchScore": round(score, 3),
            "twin": twin_of.get(t["id"]),
        })

    (ROOT / "data" / "talks_base.json").write_text(json.dumps(records, indent=1, ensure_ascii=False))
    print(f"matched videos: {sum(1 for r in records if r['videoId'])}/{len(records)}")


if __name__ == "__main__":
    main()
