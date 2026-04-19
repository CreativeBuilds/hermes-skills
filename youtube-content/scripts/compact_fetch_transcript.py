#!/usr/bin/env python3
"""
Compact YouTube transcript fetcher. Single file, robust, auto-installs dependency.
Designed for fast research ingestion into Zephyr wiki / Karpathy harness.
"""
import argparse
import re
import subprocess
import sys

def extract_video_id(url_or_id):
    url_or_id = url_or_id.strip()
    match = re.search(r'(?:v=|youtu\.be/|shorts/|embed/|live/)([a-zA-Z0-9_-]{11})', url_or_id)
    return match.group(1) if match else url_or_id

def format_ts(seconds):
    total = int(seconds)
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"

def fetch(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Installing youtube-transcript-api...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "youtube-transcript-api", "--break-system-packages"])
        from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=["en"])
    return transcript.snippets

def main():
    parser = argparse.ArgumentParser(description="Compact YouTube transcript fetcher")
    parser.add_argument("url", help="YouTube URL or video ID")
    parser.add_argument("--no-timestamps", action="store_true", help="Output plain text only")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    try:
        snippets = fetch(video_id)
        for seg in snippets:
            if not args.no_timestamps:
                ts = format_ts(getattr(seg, "start", 0))
                text = getattr(seg, "text", str(seg)).replace("\n", " ")
                print(f"{ts} | {text}")
            else:
                print(getattr(seg, "text", str(seg)).replace("\n", " "))
        print(f"\n--- End of transcript for https://www.youtube.com/watch?v={video_id} ---")
        print(f"Total segments: {len(snippets)} (~{len(snippets)*3//60} minutes)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
