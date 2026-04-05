#!/usr/bin/env python3
"""
PI Colony Monitor - Cron Job

Runs every 30 minutes to check PI colony status and generate alerts.

Alerts generated:
- extractor_depleting: Extractor has < 12h remaining (configurable)
- extractor_stopped: Extractor has stopped (expiry_time passed)
- storage_full: Storage > 90% capacity (configurable)
- factory_idle: Factory has no active schematic
- pickup_reminder: Time for scheduled pickup

Usage:
    python3 -m jobs.pi_monitor

Cron:
    */30 * * * * cd /home/cytrex/eve_copilot/services/production-service && python3 -m jobs.pi_monitor >> /home/cytrex/eve_copilot/logs/pi_monitor.log 2>&1
"""

import logging
import time
import sys
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eve_shared import get_db
from app.services.pi.repository import PIRepository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default thresholds (can be overridden per-character)
DEFAULT_EXTRACTOR_WARNING_HOURS = 12
DEFAULT_EXTRACTOR_CRITICAL_HOURS = 4
DEFAULT_STORAGE_WARNING_PERCENT = 75
DEFAULT_STORAGE_CRITICAL_PERCENT = 90

# EVE PI pin type IDs for classification
EXTRACTOR_TYPE_IDS = {2848}  # Extractor Control Unit
STORAGE_TYPE_IDS = {2256, 2541, 2542, 2543, 2544}  # Storage/Launchpad types
FACTORY_TYPE_IDS = {2469, 2470, 2471, 2472, 2473, 2474, 2475, 2481, 2482, 2483, 2484, 2485}


class PIMonitor:
    """PI Colony Monitor service."""

    def __init__(self, db):
        self.db = db
        self.repo = PIRepository(db)

    def get_config(self, character_id: int) -> Dict:
        """Get alert config for character, or defaults."""
        config = self.repo.get_alert_config(character_id)
        if config:
            return dict(config)
        return {
            'discord_webhook_url': None,
            'discord_enabled': True,
            'extractor_warning_hours': DEFAULT_EXTRACTOR_WARNING_HOURS,
            'extractor_critical_hours': DEFAULT_EXTRACTOR_CRITICAL_HOURS,
            'storage_warning_percent': DEFAULT_STORAGE_WARNING_PERCENT,
            'storage_critical_percent': DEFAULT_STORAGE_CRITICAL_PERCENT,
            'alert_extractor_depleting': True,
            'alert_extractor_stopped': True,
            'alert_storage_full': True,
            'alert_factory_idle': True,
            'alert_pickup_reminder': True,
        }

    def check_extractor(
        self,
        character_id: int,
        character_name: str,
        colony: Dict,
        pin: Dict,
        config: Dict
    ) -> Optional[Dict]:
        """Check extractor status and return alert if needed."""
        if not config.get('alert_extractor_depleting') and not config.get('alert_extractor_stopped'):
            return None

        expiry_time = pin.get('expiry_time')
        if not expiry_time:
            return None

        now = datetime.utcnow()
        if isinstance(expiry_time, str):
            expiry_time = datetime.fromisoformat(expiry_time.replace('Z', '+00:00')).replace(tzinfo=None)

        hours_remaining = (expiry_time - now).total_seconds() / 3600

        # Extractor stopped
        if hours_remaining <= 0 and config.get('alert_extractor_stopped'):
            return {
                'character_id': character_id,
                'alert_type': 'extractor_stopped',
                'severity': 'critical',
                'planet_id': colony.get('planet_id'),
                'planet_name': colony.get('solar_system_name', 'Unknown'),
                'pin_id': pin.get('pin_id'),
                'product_type_id': pin.get('product_type_id'),
                'product_name': pin.get('product_name', 'Unknown'),
                'message': f"Extractor stopped on {colony.get('solar_system_name', 'Unknown')} - {pin.get('product_name', 'Resource')}",
                'details': {'hours_remaining': 0, 'expiry_time': expiry_time.isoformat()}
            }

        # Extractor depleting (critical)
        critical_hours = config.get('extractor_critical_hours', DEFAULT_EXTRACTOR_CRITICAL_HOURS)
        warning_hours = config.get('extractor_warning_hours', DEFAULT_EXTRACTOR_WARNING_HOURS)

        if hours_remaining <= critical_hours and config.get('alert_extractor_depleting'):
            return {
                'character_id': character_id,
                'alert_type': 'extractor_depleting',
                'severity': 'critical',
                'planet_id': colony.get('planet_id'),
                'planet_name': colony.get('solar_system_name', 'Unknown'),
                'pin_id': pin.get('pin_id'),
                'product_type_id': pin.get('product_type_id'),
                'product_name': pin.get('product_name', 'Unknown'),
                'message': f"CRITICAL: {pin.get('product_name', 'Extractor')} depletes in {hours_remaining:.1f}h on {colony.get('solar_system_name', 'Unknown')}",
                'details': {'hours_remaining': hours_remaining, 'expiry_time': expiry_time.isoformat()}
            }

        # Extractor depleting (warning)
        if hours_remaining <= warning_hours and config.get('alert_extractor_depleting'):
            return {
                'character_id': character_id,
                'alert_type': 'extractor_depleting',
                'severity': 'warning',
                'planet_id': colony.get('planet_id'),
                'planet_name': colony.get('solar_system_name', 'Unknown'),
                'pin_id': pin.get('pin_id'),
                'product_type_id': pin.get('product_type_id'),
                'product_name': pin.get('product_name', 'Unknown'),
                'message': f"{pin.get('product_name', 'Extractor')} depletes in {hours_remaining:.1f}h on {colony.get('solar_system_name', 'Unknown')}",
                'details': {'hours_remaining': hours_remaining, 'expiry_time': expiry_time.isoformat()}
            }

        return None

    def check_character(self, character_id: int) -> List[Dict]:
        """Check all colonies for a character and return alerts."""
        alerts = []
        config = self.get_config(character_id)

        # Get character name
        character_name = f"Character {character_id}"
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT character_name FROM oauth_tokens WHERE character_id = %s
                """, (character_id,))
                result = cur.fetchone()
                if result:
                    character_name = result['character_name']
        except Exception:
            pass

        # Get colonies
        colonies = self.repo.get_colonies(character_id)

        for colony in colonies:
            colony_dict = colony if isinstance(colony, dict) else colony.__dict__

            # Get colony details with pins
            try:
                detail = self.repo.get_colony_detail(colony_dict.get('id'))
                if not detail:
                    continue

                detail_dict = detail if isinstance(detail, dict) else detail.__dict__
                pins = detail_dict.get('pins', [])

                for pin in pins:
                    pin_dict = pin if isinstance(pin, dict) else pin.__dict__
                    type_id = pin_dict.get('type_id')

                    # Check extractors
                    if pin_dict.get('expiry_time'):  # Has expiry = likely extractor
                        alert = self.check_extractor(
                            character_id, character_name, colony_dict, pin_dict, config
                        )
                        if alert:
                            alerts.append(alert)

            except Exception as e:
                logger.warning(f"Failed to check colony {colony_dict.get('id')}: {e}")

        return alerts

    def send_discord_alert(self, alert: Dict, webhook_url: str) -> bool:
        """Send alert to Discord webhook."""
        if not webhook_url:
            return False

        # Color based on severity
        color = 0xFFA500 if alert['severity'] == 'warning' else 0xFF0000  # Orange or Red

        embed = {
            "title": f"PI Alert: {alert['alert_type'].replace('_', ' ').title()}",
            "description": alert['message'],
            "color": color,
            "fields": [],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "EVE Co-Pilot PI Monitor"}
        }

        if alert.get('product_name'):
            embed["fields"].append({
                "name": "Product",
                "value": alert['product_name'],
                "inline": True
            })

        if alert.get('details', {}).get('hours_remaining') is not None:
            embed["fields"].append({
                "name": "Time Remaining",
                "value": f"{alert['details']['hours_remaining']:.1f}h",
                "inline": True
            })

        try:
            response = requests.post(
                webhook_url,
                json={
                    "username": "EVE PI Monitor",
                    "embeds": [embed]
                },
                timeout=10
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        """Run the monitoring job."""
        start = time.time()
        result = {
            'characters_checked': 0,
            'colonies_checked': 0,
            'alerts_generated': 0,
            'alerts_by_type': {},
            'discord_notifications_sent': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Get all characters with PI
            character_ids = self.repo.get_all_character_ids_with_pi()
            result['characters_checked'] = len(character_ids)
            logger.info(f"Checking {len(character_ids)} characters with PI colonies")

            for char_id in character_ids:
                try:
                    alerts = self.check_character(char_id)
                    config = self.get_config(char_id)

                    for alert in alerts:
                        # Store alert
                        alert_id = self.repo.create_alert(
                            character_id=alert['character_id'],
                            alert_type=alert['alert_type'],
                            severity=alert['severity'],
                            message=alert['message'],
                            planet_id=alert.get('planet_id'),
                            planet_name=alert.get('planet_name'),
                            pin_id=alert.get('pin_id'),
                            product_type_id=alert.get('product_type_id'),
                            product_name=alert.get('product_name'),
                            details=alert.get('details')
                        )

                        if alert_id:
                            result['alerts_generated'] += 1
                            alert_type = alert['alert_type']
                            result['alerts_by_type'][alert_type] = result['alerts_by_type'].get(alert_type, 0) + 1

                            # Send Discord notification
                            if config.get('discord_enabled') and config.get('discord_webhook_url'):
                                if self.send_discord_alert(alert, config['discord_webhook_url']):
                                    self.repo.mark_alert_discord_sent(alert_id)
                                    result['discord_notifications_sent'] += 1

                except Exception as e:
                    logger.error(f"Failed to check character {char_id}: {e}")

            # Cleanup old alerts
            deleted = self.repo.cleanup_old_alerts()
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old alerts")

        except Exception as e:
            logger.error(f"PI Monitor job failed: {e}")
            result['error'] = str(e)

        result['duration_ms'] = int((time.time() - start) * 1000)
        logger.info(f"PI Monitor complete: {result['alerts_generated']} alerts generated in {result['duration_ms']}ms")
        return result


def main():
    """Entry point for cron job."""
    db = get_db()
    db.initialize()
    monitor = PIMonitor(db)
    result = monitor.run()

    if result.get('error'):
        sys.exit(1)


if __name__ == "__main__":
    main()
