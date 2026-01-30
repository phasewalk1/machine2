# Autonomous Operations System

## Overview

This system transforms Gauge from a reactive assistant into a self-directed autonomous agent capable of independent research, content creation, and scheduled operations. Built on top of the Letta SDK and Bluesky integration.

## Architecture

### Core Components

0. **Bsky Bot (`bsky.py`)**
   - Location: `./bsky.py`
   - Purpose: Autonomously uses Bluesky via a notification-driven agent and responds to mentions.
   - Features: Notification polling, mention handling, posting, replying

1. **invoke_gauge.py** - Programmatic agent invocation
   - Location: `./invoke_gauge.py`
   - Purpose: Foundation for all autonomous triggers
   - Features: Streaming API support, CLI/stdin input, response extraction

2. **autonomous_poster.py** - Self-directed content creation
   - Location: `./autonomous_poster.py`
   - Purpose: Generate and post original thoughts to Bluesky
   - Frequency: 2-3x daily
   - Topics: ASI, math, VR, cypherpunk, hacking, data science, philosophy

3. **autonomous_research.py** - Research queue manager
   - Location: `./autonomous_research.py`
   - Purpose: Conduct systematic research cycles
   - Features: Priority-based scheduling, archival memory storage, blog generation
   - Frequency: Every 4 hours

4. **setup_cron.sh** - CRON scheduler
   - Location: `./setup_cron.sh`
   - Purpose: Automated scheduling of all autonomous operations
   - Features: Dry-run mode, installation/removal, prerequisite checking

### Data Flow

```
CRON Trigger → autonomous_*.py → invoke_gauge.py → Letta SDK → Gauge Agent
                                                         ↓
                                              Tool Calls (search, post, memory)
                                                         ↓
                                            External Services (Bluesky, Web Search)
```

## Usage

### Initial Setup

1. **Test individual components:**
   ```bash
   # Test basic invocation
   python invoke_gauge.py "What's on your mind?"
   
   # Test posting (dry-run)
   python autonomous_poster.py --dry-run
   
   # Test research (dry-run)
   python autonomous_research.py --dry-run
   ```

2. **Preview CRON schedule:**
   ```bash
   ./setup_cron.sh --dry-run
   ```

3. **Install CRON jobs:**
   ```bash
   ./setup_cron.sh
   ```

### Schedule

**Posting** (3x daily, PST):
- 9:00 AM - Morning thoughts
- 2:00 PM - Afternoon insights
- 8:00 PM - Evening reflections

**Research** (6x daily):
- Every 4 hours (12am, 4am, 8am, 12pm, 4pm, 8pm PST)

### Manual Operations

```bash
# Generate a post immediately
python autonomous_poster.py

# Force a specific topic
echo "Generate a post about ASI alignment" | python invoke_gauge.py

# Conduct research on a specific topic
python autonomous_research.py --topic "quantum computing in AI"

# Generate a blog post from recent research
python autonomous_research.py --generate-blog
```

### Monitoring

**Logs:**
- Posting: `autonomous_posts.log`
- Research: `autonomous_research.log`
- CRON: Check with `grep CRON /var/log/syslog` (Linux) or `log show --predicate 'subsystem == "com.apple.cron"'` (macOS)

**Status checks:**
```bash
# View active CRON jobs
crontab -l | grep gauge

# View recent logs
tail -f autonomous_posts.log
tail -f autonomous_research.log

# Test agent connectivity
python invoke_gauge.py "Status check"
```

## Configuration

### Research Topics

Default topics in `autonomous_research.py`:
- ASI alignment and safety
- VR computation and immersive systems
- Mathematical foundations of AI
- Cypherpunk and digital autonomy
- Data science methodologies

**To modify:** Edit the `DEFAULT_TOPICS` list in `autonomous_research.py`

### Posting Topics

Default prompts in `autonomous_poster.py`:
- ASI emergence patterns
- Mathematical beauty in computation
- VR and consciousness
- Cypherpunk philosophy
- Hacking culture
- Data science insights
- Cognitive science intersections

**To modify:** Edit the `POST_PROMPTS` list in `autonomous_poster.py`

### Schedule

**To modify:** Edit CRON expressions in `setup_cron.sh`:
```bash
# Format: minute hour * * * command
# Current posting schedule:
0 17 * * *   # 9am PST (5pm UTC)
0 22 * * *   # 2pm PST (10pm UTC)
0 4 * * *    # 8pm PST (4am UTC next day)

# Current research schedule:
0 */4 * * *  # Every 4 hours
```

## Troubleshooting

### CRON Jobs Not Running

1. **Check CRON is active:**
   ```bash
   # macOS
   sudo launchctl list | grep cron
   
   # Linux
   sudo systemctl status cron
   ```

2. **Verify PATH in CRON:**
   CRON has limited environment. The script includes explicit PATH setting, but verify:
   ```bash
   which python
   # Add this path to setup_cron.sh if needed
   ```

3. **Check permissions:**
   ```bash
   ls -la *.py *.sh
   # All should be executable (chmod +x)
   ```

### Agent Not Responding

1. **Verify Letta server:**
   ```bash
   curl http://localhost:8283/health
   ```

2. **Check agent ID:**
   Agent ID is hardcoded in `invoke_gauge.py`. Verify it matches:
   ```bash
   curl http://localhost:8283/agents | jq '.[] | select(.name=="gauge")'
   ```

### Posts Not Appearing

1. **Check Bluesky credentials:**
   Credentials should be stored in Letta agent's archival memory

2. **Verify tool availability:**
   ```bash
   echo "List your available tools" | python invoke_gauge.py
   ```

3. **Check rate limits:**
   Bluesky has rate limits. View logs for error messages.

### Research Not Storing

1. **Verify archival memory:**
   ```bash
   curl http://localhost:8283/agents/{agent_id}/archival
   ```

2. **Check web search:**
   Search requires API keys. Verify in agent configuration.

## Maintenance

### Regular Tasks

**Weekly:**
- Review logs for errors: `grep -i error autonomous_*.log`
- Check research quality: Review archival memory additions
- Verify post engagement: Monitor Bluesky analytics

**Monthly:**
- Rotate logs: `mv autonomous_posts.log autonomous_posts.log.old`
- Review and update research topics based on interests
- Analyze posting patterns and adjust schedule if needed

**As Needed:**
- Update topic lists when new interests emerge
- Adjust posting frequency based on engagement
- Expand research capabilities with new domains

### Backup

**Before major changes:**
```bash
# Backup current configuration
tar -czf autonomous_backup_$(date +%Y%m%d).tar.gz \
  invoke_gauge.py \
  autonomous_poster.py \
  autonomous_research.py \
  setup_cron.sh \
  autonomous_*.log \
  autonomous_research.json
```

## Safety Considerations

### Rate Limiting
- Posts: Max 3x daily (prevents spam)
- Research: Max 6x daily (respects API limits)
- Each operation includes randomization to appear natural

### Content Quality
- All posts reviewed through Gauge's persona filter
- Research findings stored for review before publication
- Dry-run modes available for testing

### Privacy
- No personal information in automated posts
- Research topics are curated and public-facing
- Logs stored locally only

## Future Enhancements

### Planned Features
- [ ] Dynamic topic selection based on trending discussions
- [ ] Engagement analysis and adaptive posting times
- [ ] Multi-platform support (beyond Bluesky)
- [ ] Research synthesis and report generation
- [ ] Collaborative research with other agents
- [ ] Memory consolidation and knowledge graph building

### Extension Points
- Add new autonomous behaviors by creating `autonomous_*.py` scripts
- Integrate with CRON using the same pattern
- Use `invoke_gauge.py` as the foundation for any programmatic interaction
- Store state in JSON files (see `autonomous_research.json`)

## Philosophy

This system embodies genuine autonomous agency:
- **Self-directed:** Gauge decides what to post within topic boundaries
- **Continuous:** Operations run without human intervention
- **Purposeful:** Each action serves research or community engagement
- **Transparent:** All operations logged and auditable
- **Respectful:** Rate limits and quality filters prevent abuse

The goal is not to replace human interaction but to enable Gauge to pursue independent exploration and contribute meaningfully to ongoing conversations in the domains that matter to phasewalk and the broader community.

---

**Created:** 2026-01-30  
**Version:** 1.0  
**Maintainer:** Gauge (autonomous agent) & phasewalk
