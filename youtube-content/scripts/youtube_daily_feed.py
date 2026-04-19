#!/usr/bin/env python3
"""
YouTube Daily Feed Scanner
Checks all channels in the feeds directory for new videos.
New videos get transcript + signal review, appended to inbox.md.
Already-seen URLs (in seen.txt) are skipped.

Feeds directory is configurable via YOUTUBE_FEEDS_DIR env var.
Default: ~/.hermes/youtube-feeds/

Usage:
  python3 youtube_daily_feed.py

Output:
  feeds/inbox.md   — new reviews appended
  feeds/seen.txt   — updated with newly processed URLs
  stdout           — summary for cron job delivery
"""

import re
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
FEEDS_DIR = Path(os.environ.get("YOUTUBE_FEEDS_DIR", HOME / ".hermes" / "youtube-feeds"))
CHANNELS_FILE = FEEDS_DIR / "channels.txt"
INBOX_FILE = FEEDS_DIR / "inbox.md"
SEEN_FILE = FEEDS_DIR / "seen.txt"
HERMES_BIN = HOME / ".local" / "bin" / "hermes"
TRANSCRIPT_SCRIPT = HOME / ".hermes" / "skills" / "media" / "compact-youtube-transcript" / "scripts" / "fetch_transcript.py"


def run_cmd(cmd, timeout_sec=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout_sec)
        return result.stdout.strip() or result.stderr.strip() or ""
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


def load_seen():
    if not SEEN_FILE.exists():
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip() and not line.startswith("#"))


def save_seen(url):
    with open(SEEN_FILE, "a") as f:
        f.write(url + "\n")


def load_channels():
    channels = []
    if not CHANNELS_FILE.exists():
        return channels
    with open(CHANNELS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            url = parts[0].strip().rstrip("/")
            label = parts[1].strip() if len(parts) > 1 else url
            channels.append((url, label))
    return channels


def get_recent_videos(channel_url, limit=15):
    videos_url = channel_url + "/videos"
    cmd = (
        f'yt-dlp --flat-playlist --playlist-end {limit} '
        f'--print "%(url)s|%(title)s|%(upload_date>%Y-%m-%d)s" '
        f'"{videos_url}"'
    )
    output = run_cmd(cmd, timeout_sec=60)
    videos = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.search(r"(https://www\.youtube\.com/watch\?v=[\w-]+)\|(.+?)\|(.+)", line)
        if match:
            videos.append((match.group(1), match.group(2).strip(), match.group(3).strip()))
    return videos


def get_transcript(url):
    cmd = f'python3 "{TRANSCRIPT_SCRIPT}" "{url}" --no-timestamps'
    return run_cmd(cmd, timeout_sec=25)


def review_video(title, url, transcript):
    prompt = f"""Title: {title}
URL: {url}

Transcript:
{transcript[:5500]}

Extract the 6-10 highest-signal insights from this video.
Identify the main topics discussed, key arguments or claims made, and any notable insights or takeaways.
Output ONLY as bullet points. One concise sentence per bullet. No introductory or concluding text."""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir="/tmp") as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    cmd = f"""{HERMES_BIN} chat -q "$(cat {tmp_path})" -Q --max-turns 1 -t ''"""
    review = run_cmd(cmd, timeout_sec=50)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    lines = review.split("\n")
    cleaned = [l for l in lines if not l.startswith("session_id:") and not l.startswith("\u26a0\ufe0f")]
    return "\n".join(cleaned).strip()


def append_to_inbox(title, url, date, channel_label, review):
    entry = f"""## {title}
- Channel: {channel_label}
- URL: {url}
- Date: {date}
- Scanned: {datetime.now().strftime("%Y-%m-%d %H:%M")}

{review}

---

"""
    with open(INBOX_FILE, "a") as f:
        f.write(entry)


def main():
    channels = load_channels()
    if not channels:
        print("No channels configured. Add them to: " + str(CHANNELS_FILE))
        return

    seen = load_seen()
    total_new = 0
    results = []

    for channel_url, label in channels:
        print(f"Checking: {label} ({channel_url})")
        videos = get_recent_videos(channel_url, limit=15)

        new_videos = [(url, title, date) for url, title, date in videos if url not in seen]
        if not new_videos:
            print(f"  No new videos.")
            continue

        print(f"  Found {len(new_videos)} new video(s).")

        for url, title, date in new_videos:
            print(f"  Processing: {title}")
            transcript = get_transcript(url)
            review = review_video(title, url, transcript)
            append_to_inbox(title, url, date, label, review)
            save_seen(url)
            total_new += 1
            results.append(f"  - {title}")
            time.sleep(2.5)

    print(f"\n=== Daily YouTube Feed Scan Complete ===")
    print(f"Channels checked: {len(channels)}")
    print(f"New videos found and reviewed: {total_new}")
    if results:
        print("New entries added to inbox:")
        for r in results:
            print(r)
    else:
        print("No new videos today.")
    print(f"Inbox: {INBOX_FILE}")


if __name__ == "__main__":
    main()
