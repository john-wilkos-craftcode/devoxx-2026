"""Fetch Devoxx Belgium 2026 talks, schedule, YouTube matches and transcripts.

Outputs:
  data/raw/talks.json            CFP talks
  data/raw/schedule.json         all schedule slots (Mon-Fri)
  data/raw/videos.json           Devoxx channel videos (id, title)
  data/talks_base.json           joined talk records (no summaries yet)
  data/raw/transcripts/<id>.txt  plain-text transcript per talk (gitignored)

Usage: python scripts/fetch_data.py [--skip-videos] [--skip-search] [--skip-transcripts]
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


def match_video(talk, videos):
    """Video titles look like '<talk title>  by <speakers>'. Score on the title part,
    require a speaker surname in the video title to accept weaker title matches."""
    t = norm(talk["title"])
    surnames = [norm(s.get("lastName") or "") for s in talk["speakers"]]
    best, best_score = None, 0.0
    for v in videos:
        vt = norm(re.split(r"\s+(?:by|By|BY)\s+|\s+[–-]\s+", v["title"])[0])
        score = difflib.SequenceMatcher(None, t, vt).ratio()
        if vt and (t.startswith(vt) or vt.startswith(t)) and len(vt) > 15:
            score = max(score, 0.95)
        has_speaker = any(sn and sn in norm(v["title"]) for sn in surnames)
        if has_speaker:
            score += 0.1
        elif score < 0.9:
            continue  # loose title match with other speakers = different talk
        if score > best_score:
            best, best_score = v, score
    return (best, best_score) if best_score >= 0.8 else (None, best_score)


def search_video(talk):
    """Fallback for talks not in the channel's recent uploads: YouTube search,
    accepting only Devoxx uploads whose title matches and names a speaker."""
    names = ", ".join(s["fullName"] for s in talk["speakers"][:2]) if talk["speakers"] else ""
    q = f"ytsearch5:{talk['title']} {names} Devoxx"
    try:
        out = subprocess.run(["yt-dlp", "--flat-playlist", "--print",
                              "%(id)s\t%(channel)s\t%(title)s", q],
                             capture_output=True, text=True, timeout=90).stdout
    except subprocess.TimeoutExpired:
        return None
    cands = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and "devoxx" in parts[1].lower():
            cands.append({"id": parts[0], "title": parts[2]})
    video, score = match_video(talk, cands)
    return video if video and score >= 0.85 else None


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
    ap.add_argument("--skip-search", action="store_true")
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

    records = []
    for t in talks:
        sl = sorted(by_proposal.get(t["id"], []), key=lambda s: (s.get("overflow", False), s["fromDate"]))
        main_slot = sl[0] if sl else None
        video, score = match_video(t, videos)
        if not video and not args.skip_search and (t.get("sessionType") or {}).get("name") not in ("Hands-on Lab", "BOF", "Keynote Overflow"):
            video = search_video(t)
            if video:
                score = 0.85
                print(f"  search matched: {t['title'][:50]} -> {video['title'][:60]}")
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
