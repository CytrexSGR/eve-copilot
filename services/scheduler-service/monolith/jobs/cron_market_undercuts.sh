#!/bin/bash
# jobs/cron_market_undercuts.sh
cd /home/cytrex/eve_copilot
/usr/bin/python3 jobs/market_undercut_checker.py >> logs/market_undercuts.log 2>&1
