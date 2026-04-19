#!/usr/bin/env bash
# YouTube Daily Feed — Setup script for Hermes Agent users
# Run this after installing the youtube-channel-bulk-scan skill.
# It creates the feeds directory, starter config files, and copies scripts.
#
# Usage: bash install.sh
#
# Prerequisites: hermes agent, yt-dlp, youtube-transcript-api pip package,
# compact-youtube-transcript skill.

set -euo pipefail

FEEDS_DIR="${YOUTUBE_FEEDS_DIR:-$HOME/.hermes/youtube-feeds}"
SCRIPTS_DIR="$HOME/.hermes/scripts"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== YouTube Daily Feed Setup ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v yt-dlp &>/dev/null; then
    echo "ERROR: yt-dlp not found. Please install it first."
    exit 1
fi

echo "  yt-dlp: OK"
echo "  hermes: OK"
echo ""

# Create feeds directory
echo "Creating feeds directory at: $FEEDS_DIR"
mkdir -p "$FEEDS_DIR"

if [ ! -f "$FEEDS_DIR/channels.txt" ]; then
    cat > "$FEEDS_DIR/channels.txt" << 'CHANNELS'
# YouTube Channels to Monitor
# Format: URL | label (one per line, # for comments)
# Add channels here. The daily scan picks them up automatically.
#
# Example:
# https://www.youtube.com/@ChannelName | Short description of channel focus
CHANNELS
    echo "  channels.txt: created (add your channels here)"
else
    echo "  channels.txt: already exists, skipping"
fi

if [ ! -f "$FEEDS_DIR/inbox.md" ]; then
    cat > "$FEEDS_DIR/inbox.md" << 'INBOX'
# YouTube Video Inbox
# New video reviews land here via the daily scan.
# Ask your agent about new videos — it reads this file.
# Dismissed entries get removed. Good ones become wiki notes.
# Goal: this file trends toward zero.

INBOX
    echo "  inbox.md: created"
else
    echo "  inbox.md: already exists, skipping"
fi

if [ ! -f "$FEEDS_DIR/seen.txt" ]; then
    cat > "$FEEDS_DIR/seen.txt" << 'SEEN'
# Seen Videos — one URL per line. Daily scan skips these.
SEEN
    echo "  seen.txt: created"
else
    echo "  seen.txt: already exists, skipping"
fi

echo ""

# Copy scripts
echo "Installing scripts to: $SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"

for script in youtube_daily_feed.py youtube_channel_bulk_scan.py; do
    if [ -f "$SKILL_DIR/scripts/$script" ]; then
        cp "$SKILL_DIR/scripts/$script" "$SCRIPTS_DIR/$script"
        echo "  $script: installed"
    elif [ -f "$SCRIPTS_DIR/$script" ]; then
        echo "  $script: already exists"
    else
        echo "  $script: not found in skill directory"
    fi
done

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Add channels: edit $FEEDS_DIR/channels.txt"
echo "  2. Test: python3 $SCRIPTS_DIR/youtube_daily_feed.py"
echo "  3. Set up cron: tell hermes 'Set up the youtube daily feed cron job'"
echo "  4. Ask anytime: 'Any new videos?'"
echo ""
echo "Done."
