"""Battle Event Detector - Detects changes in battle data and generates events."""

import logging
from datetime import datetime
from typing import List, Dict, Any

from app.database import db_cursor
from app.services.events.models import (
    BattleEvent, BattleEventType, BattleEventSeverity, EVENT_SEVERITY_MAP
)
from app.repository.battle_events import battle_events_repo

logger = logging.getLogger(__name__)


class BattleEventDetector:
    """Detects battle events by comparing current state with previous snapshots."""

    HOT_ZONE_RANK_CHANGE = 3  # Positions moved to trigger event

    def __init__(self):
        self.repo = battle_events_repo

    def run_detection(self) -> List[BattleEvent]:
        """Run full detection cycle. Returns detected events."""
        all_events = []

        try:
            # Detect capital kills
            capital_events = self._detect_capital_kills()
            all_events.extend(capital_events)

            # Detect hot zone changes
            hotzone_events = self._detect_hot_zone_changes()
            all_events.extend(hotzone_events)

            # Detect high-value kills
            hvk_events = self._detect_high_value_kills()
            all_events.extend(hvk_events)

            # Save all events
            if all_events:
                saved = self.repo.save_events(all_events)
                logger.info(f"Detection complete: {len(all_events)} detected, {saved} new")

        except Exception as e:
            logger.error(f"Event detection failed: {e}", exc_info=True)

        return all_events

    def _detect_capital_kills(self) -> List[BattleEvent]:
        """Detect capital ship kills in last 2 minutes."""
        events = []

        CAPITAL_GROUPS = {
            30: ('Titan', BattleEventType.TITAN_KILLED),
            659: ('Supercarrier', BattleEventType.SUPERCARRIER_KILLED),
            547: ('Carrier', BattleEventType.CARRIER_KILLED),
            485: ('Dreadnought', BattleEventType.DREAD_KILLED),
            1538: ('Force Auxiliary', BattleEventType.FAX_KILLED),
        }

        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.ship_value,
                    k.solar_system_id,
                    s."solarSystemName" as system_name,
                    r."regionName" as region_name,
                    r."regionID" as region_id,
                    k.victim_alliance_id,
                    k.victim_corporation_id,
                    t."typeName" as ship_type,
                    t."groupID" as group_id,
                    COALESCE(anc.alliance_name, 'Unknown') as victim_alliance_name
                FROM killmails k
                JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
                LEFT JOIN alliance_name_cache anc ON k.victim_alliance_id = anc.alliance_id
                WHERE k.killmail_time >= NOW() - INTERVAL '12 hours'
                  AND t."groupID" = ANY(%s)
                ORDER BY k.killmail_time DESC
            """, (list(CAPITAL_GROUPS.keys()),))

            for row in cur.fetchall():
                group_id = row['group_id']
                ship_class, event_type = CAPITAL_GROUPS.get(group_id, ('Capital', BattleEventType.CAPITAL_KILLED))

                isk_value = row['ship_value'] or 0
                isk_billions = isk_value / 1_000_000_000

                event = BattleEvent(
                    event_type=event_type,
                    severity=EVENT_SEVERITY_MAP.get(event_type, BattleEventSeverity.HIGH),
                    title=f"{ship_class} down in {row['system_name']}",
                    description=f"{row['ship_type']} • {row['victim_alliance_name']} • {isk_billions:.1f}B ISK",
                    system_id=row['solar_system_id'],
                    system_name=row['system_name'],
                    region_id=row['region_id'],
                    region_name=row['region_name'],
                    alliance_id=row['victim_alliance_id'],
                    alliance_name=row['victim_alliance_name'],
                    event_data={
                        'killmail_id': row['killmail_id'],
                        'ship_type': row['ship_type'],
                        'ship_class': ship_class,
                        'isk_value': isk_value,
                    },
                    event_time=row['killmail_time'],
                )
                events.append(event)

        return events

    def _detect_hot_zone_changes(self) -> List[BattleEvent]:
        """Detect significant changes in hot zone rankings."""
        events = []

        with db_cursor() as cur:
            # Get current hot zones (top 20, last hour)
            cur.execute("""
                SELECT
                    k.solar_system_id,
                    s."solarSystemName" as system_name,
                    r."regionName" as region_name,
                    r."regionID" as region_id,
                    COUNT(*) as kills,
                    SUM(k.ship_value) as total_isk
                FROM killmails k
                JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
                WHERE k.killmail_time >= NOW() - INTERVAL '12 hours'
                GROUP BY k.solar_system_id, s."solarSystemName", r."regionName", r."regionID"
                ORDER BY kills DESC
                LIMIT 20
            """)

            current_zones = {}
            for idx, row in enumerate(cur.fetchall()):
                current_zones[row['solar_system_id']] = {
                    'rank': idx + 1,
                    'system_name': row['system_name'],
                    'region_name': row['region_name'],
                    'region_id': row['region_id'],
                    'kills': row['kills'],
                    'total_isk': float(row['total_isk'] or 0),
                }

        # Get previous snapshot
        prev_snapshot = self.repo.get_latest_snapshot('hot_zones_1h')

        if prev_snapshot:
            prev_zones = prev_snapshot.get('zones', {})

            for sys_id, current in current_zones.items():
                sys_id_str = str(sys_id)
                if sys_id_str in prev_zones:
                    prev_rank = prev_zones[sys_id_str].get('rank', 999)
                    curr_rank = current['rank']

                    # Significant rank improvement into top 5
                    if curr_rank <= 5 and prev_rank - curr_rank >= self.HOT_ZONE_RANK_CHANGE:
                        event = BattleEvent(
                            event_type=BattleEventType.HOT_ZONE_SHIFT,
                            severity=BattleEventSeverity.HIGH,
                            title=f"{current['system_name']} surged to #{curr_rank}",
                            description=f"Was #{prev_rank} • {current['kills']} kills • {current['region_name']}",
                            system_id=sys_id,
                            system_name=current['system_name'],
                            region_id=current['region_id'],
                            region_name=current['region_name'],
                            event_data={
                                'prev_rank': prev_rank,
                                'curr_rank': curr_rank,
                                'kills': current['kills'],
                            },
                        )
                        events.append(event)

                # New system in top 5
                elif current['rank'] <= 5:
                    event = BattleEvent(
                        event_type=BattleEventType.HOT_ZONE_SHIFT,
                        severity=BattleEventSeverity.MEDIUM,
                        title=f"{current['system_name']} entered top 5",
                        description=f"#{current['rank']} • {current['kills']} kills • {current['region_name']}",
                        system_id=sys_id,
                        system_name=current['system_name'],
                        region_id=current['region_id'],
                        region_name=current['region_name'],
                        event_data={
                            'curr_rank': current['rank'],
                            'kills': current['kills'],
                            'new_entry': True,
                        },
                    )
                    events.append(event)

        # Save new snapshot
        snapshot_data = {'zones': {str(k): v for k, v in current_zones.items()}}
        self.repo.save_snapshot('hot_zones_1h', snapshot_data)

        return events

    def _detect_high_value_kills(self) -> List[BattleEvent]:
        """Detect high-value kills (>10B ISK) in last 2 minutes."""
        events = []
        MIN_ISK = 10_000_000_000  # 10B

        # Capital group IDs to exclude (handled separately)
        from eve_shared.constants import CAPITAL_GROUP_IDS

        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.ship_value,
                    k.solar_system_id,
                    s."solarSystemName" as system_name,
                    r."regionName" as region_name,
                    r."regionID" as region_id,
                    t."typeName" as ship_type,
                    k.victim_alliance_id,
                    COALESCE(anc.alliance_name, 'Unknown') as victim_alliance_name
                FROM killmails k
                JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
                LEFT JOIN alliance_name_cache anc ON k.victim_alliance_id = anc.alliance_id
                WHERE k.killmail_time >= NOW() - INTERVAL '12 hours'
                  AND k.ship_value >= %s
                  AND t."groupID" != ALL(%s)
                ORDER BY k.ship_value DESC
                LIMIT 10
            """, (MIN_ISK, list(CAPITAL_GROUP_IDS)))

            for row in cur.fetchall():
                isk_billions = row['ship_value'] / 1_000_000_000

                event = BattleEvent(
                    event_type=BattleEventType.ISK_SPIKE,
                    severity=BattleEventSeverity.HIGH,
                    title=f"High-value kill: {isk_billions:.1f}B ISK",
                    description=f"{row['ship_type']} • {row['victim_alliance_name']} • {row['system_name']}",
                    system_id=row['solar_system_id'],
                    system_name=row['system_name'],
                    region_id=row['region_id'],
                    region_name=row['region_name'],
                    alliance_id=row['victim_alliance_id'],
                    alliance_name=row['victim_alliance_name'],
                    event_data={
                        'killmail_id': row['killmail_id'],
                        'ship_type': row['ship_type'],
                        'isk_value': row['ship_value'],
                    },
                    event_time=row['killmail_time'],
                )
                events.append(event)

        return events

    def _detect_last_supercaps(self) -> List[BattleEvent]:
        """Generate 'Last Titan/Super X ago' info events."""
        events = []

        SUPERCAP_GROUPS = {
            30: ('Titan', BattleEventType.LAST_TITAN),
            659: ('Supercarrier', BattleEventType.LAST_SUPERCARRIER),
        }

        with db_cursor() as cur:
            for group_id, (ship_class, event_type) in SUPERCAP_GROUPS.items():
                cur.execute("""
                    SELECT
                        k.killmail_id,
                        k.killmail_time,
                        k.ship_value,
                        k.solar_system_id,
                        s."solarSystemName" as system_name,
                        r."regionName" as region_name,
                        r."regionID" as region_id,
                        t."typeName" as ship_type,
                        k.victim_alliance_id,
                        COALESCE(anc.alliance_name, 'Unknown') as victim_alliance_name,
                        EXTRACT(EPOCH FROM (NOW() - k.killmail_time)) as seconds_ago
                    FROM killmails k
                    JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                    JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                    JOIN "mapRegions" r ON s."regionID" = r."regionID"
                    LEFT JOIN alliance_name_cache anc ON k.victim_alliance_id = anc.alliance_id
                    WHERE t."groupID" = %s
                    ORDER BY k.killmail_time DESC
                    LIMIT 1
                """, (group_id,))

                row = cur.fetchone()
                if row:
                    seconds_ago = row['seconds_ago']
                    # Format time ago
                    if seconds_ago < 3600:
                        time_ago = f"{int(seconds_ago / 60)}m ago"
                    elif seconds_ago < 86400:
                        hours = int(seconds_ago / 3600)
                        time_ago = f"{hours}h ago"
                    else:
                        days = int(seconds_ago / 86400)
                        hours = int((seconds_ago % 86400) / 3600)
                        time_ago = f"{days}d {hours}h ago"

                    isk_billions = (row['ship_value'] or 0) / 1_000_000_000

                    event = BattleEvent(
                        event_type=event_type,
                        severity=BattleEventSeverity.MEDIUM,
                        title=f"Last {ship_class}: {time_ago}",
                        description=f"{row['ship_type']} • {row['victim_alliance_name']} • {isk_billions:.1f}B",
                        system_id=row['solar_system_id'],
                        system_name=row['system_name'],
                        region_id=row['region_id'],
                        region_name=row['region_name'],
                        alliance_id=row['victim_alliance_id'],
                        alliance_name=row['victim_alliance_name'],
                        event_data={
                            'killmail_id': row['killmail_id'],
                            'ship_type': row['ship_type'],
                            'ship_class': ship_class,
                            'isk_value': row['ship_value'],
                            'seconds_ago': seconds_ago,
                        },
                        event_time=row['killmail_time'],
                    )
                    events.append(event)

        return events


# Global detector instance
battle_event_detector = BattleEventDetector()
