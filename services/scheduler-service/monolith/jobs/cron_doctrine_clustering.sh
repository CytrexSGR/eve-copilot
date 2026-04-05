#!/bin/bash
# EVE Co-Pilot Doctrine Clustering Cronjob
# Runs daily at 06:00 UTC to cluster fleet snapshots into doctrines
# and derive market items of interest
#
# Crontab entry:
# 0 6 * * * /home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh
#
# Manual execution:
# /home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"

# Activate virtualenv if exists
if [ -f "/home/cytrex/eve_copilot/venv/bin/activate" ]; then
    source /home/cytrex/eve_copilot/venv/bin/activate
fi

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/doctrine_clustering.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run doctrine clustering job
python3 /home/cytrex/eve_copilot/jobs/doctrine_clustering.py >> $LOG_FILE 2>&1
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Doctrine clustering job failed with exit code $exit_code" >> $LOG_FILE
fi

exit $exit_code
