#!/usr/bin/env python3
"""
YouTube Channel Analytics
Reads structured JSONL from the analyzer and generates reports + charts.

Usage:
  python3 youtube_channel_analytics.py /tmp/NateBJones_structured.jsonl

  # Just print topic distribution:
  python3 youtube_channel_analytics.py /tmp/NateBJones_structured.jsonl --topics

  # Export for external tools:
  python3 youtube_channel_analytics.py /tmp/NateBJones_structured.jsonl --export-csv /tmp/topics.csv

  # Generate HTML chart:
  python3 youtube_channel_analytics.py /tmp/NateBJones_structured.jsonl --html /tmp/report.html

Output:
  stdout — text report with topic distribution, framing analysis, etc.
  Optional: CSV export, HTML chart
"""

import json
import sys
import os
from collections import defaultdict, Counter
from pathlib import Path


def load_data(path):
    """Load JSONL file into list of dicts."""
    entries = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def analyze_topics(entries):
    """Aggregate topic weights across all videos."""
    topic_weights = defaultdict(float)
    topic_counts = Counter()
    topic_framings = defaultdict(list)

    for entry in entries:
        for topic in entry.get("topics", []):
            name = topic.get("name", "Unknown")
            weight = topic.get("weight", 0)
            framing = topic.get("framing", "")
            topic_weights[name] += weight
            topic_counts[name] += 1
            if framing:
                topic_framings[name].append(framing)

    # Normalize weights to percentages of total airtime
    total_weight = sum(topic_weights.values()) or 1
    topic_pcts = {k: (v / total_weight) * 100 for k, v in topic_weights.items()}

    return topic_pcts, topic_counts, topic_framings


def analyze_categories(entries):
    """Count primary categories."""
    return Counter(e.get("primary_category", "Unknown") for e in entries)


def analyze_sentiment(entries):
    """Count sentiment distribution."""
    return Counter(e.get("sentiment", "unknown") for e in entries)


def analyze_novelty(entries):
    """Count novelty distribution."""
    return Counter(e.get("novelty", "unknown") for e in entries)


def print_bar(label, value, max_val, width=40):
    """Print a text-based bar chart line."""
    bar_len = int((value / max_val) * width) if max_val > 0 else 0
    bar = "█" * bar_len
    print(f"  {label:<35} {bar} {value:.1f}%")


def print_report(entries, topic_pcts, topic_counts, topic_framings, categories, sentiments, novelties):
    """Print full text report."""
    total = len(entries)
    errors = sum(1 for e in entries if e.get("parse_error"))

    print(f"\n{'=' * 70}")
    print(f"YOUTUBE CHANNEL ANALYSIS REPORT")
    print(f"{'=' * 70}")
    print(f"Total videos analyzed: {total}")
    print(f"Parse errors: {errors}")
    print()

    # Topic distribution (pie chart as text)
    print(f"{'─' * 70}")
    print(f"TOPIC DISTRIBUTION (% of total airtime)")
    print(f"{'─' * 70}")
    sorted_topics = sorted(topic_pcts.items(), key=lambda x: x[1], reverse=True)
    max_pct = sorted_topics[0][1] if sorted_topics else 1
    for name, pct in sorted_topics[:25]:
        count = topic_counts[name]
        print_bar(f"{name} ({count}x)", pct, max_pct)
    print()

    # Primary categories
    print(f"{'─' * 70}")
    print(f"PRIMARY CATEGORY BREAKDOWN")
    print(f"{'─' * 70}")
    max_cat = categories.most_common(1)[0][1] if categories else 1
    for cat, count in categories.most_common():
        pct = (count / total) * 100
        bar_len = int((count / max_cat) * 40)
        bar = "█" * bar_len
        print(f"  {cat:<35} {bar} {count} ({pct:.0f}%)")
    print()

    # Sentiment
    print(f"{'─' * 70}")
    print(f"SENTIMENT DISTRIBUTION")
    print(f"{'─' * 70}")
    for sent, count in sentiments.most_common():
        pct = (count / total) * 100
        print(f"  {sent:<20} {count:>4} ({pct:.0f}%)")
    print()

    # Novelty
    print(f"{'─' * 70}")
    print(f"NOVELTY DISTRIBUTION")
    print(f"{'─' * 70}")
    for nov, count in novelties.most_common():
        pct = (count / total) * 100
        print(f"  {nov:<20} {count:>4} ({pct:.0f}%)")
    print()

    # Top framing patterns per major topic
    print(f"{'─' * 70}")
    print(f"FRAMING ANALYSIS (top 10 topics — how each was typically positioned)")
    print(f"{'─' * 70}")
    for name, pct in sorted_topics[:10]:
        framings = topic_framings.get(name, [])
        print(f"\n  {name} ({pct:.1f}% of airtime, {topic_counts[name]} videos):")
        # Show up to 3 representative framings
        seen = set()
        shown = 0
        for f in framings:
            short = f[:120]
            if short not in seen:
                print(f"    - {short}")
                seen.add(short)
                shown += 1
                if shown >= 3:
                    break

    print(f"\n{'=' * 70}")
    print(f"END OF REPORT")
    print(f"{'=' * 70}")


def export_csv(entries, topic_pcts, topic_counts, output_path):
    """Export topic data as CSV for external charting tools."""
    import csv
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["topic", "weight_pct", "video_count"])
        for name, pct in sorted(topic_pcts.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([name, f"{pct:.2f}", topic_counts[name]])
    print(f"CSV exported to: {output_path}")


def export_html(entries, topic_pcts, topic_counts, categories, output_path):
    """Generate a simple HTML page with Chart.js pie chart."""
    sorted_topics = sorted(topic_pcts.items(), key=lambda x: x[1], reverse=True)[:20]
    labels = [t[0] for t in sorted_topics]
    values = [round(t[1], 1) for t in sorted_topics]

    cat_labels = [c[0] for c in categories.most_common()]
    cat_values = [c[1] for c in categories.most_common()]

    html = f"""<!DOCTYPE html>
<html><head><title>YouTube Channel Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:sans-serif;max-width:1200px;margin:0 auto;padding:20px}}
.chart-container{{display:inline-block;width:48%;vertical-align:top}}</style>
</head><body>
<h1>YouTube Channel Analysis</h1>
<p>{len(entries)} videos analyzed</p>
<div class="chart-container">
<h2>Topic Distribution (% of airtime)</h2>
<canvas id="topicChart"></canvas>
</div>
<div class="chart-container">
<h2>Primary Categories</h2>
<canvas id="catChart"></canvas>
</div>
<script>
new Chart(document.getElementById('topicChart'), {{
  type: 'pie',
  data: {{
    labels: {json.dumps(labels)},
    datasets: [{{data: {json.dumps(values)}, backgroundColor: {json.dumps([f'hsl({i*360//len(labels)}, 70%, 60%)' for i in range(len(labels))])}}}]
  }},
  options: {{plugins: {{legend: {{position: 'right', labels: {{font: {{size: 10}}}}}}}}}}
}});
new Chart(document.getElementById('catChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(cat_labels)},
    datasets: [{{label: 'Videos', data: {json.dumps(cat_values)}, backgroundColor: 'rgba(54, 162, 235, 0.7)'}}]
  }},
  options: {{indexAxis: 'y', plugins: {{legend: {{display: false}}}}}}
}});
</script>
</body></html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML report: {output_path}")
    print(f"Open in browser: open {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 youtube_channel_analytics.py <structured.jsonl> [--topics] [--export-csv path] [--html path]")
        sys.exit(1)

    data_path = sys.argv[1]
    if not os.path.exists(data_path):
        print(f"File not found: {data_path}")
        sys.exit(1)

    entries = load_data(data_path)
    if not entries:
        print("No data found in file.")
        sys.exit(1)

    topic_pcts, topic_counts, topic_framings = analyze_topics(entries)
    categories = analyze_categories(entries)
    sentiments = analyze_sentiment(entries)
    novelties = analyze_novelty(entries)

    # Handle flags
    if "--export-csv" in sys.argv:
        idx = sys.argv.index("--export-csv")
        csv_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "/tmp/topics.csv"
        export_csv(entries, topic_pcts, topic_counts, csv_path)

    if "--html" in sys.argv:
        idx = sys.argv.index("--html")
        html_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "/tmp/channel_report.html"
        export_html(entries, topic_pcts, topic_counts, categories, html_path)

    # Always print text report unless --quiet
    if "--quiet" not in sys.argv:
        print_report(entries, topic_pcts, topic_counts, topic_framings, categories, sentiments, novelties)


if __name__ == "__main__":
    main()
