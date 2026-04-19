#!/usr/bin/env python3
"""
YouTube Channel Structured Analyzer
Processes videos and outputs structured JSONL data for analytics.
Each video produces a JSON object with topics, weights, framing, claims, etc.

Can be used standalone or alongside the daily feed system.

Usage:
  # Analyze a single channel (all videos):
  python3 youtube_channel_analyzer.py "https://www.youtube.com/@NateBJones"

  # Resume from where it left off:
  python3 youtube_channel_analyzer.py "https://www.youtube.com/@NateBJones" --resume

  # Re-analyze from existing video list:
  python3 youtube_channel_analyzer.py --from-list /tmp/NateBJones_videos.txt

Output:
  /tmp/<channel>_structured.jsonl  — one JSON object per line per video
  /tmp/<channel>_analysis_progress.json — resumable progress

The JSONL file is the primary data source for analytics, charts, and queries.
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

HOME = Path.home()
HERMES_BIN = HOME / ".local" / "bin" / "hermes"
TRANSCRIPT_SCRIPT = HOME / ".hermes" / "skills" / "media" / "compact-youtube-transcript" / "scripts" / "fetch_transcript.py"
BATCH_SIZE = 3
SLEEP_BETWEEN = 2.5
SLEEP_BETWEEN_BATCHES = 3.0

STRUCTURED_PROMPT_TEMPLATE = """You are a video content analyst. Given a YouTube video title and transcript, output ONLY valid JSON (no other text) with this exact structure:

{{
  "title": "exact video title",
  "topics": [
    {{"name": "topic name", "weight": 0.0, "framing": "one sentence describing HOW this topic was framed/positioned"}}
  ],
  "primary_category": "the single best-fitting category for this video (e.g. Technology, Business, Science, Education, Entertainment, Politics, Health, Finance, Culture, Philosophy, Tutorial, News, Commentary, Interview, etc.)",
  "key_claims": ["concise factual claim 1", "concise factual claim 2"],
  "sentiment": "one of: optimistic, cautionary, neutral, alarming, analytical",
  "novelty": "one of: high, medium, low"
}}

Rules:
- topics.weight must sum to 1.0 across all topics (represents time/focus allocation)
- topics should be 3-7 items, ordered by weight descending
- framing captures the ANGLE, not just the topic
- key_claims are 3-6 specific, falsifiable statements made in the video
- novelty = how original the ideas are vs typical AI commentary
- Output ONLY the JSON. No markdown, no explanation, no code fences.

Title: {title}
URL: {url}

Transcript:
{transcript}"""


def run_cmd(cmd, timeout_sec=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout_sec)
        return result.stdout.strip() or result.stderr.strip() or ""
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


def get_transcript(url):
    cmd = f'python3 "{TRANSCRIPT_SCRIPT}" "{url}" --no-timestamps'
    return run_cmd(cmd, timeout_sec=25)


def analyze_video(title, url, transcript):
    """Generate structured JSON analysis for a single video."""
    prompt = STRUCTURED_PROMPT_TEMPLATE.format(
        title=title,
        url=url,
        transcript=transcript[:5500]
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir="/tmp") as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    cmd = f"""{HERMES_BIN} chat -q "$(cat {tmp_path})" -Q --max-turns 1 -t ''"""
    raw = run_cmd(cmd, timeout_sec=50)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Clean output: strip session_id and warning lines, find JSON
    lines = raw.split("\n")
    cleaned = [l for l in lines if not l.startswith("session_id:") and not l.startswith("\u26a0\ufe0f")]
    text = "\n".join(cleaned).strip()

    # Try to extract JSON from the response
    try:
        # Find JSON boundaries
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        return data
    except (ValueError, json.JSONDecodeError):
        return {
            "title": title,
            "topics": [],
            "primary_category": "Unknown",
            "key_claims": [],
            "sentiment": "unknown",
            "novelty": "unknown",
            "parse_error": True,
            "raw_response": text[:500]
        }


def main():
    # Parse args
    resume = "--resume" in sys.argv
    from_list = None
    channel_url = None

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--from-list" and i + 1 < len(sys.argv):
            from_list = sys.argv[i + 1]
        elif arg.startswith("http"):
            channel_url = arg.rstrip("/")
        elif arg == "--resume":
            pass

    if not channel_url and not from_list:
        print("Usage: python3 youtube_channel_analyzer.py <channel_url> [--resume]")
        print("       python3 youtube_channel_analyzer.py --from-list <video_list.txt>")
        sys.exit(1)

    # Derive channel name
    if channel_url:
        channel_name = re.sub(r"[^a-zA-Z0-9]", "_", channel_url.split("@")[-1] if "@" in channel_url else "channel")
    else:
        channel_name = Path(from_list).stem

    output_path = f"/tmp/{channel_name}_structured.jsonl"
    progress_path = f"/tmp/{channel_name}_analysis_progress.json"
    list_path = f"/tmp/{channel_name}_videos.txt"

    print("=" * 60)
    print("YouTube Channel Structured Analyzer")
    print(f"Output:   {output_path}")
    print(f"Progress: {progress_path}")
    print("=" * 60)

    # Load or fetch video list
    if from_list:
        list_path = from_list

    if channel_url and (not os.path.exists(list_path) or not resume):
        print(f"\nFetching video list for {channel_url}...")
        videos_url = channel_url + "/videos"
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
        match = re.search(r"(https://www\.youtube\.com/watch\?v=[\w-]+)\|(.+?)\|(.+)", line)
        if match:
            videos.append((match.group(1), match.group(2).strip(), match.group(3).strip()))
        else:
            # Try simpler format: URL|Title
            match2 = re.search(r"(https://www\.youtube\.com/watch\?v=[\w-]+)\|(.+)", line)
            if match2:
                videos.append((match2.group(1), match2.group(2).strip(), "NA"))

    total = len(videos)
    print(f"Total videos: {total}")

    # Resume logic
    start_idx = 0
    if resume and os.path.exists(progress_path):
        try:
            with open(progress_path, "r") as f:
                prog = json.load(f)
                start_idx = prog.get("last_processed", 0)
                print(f"Resuming from video {start_idx + 1}")
        except (json.JSONDecodeError, KeyError):
            pass
    elif not resume:
        # Fresh run — clear output
        if os.path.exists(output_path):
            os.remove(output_path)
        if os.path.exists(progress_path):
            os.remove(progress_path)

    print(f"\nProcessing videos {start_idx + 1} to {total}...")
    print(f"Watch output: tail -f {output_path}\n")

    # Process
    for batch_start in range(start_idx, total, BATCH_SIZE):
        batch = videos[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        for j, (url, title, date) in enumerate(batch):
            video_num = batch_start + j + 1
            print(f"  [{video_num}/{total}] {title}")

            transcript = get_transcript(url)
            analysis = analyze_video(title, url, transcript)

            # Add metadata
            analysis["url"] = url
            analysis["date"] = date
            analysis["video_number"] = video_num
            analysis["analyzed_at"] = datetime.now().isoformat()

            # Append as JSONL
            with open(output_path, "a") as f:
                f.write(json.dumps(analysis) + "\n")

            time.sleep(SLEEP_BETWEEN)

        # Save progress
        progress = {
            "last_processed": batch_start + len(batch),
            "total": total,
            "last_updated": datetime.now().isoformat()
        }
        with open(progress_path, "w") as f:
            json.dump(progress, f, indent=2)

        done = batch_start + len(batch)
        pct = int(100 * done / total)
        print(f"  Progress: {done}/{total} ({pct}%)\n")
        time.sleep(SLEEP_BETWEEN_BATCHES)

    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print(f"Structured data: {output_path}")
    print(f"Total videos analyzed: {total}")
    print("")
    print("Next: python3 youtube_channel_analytics.py " + output_path)
    print("=" * 60)


if __name__ == "__main__":
    main()
