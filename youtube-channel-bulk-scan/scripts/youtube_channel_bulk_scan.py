#!/usr/bin/env python3
"""
YouTube Channel Bulk Scan
Fetches all video links from a channel, extracts transcripts,
generates high-signal reviews, writes to a single output file.

Usage:
  python3 youtube_channel_bulk_scan.py https://www.youtube.com/@ChannelHandle

Watch live:
  tail -f /tmp/<channel>_reviews.txt
"""

import re
import os
import sys
import time
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
TRANSCRIPT_SCRIPT = os.path.expanduser(
    "~/.hermes/skills/media/compact-youtube-transcript/scripts/fetch_transcript.py"
)
BATCH_SIZE = 3
SLEEP_BETWEEN_VIDEOS = 2.5
SLEEP_BETWEEN_BATCHES = 3.0
TRANSCRIPT_CHAR_LIMIT = 5500


def run_cmd(cmd, timeout_sec=30):
    """Run a shell command, return stdout or error string."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout_sec
        )
        out = result.stdout.strip()
        if not out:
            out = result.stderr.strip()
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


def get_transcript(url):
    """Fetch transcript for a single video URL."""
    cmd = f'python3 "{TRANSCRIPT_SCRIPT}" "{url}" --no-timestamps'
    return run_cmd(cmd, timeout_sec=25)


def review_transcript(title, url, transcript):
    """Generate a high-signal bullet-point review using hermes chat."""
    prompt = f"""Title: {title}
URL: {url}

Transcript excerpt:
{transcript[:TRANSCRIPT_CHAR_LIMIT]}

Extract the 6-10 highest-signal insights from this video.
Identify the main topics discussed, key arguments or claims made, and any notable insights or takeaways.
Output ONLY as bullet points. One concise sentence per bullet. No introductory or concluding text."""

    # Write prompt to temp file, pass via $(cat ...) to hermes -q
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir="/tmp"
    ) as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    cmd = (
        f'{HERMES_BIN} chat -q "$(cat {tmp_path})" '
        f"-Q --max-turns 1 -t ''"
    )
    review = run_cmd(cmd, timeout_sec=50)

    # Clean up temp file
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Strip session_id line if present
    lines = review.split("\n")
    cleaned = [l for l in lines if not l.startswith("session_id:")]
    return "\n".join(cleaned).strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 youtube_channel_bulk_scan.py <channel_url>")
        print("Example: python3 youtube_channel_bulk_scan.py https://www.youtube.com/@NateBJones")
        sys.exit(1)

    channel_url = sys.argv[1].rstrip("/")
    # Derive a short channel name for filenames
    channel_name = re.sub(r"[^a-zA-Z0-9]", "_", channel_url.split("@")[-1] if "@" in channel_url else "channel")

    videos_url = channel_url + "/videos"
    list_path = f"/tmp/{channel_name}_videos.txt"
    output_path = f"/tmp/{channel_name}_reviews.txt"
    progress_path = f"/tmp/{channel_name}_progress.json"

    print("=" * 60)
    print(f"YouTube Channel Bulk Scan")
    print(f"Channel:  {channel_url}")
    print(f"Output:   {output_path}")
    print(f"Progress: {progress_path}")
    print("=" * 60)

    # Check for resume
    start_idx = 0
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r") as f:
                prog = json.load(f)
            start_idx = prog.get("last_processed", 0)
            if start_idx > 0:
                print(f"Resuming from video {start_idx + 1}")
        except (json.JSONDecodeError, KeyError):
            start_idx = 0

    if start_idx == 0:
        # Fresh run — clear output
        if os.path.exists(output_path):
            os.remove(output_path)
        if os.path.exists(progress_path):
            os.remove(progress_path)

    # Step 1: Get all video links
    if not os.path.exists(list_path) or start_idx == 0:
        print("\nFetching video list with yt-dlp...")
        fetch_cmd = (
            f'yt-dlp --flat-playlist '
            f'--print "%(url)s|%(title)s|%(upload_date>%Y-%m-%d)s" '
            f'"{videos_url}"'
        )
        result = run_cmd(fetch_cmd, timeout_sec=120)
        with open(list_path, "w") as f:
            f.write(result)
        print("Video list saved.")

    # Parse video list
    with open(list_path, "r") as f:
        raw_lines = f.readlines()

    videos = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        match = re.search(r"(https://www\.youtube\.com/watch\?v=[\w-]+)\|(.+?)\|", line)
        if match:
            videos.append((match.group(1), match.group(2).strip()))

    total = len(videos)
    print(f"\nTotal videos found: {total}")
    print(f"Starting from video: {start_idx + 1}")
    print(f"\nWatch live output with:")
    print(f"  tail -f {output_path}\n")

    # Step 2: Process in batches
    for batch_start in range(start_idx, total, BATCH_SIZE):
        batch = videos[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        print(f"--- Batch {batch_num}: videos {batch_start + 1}-{batch_start + len(batch)} ---")

        for j, (url, title) in enumerate(batch):
            video_num = batch_start + j + 1
            print(f"  [{video_num}/{total}] {title}")

            transcript = get_transcript(url)
            review = review_transcript(title, url, transcript)

            entry = (
                f"VIDEO {video_num}: {title}\n"
                f"URL: {url}\n"
                f"TOP SIGNALS:\n"
                f"{review if review else '(no review generated)'}\n\n"
                f"{'─' * 90}\n\n"
            )

            with open(output_path, "a") as f:
                f.write(entry)

            time.sleep(SLEEP_BETWEEN_VIDEOS)

        # Save progress after each batch
        progress = {
            "last_processed": batch_start + len(batch),
            "total": total,
            "channel": channel_url,
            "last_updated": datetime.now().isoformat(),
        }
        with open(progress_path, "w") as f:
            json.dump(progress, f, indent=2)

        done = batch_start + len(batch)
        pct = int(100 * done / total)
        print(f"  Progress: {done}/{total} ({pct}%)\n")
        time.sleep(SLEEP_BETWEEN_BATCHES)

    print("=" * 60)
    print("BULK SCAN COMPLETE")
    print(f"All {total} videos processed.")
    print(f"Reviews saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
