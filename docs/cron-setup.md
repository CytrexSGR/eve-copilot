# Cron Job Setup Guide

This guide documents how to install, monitor, and troubleshoot the EVE Co-Pilot cron jobs.

## Doctrine Clustering Job

The doctrine clustering job analyzes combat losses to identify ship doctrines used by alliances. It runs daily at 06:00 UTC to ensure fresh intelligence data.

### Installation

To install the doctrine clustering cron job:

```bash
(crontab -l 2>/dev/null; echo "0 6 * * * /home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh") | crontab -
```

This adds the job to your user crontab without removing existing entries.

### Verification

Check if the job is installed:

```bash
crontab -l | grep doctrine
```

Expected output:
```
0 6 * * * /home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh
```

### Schedule

- **Frequency:** Daily
- **Time:** 06:00 UTC (07:00 Berlin time)
- **Purpose:** Analyze killmails to detect ship doctrines and market opportunities

### Manual Trigger

To run the job manually without waiting for the scheduled time:

```bash
/home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh
```

Or run the Python script directly:

```bash
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/python jobs/doctrine_clustering.py
```

### Monitoring

#### View Recent Logs

Check the last 50 lines of the log:

```bash
tail -50 /home/cytrex/eve_copilot/logs/doctrine_clustering.log
```

#### Follow Live Logs

Monitor the job in real-time:

```bash
tail -f /home/cytrex/eve_copilot/logs/doctrine_clustering.log
```

#### Check Last Execution

View when the job last ran and its result:

```bash
grep -E "Starting|Processing|Clustering|Complete" /home/cytrex/eve_copilot/logs/doctrine_clustering.log | tail -10
```

### Troubleshooting

#### Job Not Running

1. **Verify crontab installation:**
   ```bash
   crontab -l | grep doctrine
   ```

2. **Check cron daemon status:**
   ```bash
   systemctl status cron
   ```

3. **Verify script permissions:**
   ```bash
   ls -la /home/cytrex/eve_copilot/jobs/cron_doctrine_clustering.sh
   ```
   Should be executable (`-rwxr-xr-x`)

4. **Check system logs:**
   ```bash
   grep CRON /var/log/syslog | grep doctrine
   ```

#### Script Errors

1. **View full error log:**
   ```bash
   tail -100 /home/cytrex/eve_copilot/logs/doctrine_clustering.log | grep -i error
   ```

2. **Test database connection:**
   ```bash
   echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "SELECT COUNT(*) FROM combat_ship_losses;"
   ```

3. **Verify Python environment:**
   ```bash
   /home/cytrex/.local/bin/python --version
   /home/cytrex/.local/bin/python -c "import sklearn; print(sklearn.__version__)"
   ```

#### No Doctrines Detected

1. **Check data availability:**
   ```bash
   echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "SELECT COUNT(*) FROM combat_ship_losses WHERE loss_date >= CURRENT_DATE - 30;"
   ```
   Should show > 0 records

2. **Verify region ID:**
   Check that the region_id in the script matches your target region

3. **Review clustering parameters:**
   Edit `/home/cytrex/eve_copilot/jobs/doctrine_clustering.py` and adjust:
   - `min_fleet_size`: Minimum ships to form a doctrine (default: 10)
   - `lookback_days`: Days to analyze (default: 30)

### Uninstallation

To remove the cron job:

```bash
crontab -l | grep -v "doctrine_clustering" | crontab -
```

## All EVE Co-Pilot Cron Jobs

View all installed cron jobs:

```bash
crontab -l
```

Current schedule:

| Job | Schedule | Purpose |
|-----|----------|---------|
| `cron_batch_calculator.sh` | Every 5 minutes | Manufacturing opportunities |
| `cron_regional_prices.sh` | Every 30 minutes | Regional market prices |
| `cron_sov_tracker.sh` | Every 30 minutes | Sovereignty campaigns |
| `cron_fw_tracker.sh` | Every 30 minutes | Faction Warfare status |
| `cron_killmail_fetcher.sh` | Daily at 06:00 | Download killmail data |
| `cron_doctrine_clustering.sh` | Daily at 06:00 | Analyze ship doctrines |
| `cron_capability_sync.sh` | Daily at 04:00 | Character capability sync |
| `cron_telegram_report.sh` | Every hour | Telegram battle reports |
| `cron_alliance_wars.sh` | Every 30 minutes | Alliance war tracking |
| `cron_war_profiteering.sh` | Every 6 hours | War profiteering analysis |
| `cron_goaccess_update.sh` | Every 10 minutes | Web analytics |
| `cron_battle_cleanup.sh` | Every 30 minutes | Battle cleanup |
| `cron_report_generator.sh` | Every 6 hours | Report pre-generation |
| `cron_character_sync.sh` | Every 30 minutes | Character data sync |
| `cron_skill_snapshot.sh` | Daily at 05:00 | Skill analysis snapshots |

### Viewing All Logs

```bash
# View all logs
ls -lh /home/cytrex/eve_copilot/logs/

# Monitor all jobs
tail -f /home/cytrex/eve_copilot/logs/*.log
```

## Additional Resources

- **Main Documentation:** `/home/cytrex/eve_copilot/CLAUDE.md`
- **Backend Guide:** `/home/cytrex/eve_copilot/CLAUDE.backend.md`
- **Job Scripts:** `/home/cytrex/eve_copilot/jobs/`
- **Logs Directory:** `/home/cytrex/eve_copilot/logs/`

## Support

For issues or questions, check the main documentation or review the session summaries in `/home/cytrex/eve_copilot/docs/`.
