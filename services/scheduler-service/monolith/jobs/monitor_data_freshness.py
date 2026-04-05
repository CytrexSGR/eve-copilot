#!/usr/bin/env python3
"""
Data Freshness Monitor

Checks if killmail data is up-to-date and sends alerts when data becomes stale.
Run via cron every 15 minutes.

Alerts via:
- Discord webhook (if configured)
- Log file
- Exit code (for cron monitoring)
"""

import sys
import os
import requests
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from database import get_db_connection
from config import DISCORD_WEBHOOK_URL

# Thresholds
WARNING_THRESHOLD_MINUTES = 60      # Warn after 1 hour without new kills
CRITICAL_THRESHOLD_MINUTES = 180    # Critical after 3 hours
EXPECTED_KILLS_PER_HOUR = 300       # Minimum expected kills per hour (galaxy-wide)

LOG_FILE = "/home/cytrex/eve_copilot/logs/data_freshness.log"


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def send_discord_alert(message: str, level: str = "warning"):
    """Send alert to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return

    color = 0xFFFF00 if level == "warning" else 0xFF0000  # Yellow or Red

    payload = {
        "embeds": [{
            "title": f"⚠️ Data Freshness Alert" if level == "warning" else "🚨 CRITICAL: Data Stale",
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "EVE Copilot Monitor"}
        }]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        log(f"Discord webhook failed: {e}", "ERROR")


def check_data_freshness():
    """Check killmail data freshness and return status."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get latest killmail time
            cur.execute("""
                SELECT
                    MAX(killmail_time) as latest,
                    COUNT(*) as count_1h,
                    COUNT(*) FILTER (WHERE killmail_time >= NOW() - INTERVAL '24 hours') as count_24h
                FROM killmails
                WHERE killmail_time >= NOW() - INTERVAL '1 hour'
            """)
            row = cur.fetchone()

            # Get the actual latest killmail
            cur.execute("SELECT MAX(killmail_time) FROM killmails")
            latest_kill = cur.fetchone()[0]

            if not latest_kill:
                return {
                    "status": "critical",
                    "message": "No killmails in database!",
                    "latest_kill": None,
                    "age_minutes": None,
                    "kills_1h": 0
                }

            age = datetime.utcnow() - latest_kill.replace(tzinfo=None)
            age_minutes = int(age.total_seconds() / 60)
            kills_1h = row[1] if row else 0

            return {
                "status": "ok" if age_minutes < WARNING_THRESHOLD_MINUTES else
                         "warning" if age_minutes < CRITICAL_THRESHOLD_MINUTES else "critical",
                "message": f"Latest kill: {age_minutes}min ago, {kills_1h} kills/h",
                "latest_kill": latest_kill,
                "age_minutes": age_minutes,
                "kills_1h": kills_1h
            }


def check_redisq_status():
    """Check if RedisQ endpoint is accessible."""
    try:
        response = requests.get(
            "https://zkillredisq.stream/listen.php?ttw=1",
            timeout=5,
            headers={"User-Agent": "EVE-Copilot-Monitor/1.0"}
        )

        if response.status_code == 200:
            return {"status": "ok", "message": "RedisQ accessible"}
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            return {"status": "rate_limited", "message": f"Rate limited (Retry-After: {retry_after}s)"}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "blocked", "message": "Connection refused (IP blocked?)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    log("=" * 50)
    log("Data Freshness Check Starting")

    # Check data freshness
    freshness = check_data_freshness()
    log(f"Data: {freshness['status'].upper()} - {freshness['message']}")

    # Check RedisQ
    redisq = check_redisq_status()
    log(f"RedisQ: {redisq['status'].upper()} - {redisq['message']}")

    # Determine overall status
    exit_code = 0
    alert_message = None
    alert_level = None

    if freshness["status"] == "critical":
        alert_level = "critical"
        alert_message = f"**Killmail data is {freshness['age_minutes']} minutes old!**\n\n"
        alert_message += f"Latest kill: {freshness['latest_kill']}\n"
        alert_message += f"Kills in last hour: {freshness['kills_1h']}\n\n"
        alert_message += f"RedisQ Status: {redisq['message']}"
        exit_code = 2

    elif freshness["status"] == "warning":
        alert_level = "warning"
        alert_message = f"Killmail data is {freshness['age_minutes']} minutes old.\n\n"
        alert_message += f"RedisQ Status: {redisq['message']}\n"
        alert_message += "Check if RedisQ listener is running."
        exit_code = 1

    elif redisq["status"] in ["blocked", "rate_limited"]:
        alert_level = "warning"
        alert_message = f"RedisQ Issue: {redisq['message']}\n\n"
        alert_message += f"Data age: {freshness['age_minutes']} minutes\n"
        alert_message += "Live feed may be interrupted."
        exit_code = 1

    # Send alert if needed
    if alert_message:
        log(f"Sending {alert_level} alert", "ALERT")
        send_discord_alert(alert_message, alert_level)
    else:
        log("All systems nominal")

    log(f"Check complete (exit code: {exit_code})")
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"Monitor failed: {e}", "ERROR")
        sys.exit(3)
