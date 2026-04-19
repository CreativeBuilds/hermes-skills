# hermes-skills

Shareable skill collection for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Install a skill

```bash
hermes skills install CreativeBuilds/hermes-skills/<skill-name>
```

## Skills

### youtube-channel-bulk-scan

Bulk scan any YouTube channel, monitor feeds daily, and generate structured analytics.

- Prose reviews of all videos
- Structured JSONL output (topics, weights, framing, sentiment, novelty)
- Topic distribution charts (HTML + CSV)
- Daily cron monitoring with inbox staging

**Install:**
```bash
hermes skills install CreativeBuilds/hermes-skills/youtube-channel-bulk-scan
bash ~/.hermes/skills/media/youtube-channel-bulk-scan/scripts/install.sh
```

Works with any YouTube channel — not domain-specific.
