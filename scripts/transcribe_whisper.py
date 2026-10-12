"""Transcribe talks locally with faster-whisper, for when YouTube captions are missing,
in the wrong language, or too garbled. Writes the same format as fetch_data.py.

Downloads audio with yt-dlp into data/raw/audio/ (gitignored), then transcribes on the GPU,
priming Whisper with the title, speaker names and keywords so names come out right.

Usage: python scripts/transcribe_whisper.py <id> [<id> ...] [--model large-v3-turbo] [--force]
Needs: pip install faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*", plus yt-dlp and ffmpeg.
"""
import argparse
import ctypes
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AUDIO = RAW / "audio"
TRANSCRIPTS = RAW / "transcripts"
SOURCES = RAW / "transcript_sources.json"


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
    AUDIO.mkdir(parents=True, exist_ok=True)
    existing = list(AUDIO.glob(f"{video_id}.*"))
    if existing:
        return existing[0]
    subprocess.run(["yt-dlp", "-q", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", str(AUDIO / "%(id)s.%(ext)s"),
                    f"https://www.youtube.com/watch?v={video_id}"], check=True)
    return next(AUDIO.glob(f"{video_id}.*"))


def prompt_for(talk):
    names = ", ".join(s["name"] for s in talk["speakers"])
    return (f"Devoxx Belgium 2026 talk: {talk['title']}. Speakers: {names}. "
            f"Topics: {', '.join(talk['keywords'])}. Java, JVM, Devoxx.")


def transcribe(model, audio, talk):
    segments, info = model.transcribe(str(audio), language="en", vad_filter=True, beam_size=5,
                                      initial_prompt=prompt_for(talk))
    parts, next_mark = [], 0.0
    for seg in segments:
        if seg.start >= next_mark:
            parts.append(f"\n[{int(seg.start // 60):02d}:{int(seg.start % 60):02d}]")
            next_mark = seg.start + 60
        parts.append(seg.text.strip())
    return " ".join(parts).replace(" \n", "\n").strip(), info.duration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+", type=int)
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--force", action="store_true", help="overwrite existing caption transcripts")
    args = ap.parse_args()

    talks = {t["id"]: t for t in json.loads((ROOT / "data" / "talks_base.json").read_text())}
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    preload_cuda_libs()
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cuda", compute_type="int8_float16")

    for tid in args.ids:
        talk = talks[tid]
        dest = TRANSCRIPTS / f"{tid}.txt"
        if not talk["videoId"]:
            print(f"{tid}: no video, skipping")
            continue
        if dest.exists() and not args.force:
            print(f"{tid}: transcript exists, use --force to replace")
            continue
        t0 = time.time()
        try:
            audio = download_audio(talk["videoId"])
        except subprocess.CalledProcessError as e:
            print(f"{tid}: audio download failed ({e})", file=sys.stderr)
            continue
        text, duration = transcribe(model, audio, talk)
        dest.write_text(text)
        sources[str(tid)] = f"whisper:{args.model}"
        SOURCES.write_text(json.dumps(sources, indent=1, sort_keys=True))
        print(f"{tid}: {duration / 60:.0f} min of audio in {time.time() - t0:.0f}s, {len(text.split())} words")


if __name__ == "__main__":
    main()
