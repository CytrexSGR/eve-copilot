#!/bin/bash
# Daily Everef Killmail Import
# Cron: 0 6 * * * /home/cytrex/eve_copilot/jobs/cron_everef_importer.sh
# Runs at 06:00 UTC daily

cd /home/cytrex/eve_copilot

# Import yesterday's kills (and day before as safety)
python3 jobs/everef_killmail_importer.py --days 2 >> logs/everef_importer.log 2>&1
