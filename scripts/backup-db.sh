#!/usr/bin/env bash
# ============================================================================
# backup-db.sh — PostgreSQL Backup fuer EVE Copilot
# Erstellt komprimierte pg_dump Backups mit 7-Tage Retention.
# Usage: ./scripts/backup-db.sh
# Cron:  0 3 * * * /home/cytrex/eve_copilot/scripts/backup-db.sh
# ============================================================================
set -euo pipefail

BACKUP_DIR="/home/cytrex/eve_data/backups"
CONTAINER="eve_db"
DB_NAME="eve_sde"
DB_USER="eve"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/eve_copilot_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# Backup erstellen
log "START: Backup ${DB_NAME} -> ${BACKUP_FILE}"

if docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" --no-owner --no-privileges | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "OK: Backup erstellt (${SIZE})"
else
    log "FEHLER: pg_dump fehlgeschlagen"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Integritaetscheck
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    log "FEHLER: Backup-Datei korrupt"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Alte Backups loeschen (Retention)
DELETED=$(find "$BACKUP_DIR" -name 'eve_copilot_*.sql.gz' -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
    log "CLEANUP: ${DELETED} alte Backups geloescht (>${RETENTION_DAYS} Tage)"
fi

# Zusammenfassung
TOTAL=$(find "$BACKUP_DIR" -name 'eve_copilot_*.sql.gz' | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "DONE: ${TOTAL} Backups vorhanden (${TOTAL_SIZE} gesamt)"
