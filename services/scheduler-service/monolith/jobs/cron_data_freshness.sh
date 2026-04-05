#!/bin/bash
# Data Freshness Monitor - Runs every 15 minutes
# Crontab: */15 * * * * /home/cytrex/eve_copilot/jobs/cron_data_freshness.sh

cd /home/cytrex/eve_copilot
python3 jobs/monitor_data_freshness.py
