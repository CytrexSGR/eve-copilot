"""Trading alerts service with Discord webhook support.
Migrated from monolith to market-service.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertEntry(BaseModel):
    """Alert entry model."""
    id: int = Field(default=0)
    character_id: int
    alert_type: str
    severity: str = Field(default="warning")
    type_id: Optional[int] = None
    type_name: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    is_read: bool = Field(default=False)
    discord_sent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertConfig(BaseModel):
    """Discord alert configuration."""
    character_id: int
    discord_webhook_url: Optional[str] = None
    discord_enabled: bool = Field(default=False)
    alert_margin_threshold: float = Field(default=10.0)
    alert_undercut_enabled: bool = Field(default=True)
    alert_velocity_enabled: bool = Field(default=True)
    alert_goals_enabled: bool = Field(default=True)
    min_alert_interval_minutes: int = Field(default=15)
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None


class AlertsResponse(BaseModel):
    """Response for alerts list."""
    character_id: int
    alerts: List[AlertEntry] = Field(default_factory=list)
    unread_count: int = Field(default=0)
    critical_count: int = Field(default=0)
    warning_count: int = Field(default=0)


class TradingAlertsService:
    """Service for managing trading alerts and Discord notifications."""

    def __init__(self, db_pool):
        """Initialize with database pool.

        Args:
            db_pool: Database connection pool (eve_shared)
        """
        self.db = db_pool

    def _compute_alert_hash(self, alert_type: str, type_id: Optional[int], message: str) -> str:
        """Compute hash for deduplication."""
        data = f"{alert_type}:{type_id or ''}:{message}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    async def create_alert(
        self,
        character_id: int,
        alert_type: str,
        message: str,
        severity: str = "warning",
        type_id: Optional[int] = None,
        type_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        send_discord: bool = True
    ) -> Optional[AlertEntry]:
        """Create a new trading alert.

        Args:
            character_id: Character ID
            alert_type: Type of alert (margin_low, undercut, etc.)
            message: Alert message
            severity: info, warning, or critical
            type_id: Item type ID (optional)
            type_name: Item type name (optional)
            details: Additional details as dict
            send_discord: Whether to send Discord notification

        Returns:
            AlertEntry if created, None if duplicate
        """
        alert_hash = self._compute_alert_hash(alert_type, type_id, message)

        with self.db.cursor() as cur:
            try:
                # Check if same alert exists in last hour
                cur.execute("""
                    SELECT id FROM trading_alert_log
                    WHERE character_id = %s
                      AND alert_type = %s
                      AND COALESCE(type_id, 0) = COALESCE(%s, 0)
                      AND alert_hash = %s
                      AND created_at > NOW() - INTERVAL '1 hour'
                    LIMIT 1
                """, (character_id, alert_type, type_id, alert_hash))

                if cur.fetchone():
                    logger.debug(f"Duplicate alert skipped: {alert_type} for {type_name}")
                    return None

                # Insert alert
                cur.execute("""
                    INSERT INTO trading_alert_log
                    (character_id, alert_type, severity, type_id, type_name, message, details, alert_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    character_id, alert_type, severity, type_id, type_name,
                    message, json.dumps(details) if details else None, alert_hash
                ))

                row = cur.fetchone()

                alert = AlertEntry(
                    id=row['id'],
                    character_id=character_id,
                    alert_type=alert_type,
                    severity=severity,
                    type_id=type_id,
                    type_name=type_name,
                    message=message,
                    details=details,
                    created_at=row['created_at']
                )

                # Send Discord notification if enabled
                if send_discord:
                    self._send_discord_notification_sync(character_id, alert)

                return alert

            except Exception as e:
                logger.error(f"Error creating alert: {e}")
                raise

    def _send_discord_notification_sync(self, character_id: int, alert: AlertEntry) -> bool:
        """Send Discord notification synchronously.

        Args:
            character_id: Character ID
            alert: Alert entry

        Returns:
            True if sent successfully
        """
        # Get Discord config
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT discord_webhook_url, discord_enabled, min_alert_interval_minutes,
                       quiet_hours_start, quiet_hours_end
                FROM trading_discord_config
                WHERE character_id = %s
            """, (character_id,))

            row = cur.fetchone()
            if not row or not row['discord_webhook_url'] or not row['discord_enabled']:
                return False

            webhook_url = row['discord_webhook_url']
            min_interval = row['min_alert_interval_minutes'] or 15
            quiet_start = row['quiet_hours_start']
            quiet_end = row['quiet_hours_end']

            # Check quiet hours
            current_hour = datetime.now(timezone.utc).hour
            if quiet_start is not None and quiet_end is not None:
                if quiet_start <= current_hour < quiet_end:
                    logger.debug("Skipping Discord notification during quiet hours")
                    return False

            # Check last notification time
            cur.execute("""
                SELECT discord_sent_at FROM trading_alert_log
                WHERE character_id = %s AND discord_sent = TRUE
                ORDER BY discord_sent_at DESC LIMIT 1
            """, (character_id,))

            last_sent = cur.fetchone()
            if last_sent and last_sent['discord_sent_at']:
                elapsed = (datetime.now(timezone.utc) - last_sent['discord_sent_at'].replace(tzinfo=timezone.utc)).total_seconds() / 60
                if elapsed < min_interval:
                    logger.debug(f"Rate limiting Discord notification, {min_interval - elapsed:.1f}m remaining")
                    return False

        # Send notification
        try:
            color = {"critical": 0xFF0000, "warning": 0xFFA500, "info": 0x3B82F6}.get(alert.severity, 0x6B7280)

            embed = {
                "title": f"Trading Alert: {alert.alert_type.replace('_', ' ').title()}",
                "description": alert.message,
                "color": color,
                "timestamp": alert.created_at.isoformat(),
                "fields": []
            }

            if alert.type_name:
                embed["fields"].append({"name": "Item", "value": alert.type_name, "inline": True})

            if alert.details:
                for key, value in list(alert.details.items())[:3]:
                    embed["fields"].append({"name": key.replace("_", " ").title(), "value": str(value), "inline": True})

            embed["footer"] = {"text": "EVE Copilot Trading Alerts"}

            response = httpx.post(
                webhook_url,
                json={"embeds": [embed]},
                timeout=10.0
            )

            if response.status_code in (200, 204):
                # Mark as sent
                with self.db.cursor() as cur:
                    cur.execute("""
                        UPDATE trading_alert_log
                        SET discord_sent = TRUE, discord_sent_at = NOW()
                        WHERE id = %s
                    """, (alert.id,))
                return True
            else:
                logger.warning(f"Discord webhook returned {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    def get_alerts(
        self,
        character_id: int,
        limit: int = 50,
        unread_only: bool = False,
        alert_type: Optional[str] = None
    ) -> AlertsResponse:
        """Get alerts for a character.

        Args:
            character_id: Character ID
            limit: Max alerts to return
            unread_only: Only return unread alerts
            alert_type: Filter by alert type

        Returns:
            AlertsResponse with alerts list
        """
        with self.db.cursor() as cur:
            # Build query
            where = ["character_id = %s"]
            params = [character_id]

            if unread_only:
                where.append("is_read = FALSE")

            if alert_type:
                where.append("alert_type = %s")
                params.append(alert_type)

            params.append(limit)

            cur.execute(f"""
                SELECT id, alert_type, severity, type_id, type_name, message,
                       details, is_read, discord_sent, created_at
                FROM trading_alert_log
                WHERE {' AND '.join(where)}
                ORDER BY created_at DESC
                LIMIT %s
            """, params)

            alerts = []
            for row in cur.fetchall():
                alerts.append(AlertEntry(
                    id=row['id'],
                    character_id=character_id,
                    alert_type=row['alert_type'],
                    severity=row['severity'],
                    type_id=row['type_id'],
                    type_name=row['type_name'],
                    message=row['message'],
                    details=row['details'] if row['details'] else None,
                    is_read=row['is_read'],
                    discord_sent=row['discord_sent'],
                    created_at=row['created_at']
                ))

            # Get counts - use column aliases for dict access
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_read = FALSE) AS unread_count,
                    COUNT(*) FILTER (WHERE severity = 'critical' AND is_read = FALSE) AS critical_count,
                    COUNT(*) FILTER (WHERE severity = 'warning' AND is_read = FALSE) AS warning_count
                FROM trading_alert_log
                WHERE character_id = %s AND created_at > NOW() - INTERVAL '7 days'
            """, (character_id,))

            counts = cur.fetchone()

            return AlertsResponse(
                character_id=character_id,
                alerts=alerts,
                unread_count=counts['unread_count'] or 0,
                critical_count=counts['critical_count'] or 0,
                warning_count=counts['warning_count'] or 0
            )

    def mark_read(self, character_id: int, alert_ids: Optional[List[int]] = None) -> int:
        """Mark alerts as read.

        Args:
            character_id: Character ID
            alert_ids: Specific alert IDs to mark (None = mark all)

        Returns:
            Number of alerts marked
        """
        with self.db.cursor() as cur:
            if alert_ids:
                cur.execute("""
                    UPDATE trading_alert_log
                    SET is_read = TRUE
                    WHERE character_id = %s AND id = ANY(%s) AND is_read = FALSE
                """, (character_id, alert_ids))
            else:
                cur.execute("""
                    UPDATE trading_alert_log
                    SET is_read = TRUE
                    WHERE character_id = %s AND is_read = FALSE
                """, (character_id,))

            count = cur.rowcount
            return count

    def get_config(self, character_id: int) -> AlertConfig:
        """Get alert configuration for a character.

        Args:
            character_id: Character ID

        Returns:
            AlertConfig (creates default if not exists)
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT discord_webhook_url, discord_enabled, alert_margin_threshold,
                       alert_undercut_enabled, alert_velocity_enabled, alert_goals_enabled,
                       min_alert_interval_minutes, quiet_hours_start, quiet_hours_end
                FROM trading_discord_config
                WHERE character_id = %s
            """, (character_id,))

            row = cur.fetchone()
            if row:
                return AlertConfig(
                    character_id=character_id,
                    discord_webhook_url=row['discord_webhook_url'],
                    discord_enabled=row['discord_enabled'],
                    alert_margin_threshold=float(row['alert_margin_threshold']) if row['alert_margin_threshold'] else 10.0,
                    alert_undercut_enabled=row['alert_undercut_enabled'],
                    alert_velocity_enabled=row['alert_velocity_enabled'],
                    alert_goals_enabled=row['alert_goals_enabled'],
                    min_alert_interval_minutes=row['min_alert_interval_minutes'] or 15,
                    quiet_hours_start=row['quiet_hours_start'],
                    quiet_hours_end=row['quiet_hours_end']
                )

            # Create default config
            cur.execute("""
                INSERT INTO trading_discord_config (character_id)
                VALUES (%s)
                ON CONFLICT (character_id) DO NOTHING
            """, (character_id,))

            return AlertConfig(character_id=character_id)

    def update_config(self, config: AlertConfig) -> AlertConfig:
        """Update alert configuration.

        Args:
            config: AlertConfig to save

        Returns:
            Updated AlertConfig
        """
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO trading_discord_config
                (character_id, discord_webhook_url, discord_enabled, alert_margin_threshold,
                 alert_undercut_enabled, alert_velocity_enabled, alert_goals_enabled,
                 min_alert_interval_minutes, quiet_hours_start, quiet_hours_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (character_id) DO UPDATE SET
                    discord_webhook_url = EXCLUDED.discord_webhook_url,
                    discord_enabled = EXCLUDED.discord_enabled,
                    alert_margin_threshold = EXCLUDED.alert_margin_threshold,
                    alert_undercut_enabled = EXCLUDED.alert_undercut_enabled,
                    alert_velocity_enabled = EXCLUDED.alert_velocity_enabled,
                    alert_goals_enabled = EXCLUDED.alert_goals_enabled,
                    min_alert_interval_minutes = EXCLUDED.min_alert_interval_minutes,
                    quiet_hours_start = EXCLUDED.quiet_hours_start,
                    quiet_hours_end = EXCLUDED.quiet_hours_end
            """, (
                config.character_id, config.discord_webhook_url, config.discord_enabled,
                config.alert_margin_threshold, config.alert_undercut_enabled,
                config.alert_velocity_enabled, config.alert_goals_enabled,
                config.min_alert_interval_minutes, config.quiet_hours_start, config.quiet_hours_end
            ))
            return config

    def test_discord_webhook(self, character_id: int) -> bool:
        """Test Discord webhook by sending a test message.

        Args:
            character_id: Character ID

        Returns:
            True if successful
        """
        config = self.get_config(character_id)
        if not config.discord_webhook_url:
            return False

        try:
            response = httpx.post(
                config.discord_webhook_url,
                json={
                    "embeds": [{
                        "title": "EVE Copilot - Test Notification",
                        "description": "Your Discord webhook is working correctly!",
                        "color": 0x3B82F6,
                        "footer": {"text": "EVE Copilot Trading Alerts"}
                    }]
                },
                timeout=10.0
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord webhook test failed: {e}")
            return False
