#!/bin/bash
# Skill Snapshot Cron Job
# Creates daily skill snapshots for progress tracking
# Schedule: 0 6 * * * (daily at 6 AM)

LOG_FILE="/home/cytrex/eve_copilot/logs/skill_snapshot.log"
API_BASE="${API_GATEWAY_URL:-http://api-gateway:8000}/api/skills"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting skill snapshot job" >> "$LOG_FILE"

# Create snapshots for all characters
RESPONSE=$(curl -s -X POST "${API_BASE}/snapshot")
STATUS=$?

if [ $STATUS -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Snapshot response: $RESPONSE" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: curl failed with status $STATUS" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Skill snapshot job completed" >> "$LOG_FILE"
