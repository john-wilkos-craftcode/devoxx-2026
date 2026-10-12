"""Transcribe talks locally with faster-whisper. This is the main transcript source: it is more
accurate than YouTube's auto-captions (punctuation, names) and it avoids YouTube's caption endpoint,
which is the most aggressively rate-limited one. scripts/fetch_captions.py is the fallback for
machines without a GPU.

Per talk: download the audio with yt-dlp (see yt.py for the request etiquette) into
data/raw/audio/, transcribe it on the GPU with Whisper primed with the title, speaker names and
keywords, write data/raw/transcripts/<id>.txt, and delete the audio. The next talk's audio
downloads while the current one is transcribed, which also spaces requests about a minute apart.
On a rate limit (429, bot check) it waits 45 min, doubling up to 4 h, instead of retrying;
a one-off 403 on a stream gets two retries a minute apart.

Usage:
  python scripts/transcribe_whisper.py              # every recorded talk without a transcript,
                                                    # plus talks queued in data/raw/whisper_queue.json
  python scripts/transcribe_whisper.py <id> ...     # specific talks (--force to replace transcripts)
Needs: pip install -r requirements-whisper.txt, ffmpeg and an NVIDIA GPU (4 GB is enough).
"""
import argparse
import ctypes
import glob
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AUDIO = RAW / "audio"
TRANSCRIPTS = RAW / "transcripts"
SOURCES = RAW / "transcript_sources.json"
QUEUE = RAW / "whisper_queue.json"


def preload_cuda_libs():
    """The pip CUDA wheels aren't on the loader path; load them by full path first."""
    import site
    for sp in site.getsitepackages():
        for pattern in ("nvidia/cublas/lib/libcublas*.so*", "nvidia/cudnn/lib/libcudnn*.so*"):
            for lib in sorted(glob.glob(os.path.join(sp, pattern))):
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


def download_audio(video_id):
    """Returns the audio path, None if the download failed, or raises yt.Blocked.
    A 403 gets two retries a minute apart (stream URLs are flaky); a 429 propagates."""
    AUDIO.mkdir(parents=True, exist_ok=True)
    existing = [p for p in AUDIO.glob(f"{video_id}.*") if not p.name.endswith(".part")]
    if existing:
        return existing[0]
    for attempt in range(3):
        try:
            yt.run(["-f", "bestaudio[ext=m4a]/bestaudio", "-o", str(AUDIO / "%(id)s.%(ext)s"),
                    f"https://www.youtube.com/watch?v={video_id}"])
            break
        except yt.Forbidden:
            if attempt == 2:
                return None
            time.sleep(60)
    return next((p for p in AUDIO.glob(f"{video_id}.*") if not p.name.endswith(".part")), None)


def prompt_for(talk):
    """A plain sentence, not 'Speakers: ... Topics: ...': Whisper sometimes loops on label words
    from the prompt ("Topics. Topics. Topics.")."""
    names = " and ".join(s["name"] for s in talk["speakers"])
    return f"{talk['title']}, a talk at Devoxx Belgium by {names} about {', '.join(talk['keywords'])}."


LOOP = re.compile(r"((?:\b[\w']+[.,!?]?\s+){1,3})\1{7,}")


def looped_words(text):
    """Words inside hallucination loops: the same 1-3 words repeated 8+ times in a row."""
    return sum(len(m.group(0).split()) for m in LOOP.finditer(text + " "))


def transcribe(pipeline, audio, talk):
    """Primed with names for spelling; if that produces a loop, retry unprimed and keep the better one."""
    def run(prompt):
        segments, info = pipeline.transcribe(str(audio), language="en", batch_size=8, initial_prompt=prompt)
        return yt.format_transcript((seg.start, seg.text.strip()) for seg in segments), info.duration

    text, duration = run(prompt_for(talk))
    if looped_words(text) > 12:
        retry, _ = run(None)
        if looped_words(retry) < looped_words(text):
            text = retry
    return text, duration


def save(path, data):
    path.write_text(json.dumps(data, indent=1, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", type=int)
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--force", action="store_true", help="replace existing transcripts")
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--backoff-minutes", type=float, default=45)
    ap.add_argument("--max-hours", type=float, default=10)
    args = ap.parse_args()

    talks = {t["id"]: t for t in json.loads((ROOT / "data" / "talks_base.json").read_text())}
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    queue = json.loads(QUEUE.read_text()) if QUEUE.exists() else {}
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    if args.ids:
        todo = [i for i in args.ids if args.force or not (TRANSCRIPTS / f"{i}.txt").exists()]
    else:
        # Queued talks first (their caption transcripts are unusable), then most-bookmarked first.
        todo = [int(i) for i in queue] + sorted(
            (i for i, t in talks.items() if not (TRANSCRIPTS / f"{i}.txt").exists() and str(i) not in queue),
            key=lambda i: -talks[i]["favourites"])
    todo = [i for i in todo if talks[i]["videoId"]]
    # Talks given twice share a recording: transcribe it once.
    seen, unique = set(), []
    for i in todo:
        if talks[i]["videoId"] not in seen:
            seen.add(talks[i]["videoId"])
            unique.append(i)
    print(f"whisper: {len(unique)} recordings to transcribe", flush=True)
    if not unique:
        return

    preload_cuda_libs()
    from faster_whisper import BatchedInferencePipeline, WhisperModel
    pipeline = BatchedInferencePipeline(WhisperModel(args.model, device="cuda", compute_type="int8_float16"))
    deadline = time.time() + args.max_hours * 3600
    backoff = args.backoff_minutes * 60
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(download_audio, talks[unique[0]]["videoId"])
    done = 0

    i = 0
    while i < len(unique) and time.time() < deadline:
        talk = talks[unique[i]]
        try:
            audio = pending.result()
        except yt.Blocked as e:
            wait = min(backoff, max(0, deadline - time.time()))
            print(f"whisper: blocked ({e}); waiting {wait / 60:.0f} min", flush=True)
            time.sleep(wait)
            backoff = min(backoff * 2, 4 * 3600)
            pending = pool.submit(download_audio, talk["videoId"])
            continue
        backoff = args.backoff_minutes * 60
        if i + 1 < len(unique):  # prefetch the next one while the GPU works
            pending = pool.submit(download_audio, talks[unique[i + 1]]["videoId"])
        i += 1
        if audio is None:
            print(f"whisper: {talk['id']} audio download failed, skipping", flush=True)
            continue

        t0 = time.time()
        text, duration = transcribe(pipeline, audio, talk)
        for twin in (t for t in talks.values() if t["videoId"] == talk["videoId"]):
            (TRANSCRIPTS / f"{twin['id']}.txt").write_text(text)
            sources[str(twin["id"])] = f"whisper:{args.model}"
            queue.pop(str(twin["id"]), None)
        save(SOURCES, sources)
        save(QUEUE, queue)
        if not args.keep_audio:
            audio.unlink()
        done += 1
        print(f"whisper: {talk['id']} done ({duration / 60:.0f} min audio in {time.time() - t0:.0f}s), "
              f"{done}/{len(unique)}", flush=True)

    pool.shutdown(wait=False, cancel_futures=True)
    print(f"whisper: finished, {done}/{len(unique)} transcribed", flush=True)


if __name__ == "__main__":
    sys.exit(main())
