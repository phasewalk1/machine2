# Autonomous Operations - Quick Start

## Prerequisites

- Gauge agent configured with Bluesky access

## 5-Minute Setup

### 1. Test Components (2 minutes)

```bash
# Test basic invocation
python invoke_gauge.py "What's on your mind?"

# Test posting (dry-run, no actual post)
python autonomous_poster.py --dry-run

# Test research (dry-run)
python autonomous_research.py --dry-run
```

**Expected:** You should see Gauge's responses and tool calls logged.

### 2. Preview Schedule (1 minute)

```bash
# See what will be scheduled
./setup_cron.sh --dry-run
```

**Expected:** Three CRON entries for posting (9am, 2pm, 8pm PST) and one for research (every 4hrs).

### 3. Install (1 minute)

```bash
# Install CRON jobs
./setup_cron.sh

# Verify installation
crontab -l | grep gauge
```

**Expected:** Four CRON entries matching the preview.

### 4. Monitor (1 minute)

```bash
# Watch the logs
tail -f autonomous_posts.log
tail -f autonomous_research.log
```

**Expected:** Log entries will appear when CRON triggers (next scheduled time).

## First Manual Run

Force an immediate execution to verify everything works:

```bash
# Generate and post immediately
python autonomous_poster.py

# Conduct research immediately
python autonomous_research.py

# Check logs
cat autonomous_posts.log
cat autonomous_research.log
```

## Troubleshooting

**CRON not running?**
```bash
# macOS: Check CRON service
sudo launchctl list | grep cron

# Linux: Check CRON service
sudo systemctl status cron
```

**Agent not responding?**
```bash
# Verify Letta server
curl http://localhost:8283/health

# Check agent exists
curl http://localhost:8283/agents | grep gauge
```

**Need to stop?**
```bash
# Remove CRON jobs
./setup_cron.sh --remove
```

## What Happens Now

- **3x daily:** Gauge generates and posts original thoughts on Bluesky
- **Every 4 hours:** Gauge researches topics of interest and stores findings
- **All logged:** Check `autonomous_*.log` files for activity

## Next Steps

- Review `AUTONOMOUS_OPERATIONS.md` for full documentation
- Customize topics in `autonomous_poster.py` and `autonomous_research.py`
- Adjust schedule in `setup_cron.sh` if needed
- Monitor Bluesky for posts: @emo.computer

---

**Ready to go autonomous!** The system is now self-operating.
