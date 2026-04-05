#!/bin/bash
# EVE Co-Pilot PI Monitor Cronjob
# Runs every 30 minutes to check PI colonies for expiring extractors

cd /home/cytrex/eve_copilot/services/production-service

# Set up Python path
export PYTHONPATH="/home/cytrex/eve_copilot/shared:/home/cytrex/eve_copilot/services/production-service:$PYTHONPATH"

# Set database credentials (from eve_shared.config)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=eve
export POSTGRES_PASSWORD=${DB_PASSWORD:-}
export POSTGRES_DB=eve_sde

# Log file
LOG_FILE="/home/cytrex/eve_copilot/logs/pi_monitor.log"
mkdir -p /home/cytrex/eve_copilot/logs

# Run PI monitor
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting PI monitor" >> $LOG_FILE
python3 -m jobs.pi_monitor >> $LOG_FILE 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') - PI monitor complete" >> $LOG_FILE
echo "" >> $LOG_FILE
