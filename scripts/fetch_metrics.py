"""Snapshot the public YouTube counts for every talk of a Devoxx / VoxxedDays event.

Pulls the programme (talks, speakers, hearts) from the event's public CFP API,
lists the event's playlist on the Devoxx YouTube channel plus the channel's
recent uploads, matches each talk to its video by title and speaker, and reads
views, likes and the comment count from each video's public watch page. Also reads the CFP's public top-ratings list (empty until Devoxx publishes
ratings). Writes one dated JSON file per run to data/metrics/<event>/ in the
repo; scripts/build_menu.py turns the newest one into site/menu.js.

With YT_API_KEY in the environment (a YouTube Data API v3 key; the metrics
workflow passes the repo secret), the counts come from the API's videos.list,
50 videos per call, about 4 quota units a run: reliable from GitHub's runners,
where YouTube leaves the counts off many watch pages. Without it, the counts are
read from the public watch pages. YouTube's page layout is not a stable
interface, so when a parse step finds nothing the script stops with a message
instead of writing an empty snapshot.

    python scripts/fetch_metrics.py                    # Devoxx Belgium 2026, all days
    python scripts/fetch_metrics.py --days monday      # one day only
    python scripts/fetch_metrics.py --event dvuk26 --playlist PL...
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import os

CFP ="https://{event}.cfp.dev/api/public"
API_KEY = os.environ.get("YT_API_KEY", "").strip()
API = "https://www.googleapis.com/youtube/v3"
YOUTUBE = "https://www.youtube.com"
CHANNEL = "@DevoxxForever"
# The consent cookie skips YouTube's EU consent redirect, which would otherwise
# return a consent form instead of the page.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "SOCS=CAI; CONSENT=YES+1",
}
PAUSE = 1.0          # seconds between YouTube requests
MAX_PAGES = 60       # playlist pages of 100 videos; a guard against a token loop
MATCH_THRESHOLD = 0.6
SPEAKER_BONUS = 0.15
VIDEO_KEYS = ("lockupViewModel", "playlistVideoRenderer")
CONTINUATION_KEYS = ("continuationItemViewModel", "continuationItemRenderer")
INITIAL_DATA = re.compile(r"var ytInitialData = (\{.*?\});</script>", re.S)


def fetch(url, body=None, tries=4):
    """GET (or POST a JSON body) and return the response text."""
    headers = dict(HEADERS)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == tries - 1:
                raise
            # YouTube answers 429 when it is asked too fast: wait much longer than for other errors.
            limited = getattr(error, "code", None) == 429
            time.sleep(30 * (attempt + 1) if limited else 2 * (attempt + 1))


def fetch_json(url):
    return json.loads(fetch(url, tries=3))


def when(iso):
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- programme

def programme(event, days):
    """Return (event metadata, talks) from the CFP API; one entry per talk id."""
    base = CFP.format(event=event)
    meta = fetch_json(base + "/event")
    all_days = [link["href"].rstrip("/").rsplit("/", 1)[-1] for link in fetch_json(base + "/schedules")["links"]]
    talks = {}
    for day in [d for d in all_days if not days or d in days]:
        for slot in fetch_json(f"{base}/schedules/{day}"):
            proposal = slot.get("proposal") or {}
            if not proposal.get("id") or proposal["id"] in talks:
                continue  # breaks, and repeats of one talk in overflow rooms
            talks[proposal["id"]] = {
                "talkId": proposal["id"],
                "title": (proposal.get("title") or "").strip(),
                "day": day,
                "start": slot.get("fromDate"),
                "timezone": slot.get("timezone"),
                "room": (slot.get("room") or {}).get("name"),
                "format": (slot.get("sessionType") or {}).get("name"),
                "track": (proposal.get("track") or {}).get("name"),
                "level": proposal.get("audienceLevel"),
                "hearts": proposal.get("totalFavourites"),
                "speakers": [{"id": s.get("id"), "name": s.get("fullName")}
                             for s in (proposal.get("speakers") or slot.get("speakers") or [])],
                "video": None,
            }
    return meta, list(talks.values())


def ratings(event):
    """{talkId: {"rating", "numRatings"}} from the CFP's public top-ratings list, or None when it is empty."""
    request = urllib.request.Request(CFP.format(event=event) + "/ratings/top", headers={"User-Agent": HEADERS["User-Agent"]})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read().decode("utf-8", errors="replace").strip() if response.status == 200 else ""
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    rows = json.loads(body) if body else []
    found = {str(r["id"]): {"rating": r.get("rating"), "numRatings": int(r["numRatings"]) if r.get("numRatings") is not None else None}
             for r in rows if isinstance(r, dict) and r.get("id") is not None and r.get("rating") is not None}
    return found or None


# ------------------------------------------------------------------ YouTube

def initial_data(html, what):
    found = INITIAL_DATA.search(html)
    if not found:
        sys.exit(f"YouTube layout changed: no page data found on the {what} page.")
    return json.loads(found.group(1))


def unwrap(item):
    """A list item's video or continuation payload, looking through one wrapper level."""
    if not isinstance(item, dict):
        return None, None
    if "richItemRenderer" in item:
        item = item["richItemRenderer"].get("content") or {}
    for key in VIDEO_KEYS:
        if key in item:
            return "video", item[key]
    for key in CONTINUATION_KEYS:
        if key in item:
            return "more", item[key]
    return None, None


def first_token(node):
    if isinstance(node, dict):
        if isinstance(node.get("token"), str):
            return node["token"]
        node = list(node.values())
    if isinstance(node, list):
        for child in node:
            token = first_token(child)
            if token:
                return token
    return None


def text_of(node):
    """Text of a title in either of YouTube's two shapes."""
    if not isinstance(node, dict):
        return ""
    if isinstance(node.get("content"), str):
        return node["content"]
    return node.get("simpleText") or "".join(run.get("text", "") for run in node.get("runs", []))


def scan(node, videos):
    """Collect the videos under node; return the next-page token that sits in the same list."""
    token = None
    if isinstance(node, list):
        kinds = [unwrap(item) for item in node]
        if any(kind == "video" for kind, _ in kinds):
            for kind, payload in kinds:
                if kind == "more":
                    token = first_token(payload)
                elif kind == "video" and "contentId" in payload:
                    if payload.get("contentType", "").endswith("VIDEO"):
                        title = ((payload.get("metadata") or {}).get("lockupMetadataViewModel") or {}).get("title")
                        videos.append({"id": payload["contentId"], "title": text_of(title)})
                elif kind == "video" and payload.get("videoId"):
                    videos.append({"id": payload["videoId"], "title": text_of(payload.get("title"))})
            return token
        for child in node:
            token = scan(child, videos) or token
    elif isinstance(node, dict):
        for child in node.values():
            token = scan(child, videos) or token
    return token


def find_playlist(name):
    """Id of the channel playlist whose title equals name, or None."""
    data = initial_data(fetch(f"{YOUTUBE}/{CHANNEL}/playlists"), "channel playlists")
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            lockup = node.get("lockupViewModel")
            if lockup and lockup.get("contentType", "").endswith("PLAYLIST"):
                title = ((lockup.get("metadata") or {}).get("lockupMetadataViewModel") or {}).get("title")
                if text_of(title).strip().lower() == name.strip().lower():
                    return lockup.get("contentId")
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


def listing(url, what, limit=None):
    """The videos a playlist or channel page lists, in page order, without repeats."""
    html = fetch(url)
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html)
    videos = []
    token = scan(initial_data(html, what), videos)
    pages = 1
    while token and key and version and pages < MAX_PAGES and (limit is None or len(videos) < limit):
        time.sleep(PAUSE)
        before = len(videos)
        # The same request the page makes when you scroll to the end of the list.
        reply = json.loads(fetch(
            f"{YOUTUBE}/youtubei/v1/browse?key={key.group(1)}&prettyPrint=false",
            body={"context": {"client": {"clientName": "WEB", "clientVersion": version.group(1),
                                         "hl": "en", "gl": "US"}},
                  "continuation": token}))
        token = scan(reply, videos)
        pages += 1
        if len(videos) == before:
            break
    unique = {}
    for video in videos:
        unique.setdefault(video["id"], video)
    return list(unique.values())[:limit]


def count(text):
    """'1,234' or '1.2K' as an int."""
    text = text.replace(",", "").strip()
    scale = {"K": 1_000, "M": 1_000_000}.get(text[-1:].upper(), 1)
    return int(float(text.rstrip("KkMm")) * scale)


def video_stats(video_id):
    """Public counts from one watch page; a count is None when the page does not show it."""
    html = fetch(f"{YOUTUBE}/watch?v={video_id}")

    def grab(pattern):
        found = re.search(pattern, html)
        return found.group(1) if found else None

    views = grab(r'"viewCount":"(\d+)"')
    likes = grab(r'"likeCount":"(\d+)"') or grab(r"like this video along with ([\d,]+) other")
    comments = (grab(r'"commentCount":\{"simpleText":"([\d,.KM]+)"')
                or grab(r'"contextualInfo":\{"runs":\[\{"text":"([\d,.KM]+)"\}\]'))
    length = grab(r'"lengthSeconds":"(\d+)"')
    return {
        "views": int(views) if views else None,
        "likes": count(likes) if likes else None,
        "comments": count(comments) if comments else None,
        "published": grab(r'"publishDate":"([^"]+)"'),
        "lengthSeconds": int(length) if length else None,
    }


def iso_seconds(duration):
    """'PT1H2M3S' as 3723."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not m:
        return None
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + se


def api_stats(video_ids):
    """Counts for many videos from the YouTube Data API (videos.list, 50 ids a call, 1 quota unit each)."""
    out = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        url = (f"{API}/videos?part=statistics,contentDetails,snippet&maxResults=50"
               f"&id={','.join(batch)}&key={API_KEY}")
        for item in json.loads(fetch(url)).get("items", []):
            st, sn = item.get("statistics", {}), item.get("snippet", {})
            out[item["id"]] = {
                "views": int(st["viewCount"]) if "viewCount" in st else None,
                "likes": int(st["likeCount"]) if "likeCount" in st else None,
                "comments": int(st["commentCount"]) if "commentCount" in st else None,
                "published": sn.get("publishedAt"),
                "lengthSeconds": iso_seconds(item.get("contentDetails", {}).get("duration")),
            }
    return out


# ----------------------------------------------------------------- matching

def words(text):
    """Lower-case words with accents and punctuation removed."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", plain.lower()).split()


def split_video_title(title):
    """('Talk title', 'Speaker, Speaker') from the channel's 'Talk title by Speaker, Speaker'."""
    cut = title.lower().rfind(" by ")
    return (title[:cut], title[cut + 4:]) if cut > 0 else (title, "")


def similarity(talk, video):
    title, speakers = split_video_title(video["title"])
    a, b = set(words(talk["title"])), set(words(title))
    if not a or not b:
        return 0.0
    score = len(a & b) / len(a | b)
    credited = set(words(speakers))
    surnames = {words(s["name"])[-1] for s in talk["speakers"] if words(s["name"] or "")}
    if surnames & credited:
        score += SPEAKER_BONUS
    return score


def match(talks, videos):
    """Pair each video with at most one talk, best scores first.

    Two talks can share a title (a repeat later in the week); the earlier talk
    then takes the older video, which sits later in the newest-first listings.
    """
    pairs = []
    for talk in talks:
        for video in videos:
            score = similarity(talk, video)
            if score >= MATCH_THRESHOLD:
                pairs.append((-score, talk["start"] or "", -video["position"], talk["talkId"], video["id"]))
    by_talk = {t["talkId"]: t for t in talks}
    by_video = {v["id"]: v for v in videos}
    used = set()
    for neg_score, _, _, talk_id, video_id in sorted(pairs):
        talk = by_talk[talk_id]
        if talk["video"] is None and video_id not in used:
            used.add(video_id)
            talk["video"] = {"id": video_id, "title": by_video[video_id]["title"],
                             "matchScore": round(-neg_score, 2)}
    return [v for v in videos if v["id"] not in used]


# --------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--event", default="dvbe26", help="CFP event slug (default: dvbe26)")
    parser.add_argument("--days", nargs="*", default=[], help="only these days, e.g. monday tuesday")
    parser.add_argument("--playlist", help="YouTube playlist id; found by event name when omitted")
    parser.add_argument("--uploads", type=int, default=300,
                        help="also look through this many recent channel uploads (default: 300, 0 to skip)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    meta, talks = programme(args.event, [d.lower() for d in args.days])
    print(f"{meta.get('name')}: {len(talks)} talks in the programme")

    playlist = args.playlist or find_playlist(meta.get("name") or "")
    if not playlist:
        sys.exit(f"No playlist named '{meta.get('name')}' on {CHANNEL}; pass --playlist.")
    videos = listing(f"{YOUTUBE}/playlist?list={playlist}", "playlist")
    if not videos:
        sys.exit("YouTube layout changed: the playlist page listed no videos.")
    in_playlist = {v["id"] for v in videos}
    # The playlist lags behind the channel: some published talks are not in it yet.
    uploads = []
    if args.uploads:
        uploads = [v for v in listing(f"{YOUTUBE}/{CHANNEL}/videos", "channel videos", args.uploads)
                   if v["id"] not in in_playlist]
    for group in (videos, uploads):
        for position, video in enumerate(group):
            video["position"] = position
    print(f"playlist {playlist}: {len(videos)} videos, plus {len(uploads)} recent uploads that are not in it")

    def read(batch):
        if API_KEY:
            stats = api_stats([t["video"]["id"] for t in batch])
            for talk in batch:
                talk["video"].update(stats.get(talk["video"]["id"]) or {})
            print(f"  {len(stats)}/{len(batch)} from the YouTube Data API")
            return
        for number, talk in enumerate(batch, 1):
            time.sleep(PAUSE)
            try:
                talk["video"].update(video_stats(talk["video"]["id"]))
            except (urllib.error.URLError, TimeoutError) as error:
                print(f"  {talk['video']['id']}: {error}")
            if number % 25 == 0:
                print(f"  {number}/{len(batch)}")

    # The event's own playlist first; uploads only for the talks it leaves open.
    unmatched = match(talks, videos)
    matched = [t for t in talks if t["video"]]
    print(f"matched {len(matched)} talks in the playlist; reading their watch pages...")
    read(matched)

    # An upload can be the same talk given at an earlier event this year, so an
    # upload match must be published in the event week; otherwise try the next one.
    earliest = when(meta["fromDate"]) - timedelta(days=1)
    rejected = []
    while uploads:
        have = {t["talkId"] for t in talks if t["video"]}
        match(talks, uploads)
        fresh = [t for t in talks if t["video"] and t["talkId"] not in have]
        if not fresh:
            break
        print(f"matched {len(fresh)} more talks among the uploads; reading their watch pages...")
        read(fresh)
        taken_ids = {t["video"]["id"] for t in fresh}
        uploads = [v for v in uploads if v["id"] not in taken_ids]
        for talk in fresh:
            published = talk["video"].get("published")
            if published and when(published) < earliest:
                rejected.append({"talkId": talk["talkId"], "id": talk["video"]["id"],
                                 "title": talk["video"]["title"], "published": published})
                talk["video"] = None
        if not any(t["video"] is None for t in fresh):
            break
    matched = [t for t in talks if t["video"]]
    if matched and all(t["video"].get("views") is None for t in matched):
        sys.exit("YouTube layout changed: no view count found on any watch page.")
    # From a datacenter (GitHub's runners) YouTube leaves the counts off a good share of watch pages. Ask those
    # again, slower, after a pause.
    for again in ((1, 2) if not API_KEY else ()):
        blank = [t for t in matched if t["video"].get("views") is None]
        if not blank:
            break
        print(f"{len(blank)} watch pages gave no view count; asking again in {60 * again} s, slower...")
        time.sleep(60 * again)
        global PAUSE
        PAUSE = 3.0 * again
        read(blank)
    fresh = sum(1 for t in matched if t["video"].get("views") is not None)
    if fresh < len(matched) * 0.3:
        sys.exit(f"Incomplete: only {fresh} of {len(matched)} watch pages gave a view count "
                 "(rate limited or layout changed); nothing written.")

    out_dir = Path(__file__).resolve().parent.parent / "data" / "metrics" / args.event
    out_dir.mkdir(parents=True, exist_ok=True)
    # The rest keep their last known counts (counts only grow, so they are a day or so behind), marked "carried".
    earlier = sorted(out_dir.glob("*.json"))
    carried = 0
    if earlier:
        before = {t["talkId"]: t for t in json.loads(earlier[-1].read_text(encoding="utf-8"))["talks"]}
        for talk in matched:
            old = (before.get(talk["talkId"]) or {}).get("video") or {}
            if talk["video"].get("views") is None and old.get("id") == talk["video"]["id"] and old.get("views") is not None:
                for key in ("views", "likes", "comments", "published", "lengthSeconds"):
                    if talk["video"].get(key) is None:
                        talk["video"][key] = old.get(key)
                talk["video"]["carried"] = old.get("carried") or earlier[-1].stem
                carried += 1
    blank = [t for t in matched if t["video"].get("views") is None]
    if len(blank) > max(3, len(matched) // 20):
        sys.exit(f"Incomplete: {len(blank)} of {len(matched)} talks have no view count, fresh or carried; nothing written.")
    print(f"{fresh} fresh view counts, {carried} carried from the previous snapshot, {len(blank)} without")

    taken = datetime.now(timezone.utc)
    out = out_dir / (taken.astimezone().strftime("%Y-%m-%d_%H%M") + ".json")  # local time (UTC on CI)
    rated = ratings(args.event)
    for talk in talks:
        got = (rated or {}).get(str(talk["talkId"])) or {}
        talk["rating"], talk["numRatings"] = got.get("rating"), got.get("numRatings")
    out.write_text(json.dumps({
        "event": args.event,
        "eventName": meta.get("name"),
        "takenAt": taken.isoformat(timespec="seconds"),
        "days": args.days or "all",
        "playlist": playlist,
        "ratingsAvailable": rated is not None,
        "talks": talks,
        "unmatchedVideos": [{"id": v["id"], "title": v["title"]} for v in unmatched],
        "rejectedMatches": rejected,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    print("ratings: " + (f"{len(rated)} talks rated" if rated else "unavailable (the CFP list is empty)"))
    print(f"{len(matched)} talks with a video, {len(talks) - len(matched)} without; "
          f"{len(unmatched)} playlist videos without a talk, "
          f"{len(rejected)} upload matches dropped as older than the event")


if __name__ == "__main__":
    main()
