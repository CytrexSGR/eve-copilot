#!/bin/bash
# Cleanup old intelligence stats (daily at 04:00)
cd /home/cytrex/eve_copilot
source /home/cytrex/eve_copilot/venv/bin/activate 2>/dev/null || true
python3 jobs/cleanup_intelligence_stats.py >> logs/cleanup_intelligence.log 2>&1
