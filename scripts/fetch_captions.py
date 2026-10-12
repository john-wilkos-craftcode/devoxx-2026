"""Download each matched talk's original-language YouTube auto-captions, politely.

- Only the 'en-orig' track, one subtitle request per video. YouTube's plain 'en' auto track is
  machine-translated, and translated tracks are the ones YouTube rate-limits hardest (yt-dlp issue
  #13831). Don't widen this to '.*-orig': videos now list ~20 "(Original)" tracks, one per language.
- One batched yt-dlp process (see yt.py) with --sleep-subtitles on top of the 'sleep' preset:
  about 180 videos/hour at the default, under the ~300 videos/hour yt-dlp documents for guests.
- On the first 429 or bot check: stop, wait (45 min, doubling up to 4 h), then resume.
- Talks without an English original track are queued in
  data/raw/whisper_queue.json for scripts/transcribe_whisper.py.

Resumable: re-running skips talks that already have a transcript or a downloaded caption file.
Usage: python scripts/fetch_captions.py [--sleep-subtitles 15] [--backoff-minutes 45] [--max-hours 8]
"""
import argparse
import json
import time
from pathlib import Path

import yt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CAPTIONS = RAW / "captions"          # raw json3 files (gitignored)
TRANSCRIPTS = RAW / "transcripts"    # <talk id>.txt (gitignored)
QUEUE = RAW / "whisper_queue.json"
SOURCES = RAW / "transcript_sources.json"


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def json3_segments(path):
    for ev in json.loads(path.read_text()).get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).replace("\n", " ").strip()
        if text:
            yield ev["tStartMs"] / 1000, text


def caption_file(video_id):
    f = CAPTIONS / f"{video_id}.en-orig.json3"
    return f if f.exists() else None


def convert(talks, queue, sources):
    """Turn downloaded caption files into transcripts."""
    for t in talks:
        dest = TRANSCRIPTS / f"{t['id']}.txt"
        f = caption_file(t["videoId"])
        if dest.exists() or not f:
            continue
        dest.write_text(yt.format_transcript(json3_segments(f)))
        sources[str(t["id"])] = "youtube:en-orig"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep-subtitles", type=float, default=15)
    ap.add_argument("--backoff-minutes", type=float, default=45)
    ap.add_argument("--max-hours", type=float, default=8)
    args = ap.parse_args()
    CAPTIONS.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)

    talks = [t for t in json.loads((ROOT / "data" / "talks_base.json").read_text()) if t["videoId"]]
    queue, sources = load(QUEUE, {}), load(SOURCES, {})
    deadline = time.time() + args.max_hours * 3600
    backoff = args.backoff_minutes * 60

    while True:
        convert(talks, queue, sources)
        QUEUE.write_text(json.dumps(queue, indent=1, sort_keys=True))
        SOURCES.write_text(json.dumps(sources, indent=1, sort_keys=True))
        todo = sorted({t["videoId"] for t in talks
                       if not (TRANSCRIPTS / f"{t['id']}.txt").exists()
                       and str(t["id"]) not in queue and not caption_file(t["videoId"])})
        print(f"captions: {len(todo)} videos to fetch", flush=True)
        if not todo or time.time() > deadline:
            break
        batch = RAW / "caption_batch.txt"
        batch.write_text("".join(f"https://www.youtube.com/watch?v={v}\n" for v in todo))
        done = [0]

        def progress(line):
            if "Writing video subtitles" in line:
                done[0] += 1
                if done[0] % 10 == 0:
                    print(f"captions: {done[0]}/{len(todo)} downloaded", flush=True)

        try:
            yt.run(["--skip-download", "--write-auto-subs", "--sub-langs", "en-orig", "--sub-format", "json3",
                    "--sleep-subtitles", str(args.sleep_subtitles), "--ignore-errors",
                    "-o", str(CAPTIONS / "%(id)s.%(ext)s"), "-a", str(batch)], on_line=progress)
        except yt.Blocked as e:
            wait = min(backoff, max(0, deadline - time.time()))
            print(f"captions: blocked ({e}); waiting {wait / 60:.0f} min before one more try", flush=True)
            time.sleep(wait)
            backoff = min(backoff * 2, 4 * 3600)
            continue
        # A full pass without blocks: whatever is still missing has no English original captions.
        convert(talks, queue, sources)
        for t in talks:
            if not (TRANSCRIPTS / f"{t['id']}.txt").exists() and str(t["id"]) not in queue \
                    and not caption_file(t["videoId"]):
                queue[str(t["id"])] = "no English original captions on YouTube"
        backoff = args.backoff_minutes * 60

    QUEUE.write_text(json.dumps(queue, indent=1, sort_keys=True))
    SOURCES.write_text(json.dumps(sources, indent=1, sort_keys=True))
    have = sum((TRANSCRIPTS / f"{t['id']}.txt").exists() for t in talks)
    print(f"captions: done. transcripts for {have}/{len(talks)} recorded talks, {len(queue)} queued for Whisper",
          flush=True)


if __name__ == "__main__":
    main()
