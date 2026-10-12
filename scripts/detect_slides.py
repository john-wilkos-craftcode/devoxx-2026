"""Find slide changes in a talk recording: timestamps for "skip to the next slide".

Devoxx recordings put the speaker camera on one side and the slides (or the presenter's screen)
on the other, between a logo bar on top and a sponsor bar below. Per talk:
  1. download a 480p video-only H.264 stream (AV1 decodes far too slowly) into data/raw/video/,
  2. pick the slide side: the one whose outer strip has more fine detail (text) than the camera's,
  3. run ffmpeg scene detection on that crop and keep changes at least MIN_GAP seconds apart,
  4. save a small thumbnail per slide in data/raw/slides/<id>/ (gitignored: frame grabs of the
     recording, published only if the rights allow) and the timestamps in data/slides/<id>.json.

Usage: python scripts/detect_slides.py <id> [<id> ...] [--keep-video]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
VIDEO, THUMBS, OUT = RAW / "video", RAW / "slides", ROOT / "data" / "slides"
TOP, BOTTOM = 0.185, 0.835      # the band between the Devoxx logo bar and the sponsor bar
SPLIT = 0.345                   # camera strip width as a fraction of the frame
MIN_GAP = 12.0                  # seconds; faster changes are builds, scrolling or live typing
SCENE = 0.22


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    return s["width"], s["height"], float(j["format"]["duration"])


def crop_for(side, w, h):
    y0, ch = int(h * TOP), int(h * (BOTTOM - TOP))
    cw = int(w * (1 - SPLIT))
    x0 = int(w * SPLIT) if side == "right" else 0
    return f"crop={cw}:{ch}:{x0}:{y0}"


def strip_detail(path, w, h):
    """Edge energy of the two outer strips, from keyframes only. The camera strip is a dark stage
    with one person; the slide side is text. Motion is no use: live coding moves more than a speaker."""
    y0, ch, sw = int(h * TOP), int(h * (BOTTOM - TOP)), int(w * SPLIT)
    out = {}
    for side, x0 in (("left", 0), ("right", w - sw)):
        r = ffmpeg("-skip_frame", "nokey", "-i", str(path), "-vf",
                   f"crop={sw}:{ch}:{x0}:{y0},scale=240:-1,format=gray,edgedetect=low=0.1:high=0.3,signalstats,"
                   "metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-")
        v = [float(x) for x in re.findall(r"YAVG=([\d.]+)", r.stderr)] or [0.0]
        out[side] = sum(v) / len(v)
    return out


def detect(path, side, w, h):
    # keyframes only (every ~2 s in YouTube streams): ~20x faster to decode, timing within a couple of seconds
    vf = f"{crop_for(side, w, h)},scale=320:-1,select='gt(scene,{SCENE})',showinfo"
    r = ffmpeg("-skip_frame", "nokey", "-i", str(path), "-vf", vf, "-an", "-f", "null", "-")
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    kept = [0.0]
    for t in times:
        if t - kept[-1] >= MIN_GAP:
            kept.append(t)
    return kept


def thumbs(path, side, w, h, times, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        # a beat after the change, so animations and fades have settled
        ffmpeg("-ss", f"{t + 1.5:.2f}", "-i", str(path), "-frames:v", "1",
               "-vf", f"{crop_for(side, w, h)},scale=480:-1", "-q:v", "5", "-y", str(dest / f"{i:03d}.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+", type=int)
    ap.add_argument("--keep-video", action="store_true")
    args = ap.parse_args()
    talks = {t["id"]: t for t in json.loads((ROOT / "data" / "talks_base.json").read_text())}
    VIDEO.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for tid in args.ids:
        t = talks[tid]
        if not t["videoId"]:
            print(f"{tid}: no video")
            continue
        path = next(iter(VIDEO.glob(f"{t['videoId']}.*")), None)
        if not path:
            try:
                yt.run(["-f", "bv*[height<=480][vcodec^=avc1]/bv*[height<=480][ext=mp4]/bv*[height<=480]", "-o", str(VIDEO / "%(id)s.%(ext)s"),
                        f"https://www.youtube.com/watch?v={t['videoId']}"])
            except yt.Blocked as e:
                sys.exit(f"{tid}: YouTube is rate limiting ({e}); stopping")
            except yt.Forbidden:
                print(f"{tid}: download refused (403), skipping")
                continue
            path = next(iter(VIDEO.glob(f"{t['videoId']}.*")), None)
        w, h, duration = probe(path)
        scores = strip_detail(path, w, h)
        side = max(scores, key=scores.get)    # the slides are on the side whose outer strip has more detail
        times = detect(path, side, w, h)
        thumbs(path, side, w, h, times, THUMBS / str(tid))
        (OUT / f"{tid}.json").write_text(json.dumps(
            {"id": tid, "side": side, "slides": [{"at": f"{int(x // 60):02d}:{int(x % 60):02d}", "t": round(x, 1)} for x in times]},
            indent=1))
        print(f"{tid}: {len(times)} slides, slides on the {side} ({duration / 60:.0f} min), scores {scores}")
        if not args.keep_video:
            path.unlink()


if __name__ == "__main__":
    main()
