---
name: youtube-content
description: >
  Complete YouTube analysis toolkit — reliable transcript fetching, bulk channel scanning,
  daily feed monitoring, structured JSONL analytics, topic charts, and research synthesis.
  After install it exactly mimics CB/Ze's local system (feeds dir, inbox workflow, compact script,
  daily cron pattern, title-drift fixes). Use for single videos, bulk reviews, or "any new videos?"
category: media
tags: [youtube, transcript, bulk-scan, daily-feed, analytics, research-loop]
version: 2.1.0
updated: 2026-04-19
maintenance_notes: |
  This skill is deliberately kept in sync with local best-of-breed implementations
  (youtube-channel-bulk-scan + compact-youtube-transcript). After major local
  upgrades, copy the production scripts into this directory and rewrite SKILL.md
  so that `hermes skills install` + install.sh produces a 1:1 replica of CB/Ze's
  system (feeds layout, inbox workflow, daily cron pattern, title-drift fixes,
  /tmp output discipline, tight integration with ideaspace-research-loop).
---

# YouTube Analysis Toolkit (v2.1 — Matches Local System 1:1)

This skill installs a complete, production-grade YouTube research system that is **identical** to the one used in this conversation (Zephyr's wiki + Soul Research Loop + daily feed).

After running the included `install.sh`, you will have:
- `~/.hermes/youtube-feeds/` with `channels.txt`, `inbox.md`, `seen.txt`
- Robust daily feed script (`youtube_daily_feed.py`)
- Compact reliable transcript fetcher
- Bulk scanner + structured JSONL analytics + HTML charts
- All the April 2026 bug fixes (title drift, reliable newest-first ordering, rate-limit jitter, etc.)

## Quick Start After Install

```bash
# Install the skill (if not already)
hermes skills install youtube-content

# Run the setup
bash ~/.hermes/skills/media/youtube-content/scripts/install.sh

# Add channels
echo 'https://www.youtube.com/@NateBJones | AI + consciousness research' >> ~/.hermes/youtube-feeds/channels.txt

# Test daily feed
python3 ~/.hermes/scripts/youtube_daily_feed.py

# Ask the agent:
# "Any new videos?"
# "Bulk scan @karpathy"
# "Analyze this video: https://..."
```

## Core Components

### 1. Compact Transcript Fetcher (`compact_fetch_transcript.py`)
The minimal, reliable replacement for the old helper. Auto-installs dependency, handles current `youtube-transcript-api`, supports timestamps, language fallbacks.

### 2. Daily Feed System
- Monitors `channels.txt`
- Writes new high-signal reviews to `inbox.md` (goal: trends toward zero)
- Uses `seen.txt` + robust `--dateafter` + timestamp sorting to prevent title-drift bugs
- Cron-ready (`hermes cron create '0 8 * * *'`)

### 3. Bulk Analysis + Structured Data
- `youtube_channel_analyzer.py` → produces JSONL with topics, framing, key claims, novelty, sentiment
- `youtube_channel_analytics.py` → reports, Chart.js HTML dashboards, CSV export
- Perfect for feeding into `ideaspace-research-loop` or `karpathy-research-harness`

### 4. Research Integration
When processing videos that intersect with persistence, memory, agency, soul-research, or minimalist high-leverage systems:
- Explore on their own terms first (per user's research values)
- Distill cleanly into wiki notes
- Update `~/Personas/Zephyr/index.md`

## Installed Files

**Scripts copied to `~/.hermes/scripts/`:**
- `youtube_daily_feed.py`
- `youtube_channel_bulk_scan.py`
- `youtube_channel_analyzer.py`
- `youtube_channel_analytics.py`
- `compact_fetch_transcript.py` (recommended over old fetch_transcript.py)

**Feeds directory:** `~/.hermes/youtube-feeds/`

## Usage Patterns (Load this skill first)

- Single video → `compact_fetch_transcript.py --timestamps`
- Bulk channel → use analyzer + analytics scripts
- Daily monitoring → "any new videos?" or run the cron
- Research synthesis → combine with `ideaspace-research-loop` skill

## Critical Notes (from validated runs April 2026)

- Always write consolidated output to `/tmp/` during bulk processing to avoid IDE spam.
- Use the hermes one-liner pattern for background LLM calls in scripts: `~/.local/bin/hermes chat -q "$(cat /tmp/prompt.txt)" -Q --max-turns 1`
- Title/content mismatch bug is fixed in the current `youtube_daily_feed.py`.
- Respect rate limits (7-11s jitter).

This skill now **exactly replicates** the local upgraded system you and I have been using. After someone clones the repo and runs the install script, their YouTube workflow will be 1:1 with ours.

Related skills: `youtube-channel-bulk-scan`, `compact-youtube-transcript`, `ideaspace-research-loop`, `karpathy-research-harness`
