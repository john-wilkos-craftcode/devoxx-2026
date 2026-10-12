"""Shared yt-dlp setup, following yt-dlp's YouTube guidance as of 2026:

- YouTube serves JavaScript challenges; yt-dlp solves them with its EJS scripts
  (pip "yt-dlp[default]") and an external JS runtime. We use node (>= 22) since it is already here.
- curl_cffi browser impersonation (pip "yt-dlp[curl-cffi]") so requests look like a browser.
- The "sleep" preset (--sleep-requests 0.75, --sleep-subtitles 5, --sleep-interval 10-20),
  with subtitle sleeps raised further by callers: subtitles are YouTube's most rate-limited endpoint.
- Guest sessions only. Cookies tie requests to an account, which risks that account being banned,
  and public videos don't need them.
- At the first sign of rate limiting, stop. Retrying while blocked only extends the block.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

BLOCKED = re.compile(r"HTTP Error 429|Too Many Requests|confirm you.re not a bot|"
                     r"content isn.t available, try again later|HTTP Error 403", re.I)


class Blocked(Exception):
    pass


def yt_dlp_cmd():
    local = Path(sys.executable).parent / "yt-dlp"
    exe = str(local) if local.exists() else shutil.which("yt-dlp")
    if not exe:
        sys.exit("yt-dlp not found: pip install -r requirements.txt")
    return [exe, "--js-runtimes", "node", "--impersonate", "chrome", "--no-progress", "-t", "sleep"]


def run(args, on_line=None):
    """Run yt-dlp, streaming its output. Raises Blocked (after killing the process) on the first
    rate-limit or bot-check message. Returns (returncode, output)."""
    proc = subprocess.Popen(yt_dlp_cmd() + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    out = []
    for line in proc.stdout:
        out.append(line)
        if BLOCKED.search(line):
            proc.kill()
            proc.wait()
            raise Blocked(line.strip())
        if on_line:
            on_line(line)
    proc.wait()
    return proc.returncode, "".join(out)


def format_transcript(segments):
    """(start_seconds, text) pairs -> plain text with a [mm:ss] marker about every minute,
    so summaries can cite chapters."""
    parts, next_mark = [], 0.0
    for start, text in segments:
        if start >= next_mark:
            parts.append(f"\n[{int(start // 60):02d}:{int(start % 60):02d}]")
            next_mark = start + 60
        parts.append(text)
    text = re.sub(r"\[(music|applause|laughter)\]", "", " ".join(parts), flags=re.I)
    return re.sub(r"[ \t]+", " ", text).replace(" \n", "\n").strip()
