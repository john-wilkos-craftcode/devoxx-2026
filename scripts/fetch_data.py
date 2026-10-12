"""Fetch Devoxx Belgium 2026 talks, schedule, YouTube matches and transcripts.

Outputs:
  data/raw/talks.json            CFP talks
  data/raw/schedule.json         all schedule slots (Mon-Fri)
  data/raw/videos.json           Devoxx channel videos (id, title)
  data/talks_base.json           joined talk records (no summaries yet)
  data/raw/transcripts/<id>.txt  plain-text transcript per talk (gitignored)

Usage: python scripts/fetch_data.py [--skip-videos] [--skip-transcripts]
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TRANSCRIPTS = RAW / "transcripts"
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
    out = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--playlist-end", str(limit),
         "--print", "%(id)s\t%(title)s", CHANNEL],
        capture_output=True, text=True, check=True,
    ).stdout
    videos = [dict(zip(("id", "title"), line.split("\t", 1)))
              for line in out.splitlines() if "\t" in line]
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
    surnames = [norm(s.get("lastName") or "") for s in talk["speakers"]]
    if any(sn and sn in norm(video["title"]) for sn in surnames):
        return score + 0.1
    return score if score >= 0.9 else 0.0  # loose title match with other speakers = different talk


def assign_videos(talks, videos):
    """Greedy one-to-one assignment, best-scoring pairs first."""
    pairs = sorted(((score_match(t, v), t["id"], v["id"]) for t in talks for v in videos), reverse=True)
    by_vid = {v["id"]: v for v in videos}
    out, used = {}, set()
    for score, tid, vid in pairs:
        if score < 0.8:
            break
        if tid not in out and vid not in used:
            out[tid] = (by_vid[vid], score)
            used.add(vid)
    # A talk given twice (e.g. Tools-in-Action and Conference) has one recording: share it.
    key = lambda t: (norm(t["title"]), tuple(sorted(s["id"] for s in t["speakers"])))
    by_key = {key(t): out[t["id"]] for t in talks if t["id"] in out}
    for t in talks:
        if t["id"] not in out and key(t) in by_key:
            out[t["id"]] = by_key[key(t)]
    return out


def fetch_transcript(api, video_id, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(3):
        try:
            t = api.fetch(video_id, languages=["en", "en-US", "en-GB", "nl", "fr"])
            # Plain text with a [mm:ss] marker roughly every minute, so summaries can cite chapters.
            parts, next_mark = [], 0.0
            for seg in t:
                if seg.start >= next_mark:
                    parts.append(f"\n[{int(seg.start // 60):02d}:{int(seg.start % 60):02d}]")
                    next_mark = seg.start + 60
                parts.append(seg.text.replace("\n", " "))
            text = re.sub(r"\[(music|applause|laughter)\]", "", " ".join(parts), flags=re.I)
            dest.write_text(re.sub(r"[ \t]+", " ", text).strip())
            return True
        except Exception as e:  # noqa: BLE001 - network/YouTube errors vary
            if type(e).__name__ in ("IpBlocked", "RequestBlocked") or "429" in str(e):
                raise  # caller cools down; retrying straight away only extends the block
            last = e
            time.sleep(2 + attempt * 3)
    print(f"  transcript failed {video_id}: {type(last).__name__}", file=sys.stderr)
    return False


def fetch_all_transcripts(records, pace, cooldown, max_hours):
    """YouTube IP-blocks bursts after a few dozen requests, so go slowly and
    back off for `cooldown` seconds whenever blocked."""
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    deadline = time.time() + max_hours * 3600
    todo = [r for r in records if r["videoId"] and not (TRANSCRIPTS / f"{r['id']}.txt").exists()]
    print(f"{len(todo)} transcripts to fetch", flush=True)
    i = 0
    while i < len(todo) and time.time() < deadline:
        r = todo[i]
        try:
            fetch_transcript(api, r["videoId"], TRANSCRIPTS / f"{r['id']}.txt")
            i += 1
            if i % 10 == 0:
                print(f"  transcripts {i}/{len(todo)}", flush=True)
            time.sleep(pace)
        except Exception as e:  # noqa: BLE001
            print(f"  blocked ({type(e).__name__}) at {i}/{len(todo)}, cooling down {cooldown}s", flush=True)
            time.sleep(cooldown)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-videos", action="store_true")
    ap.add_argument("--skip-transcripts", action="store_true")
    ap.add_argument("--pace", type=float, default=20, help="seconds between transcript requests")
    ap.add_argument("--cooldown", type=float, default=900, help="seconds to wait when YouTube blocks")
    ap.add_argument("--max-hours", type=float, default=4)
    ap.add_argument("--video-limit", type=int, default=600)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)

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
        })

    if not args.skip_transcripts:
        fetch_all_transcripts(records, args.pace, args.cooldown, args.max_hours)
    for r in records:
        p = TRANSCRIPTS / f"{r['id']}.txt"
        r["hasTranscript"] = p.exists() and p.stat().st_size > 500

    (ROOT / "data" / "talks_base.json").write_text(json.dumps(records, indent=1, ensure_ascii=False))
    print(f"matched videos: {sum(1 for r in records if r['videoId'])}/{len(records)}, "
          f"transcripts: {sum(r['hasTranscript'] for r in records)}")


if __name__ == "__main__":
    main()
