#!/bin/bash
# EVE Co-Pilot Character Sync Cronjob
# Runs every 30 minutes and syncs all character data
# Syncs: wallet, skills, assets, orders, jobs, blueprints

cd /home/cytrex/eve_copilot

export PYTHONPATH="/home/cytrex/eve_copilot:$PYTHONPATH"

# Activate virtualenv if exists
if [ -f "/home/cytrex/eve_copilot/venv/bin/activate" ]; then
    source /home/cytrex/eve_copilot/venv/bin/activate
fi

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/character_sync.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run character sync
python3 /home/cytrex/eve_copilot/jobs/character_sync.py >> $LOG_FILE 2>&1
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Character sync failed with exit code $exit_code" >> $LOG_FILE
fi

exit $exit_code
