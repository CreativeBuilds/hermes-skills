---
name: youtube-channel-bulk-scan
description: >
  YouTube channel analysis toolkit — bulk scan, daily feed monitoring,
  structured analytics (JSONL), topic distribution charts, and framing analysis.
  Produces both human-readable reviews and machine-parsable structured data.
  Works with any type of YouTube channel — not domain-specific.
category: media
tags: [youtube, channel, bulk, analytics, daily-feed, structured-data]
---

# YouTube Channel Analysis Toolkit

**Trigger**: User gives a YouTube channel link and asks to "bulk scan", "analyze", "review all videos", "add to my feed", "chart topics", or asks "any new videos?"

## What's In The Box

| Script | Purpose | Output |
|--------|---------|--------|
| `youtube_channel_bulk_scan.py` | Prose reviews of all videos | `/tmp/<channel>_reviews.txt` |
| `youtube_channel_analyzer.py` | Structured JSON analysis | `/tmp/<channel>_structured.jsonl` |
| `youtube_channel_analytics.py` | Reports, charts, CSV from JSONL | Text report, HTML, CSV |
| `youtube_daily_feed.py` | Daily new-video monitoring | `~/.hermes/youtube-feeds/inbox.md` |
| `install.sh` | One-command setup for new users | Feeds dir + scripts |

## Quick Start

```bash
# Install the skill, then run setup:
bash ~/.hermes/skills/media/youtube-channel-bulk-scan/scripts/install.sh

# Add a channel:
echo 'https://www.youtube.com/@ChannelName | Description' >> ~/.hermes/youtube-feeds/channels.txt

# Full structured analysis:
python3 ~/.hermes/scripts/youtube_channel_analyzer.py "https://www.youtube.com/@ChannelName"

# Generate charts + reports:
python3 ~/.hermes/scripts/youtube_channel_analytics.py /tmp/ChannelName_structured.jsonl --html /tmp/report.html
open /tmp/report.html
```

## Structured Data Format (JSONL)

Each line in `_structured.jsonl` is a self-contained JSON object:

```json
{
  "title": "Video Title",
  "url": "https://youtube.com/watch?v=...",
  "date": "2026-04-19",
  "topics": [
    {"name": "Topic A", "weight": 0.4, "framing": "presented as an urgent problem"},
    {"name": "Topic B", "weight": 0.3, "framing": "framed as an emerging opportunity"},
    {"name": "Topic C", "weight": 0.3, "framing": "discussed as background context"}
  ],
  "primary_category": "Technology",
  "key_claims": ["Specific claim 1", "Claim 2", "Claim 3"],
  "sentiment": "analytical",
  "novelty": "high",
  "video_number": 1,
  "analyzed_at": "2026-04-19T12:30:00"
}
```

**Key fields for analytics:**
- `topics[].weight` — sums to 1.0, represents % of video focused on that topic
- `topics[].framing` — HOW the topic was positioned (angle, not just subject)
- `primary_category` — auto-detected (Technology, Business, Science, Education, etc.)
- `key_claims` — falsifiable statements for tracking or fact-checking
- `sentiment` / `novelty` — quick filters

**Extensibility:** Edit the prompt template in `youtube_channel_analyzer.py` to add custom fields (e.g. "target_audience", "mentioned_products", "data_sources_cited"). JSONL means each video is independent — merge datasets, re-analyze individuals, pipe to jq/pandas/anything.

## Analytics Capabilities

```bash
# Full text report:
python3 youtube_channel_analytics.py data.jsonl

# HTML charts (Chart.js pie + bar):
python3 youtube_channel_analytics.py data.jsonl --html /tmp/report.html

# CSV for spreadsheets:
python3 youtube_channel_analytics.py data.jsonl --export-csv /tmp/topics.csv

# Raw jq queries:
cat data.jsonl | jq -r '.primary_category' | sort | uniq -c | sort -rn
cat data.jsonl | jq -r 'select(.novelty == "high") | .title'
cat data.jsonl | jq '[.topics[] | {name, weight}] | sort_by(-.weight)'
```

## Daily Feed System

**File structure:**
```
~/.hermes/youtube-feeds/
  channels.txt   — channels to monitor (URL | label per line)
  inbox.md       — new video reviews staging (trends toward zero)
  seen.txt       — processed URLs (dedup)
```

Configurable via `YOUTUBE_FEEDS_DIR` env var if you want a different location.

**Cron:** Set up via `hermes cron create '0 8 * * *'` with the daily feed script. Checks each channel for recent videos, skips seen ones, reviews new ones.

**Inbox workflow:** Agent reads inbox.md on request. User dismisses → remove. User wants more detail → agent processes further. Goal: inbox shrinks.

## Validated Working Pattern

The only reliable subprocess call to hermes:
```
~/.local/bin/hermes chat -q "$(cat /tmp/prompt.txt)" -Q --max-turns 1 -t ''
```

## Critical Pitfalls

1. **No hermes_tools in background scripts** — use standard subprocess/os/json
2. **Shell quoting** — write prompts to temp files, use $(cat tmpfile)
3. **hermes CLI** — must be `hermes chat -q`, not `python3 -m hermes`
4. **Write to /tmp/** — avoid ~/ which triggers IDE file watchers
5. **Scripts are self-contained** — only stdlib imports

## Performance

- Prose review: ~4.5 videos/min (522 videos ≈ 2 hours)
- Structured analysis: ~3 videos/min (more complex prompt)
- Both are resumable — re-run same command to pick up where it left off

**Status**: VALIDATED April 19, 2026. Tested on 522-video channel.
