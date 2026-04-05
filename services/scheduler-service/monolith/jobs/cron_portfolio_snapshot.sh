#!/bin/bash
# jobs/cron_portfolio_snapshot.sh
cd /home/cytrex/eve_copilot
/usr/bin/python3 jobs/portfolio_snapshotter.py >> logs/portfolio_snapshot.log 2>&1
