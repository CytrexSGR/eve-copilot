"""Fleet Snapshot Collector - Task 3: Aggregates zkillboard kills into fleet snapshots.

This service hooks into the existing zkillboard live stream and:
1. Buffers kills in 5-minute time windows
2. Groups by system/region
3. Aggregates ship compositions
4. Saves snapshots to doctrine_fleet_snapshots table

Integration Point:
    The zkillboard live service (services/zkillboard/live_service.py) calls
    process_live_kill() for each incoming kill. We hook into this by calling
    our receive_kill() method from that pipeline.

Architecture:
    - Buffer: Dict[(region_id, system_id, timestamp_bucket)] -> buffer_data
    - Auto-flush: Snapshots older than current window are flushed on each kill
    - Filtering: Only fleets with >= min_fleet_size pilots are saved
    - Deduplication: killmail_ids tracked to prevent duplicate processing
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import psycopg2.extras

from src.database import get_db_connection
from services.war_economy.doctrine.models import FleetSnapshot, ShipEntry

# Ship types to exclude from doctrine detection (not combat ships)
EXCLUDED_SHIP_TYPES = {
    670,     # Capsule (Pod)
    33328,   # Capsule - Genolution 'Auroral' 197-variant
}


class FleetSnapshotCollector:
    """Collects and aggregates zkillboard kills into fleet snapshots.

    This collector buffers incoming killmails from the zkillboard live stream,
    groups them by location and time, and periodically flushes completed
    snapshots to the database.
    """

    def __init__(
        self,
        buffer_window_seconds: int = 300,  # 5 minutes
        min_fleet_size: int = 5
    ):
        """Initialize the fleet snapshot collector.

        Args:
            buffer_window_seconds: Time window for aggregating kills (default: 300s = 5min)
            min_fleet_size: Minimum number of unique pilots to consider a fleet (default: 5)
        """
        self.buffer_window_seconds = buffer_window_seconds
        self.min_fleet_size = min_fleet_size

        # Buffer structure: {(region_id, system_id, timestamp_bucket): buffer_data}
        # buffer_data = {
        #     "ships": {type_id: count},
        #     "killmail_ids": [id1, id2, ...],
        #     "total_pilots": count
        # }
        self.buffer: Dict[Tuple[int, int, datetime], Dict] = {}

        # Cache for system->region lookups
        self._region_cache: Dict[int, Optional[int]] = {}

    def get_timestamp_bucket(self, timestamp: datetime) -> datetime:
        """Calculate the 5-minute bucket for a given timestamp.

        Buckets align to clock boundaries: 12:00, 12:05, 12:10, etc.

        Args:
            timestamp: Kill timestamp

        Returns:
            Bucket start time (floor to nearest 5-minute boundary)

        Example:
            12:02:30 -> 12:00:00
            12:05:00 -> 12:05:00
            12:07:45 -> 12:05:00
        """
        # Convert to Unix timestamp
        epoch = timestamp.replace(tzinfo=None).timestamp()

        # Floor to nearest bucket
        bucket_epoch = (epoch // self.buffer_window_seconds) * self.buffer_window_seconds

        return datetime.fromtimestamp(bucket_epoch)

    def get_region_from_system(self, system_id: int) -> Optional[int]:
        """Lookup region_id from system_id using database.

        Uses in-memory cache to minimize DB queries.

        Args:
            system_id: Solar system ID

        Returns:
            Region ID or None if not found
        """
        # Check cache first
        if system_id in self._region_cache:
            return self._region_cache[system_id]

        # Query database
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "regionID" FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
                        (system_id,)
                    )
                    row = cur.fetchone()
                    region_id = row[0] if row else None

                    # Cache result
                    self._region_cache[system_id] = region_id
                    return region_id
        except Exception as e:
            print(f"Error fetching region for system {system_id}: {e}")
            return None

    def count_unique_pilots(self, kill: Dict) -> int:
        """Count unique pilots involved in a kill (victim + attackers).

        Args:
            kill: Killmail dict with victim and attackers

        Returns:
            Number of unique character_ids
        """
        pilot_ids = set()

        # Add victim
        victim_id = kill.get("victim", {}).get("character_id")
        if victim_id:
            pilot_ids.add(victim_id)

        # Add attackers
        for attacker in kill.get("attackers", []):
            attacker_id = attacker.get("character_id")
            if attacker_id:
                pilot_ids.add(attacker_id)

        return len(pilot_ids)

    def extract_ship_types(self, kill: Dict) -> Dict[int, int]:
        """Extract all ship types from a kill and count occurrences.

        Excludes non-combat ships like Capsules (pods).

        Args:
            kill: Killmail dict with victim and attackers

        Returns:
            Dict mapping ship_type_id to count
        """
        ship_counts = defaultdict(int)

        # Add victim ship (exclude capsules and other non-combat ships)
        victim_ship = kill.get("victim", {}).get("ship_type_id")
        if victim_ship and victim_ship not in EXCLUDED_SHIP_TYPES:
            ship_counts[victim_ship] += 1

        # Add attacker ships (exclude capsules and other non-combat ships)
        for attacker in kill.get("attackers", []):
            attacker_ship = attacker.get("ship_type_id")
            if attacker_ship and attacker_ship not in EXCLUDED_SHIP_TYPES:
                ship_counts[attacker_ship] += 1

        return dict(ship_counts)

    def buffer_kill(self, kill: Dict) -> None:
        """Add a kill to the buffer for aggregation.

        Kills are grouped by (region_id, system_id, timestamp_bucket).

        Args:
            kill: Killmail dict from zkillboard
        """
        # Extract metadata
        killmail_id = kill.get("killmail_id")
        system_id = kill.get("solar_system_id")
        kill_time_str = kill.get("killmail_time")

        if not killmail_id or not system_id or not kill_time_str:
            return

        # Parse timestamp
        kill_time = datetime.fromisoformat(kill_time_str.replace("Z", "+00:00"))
        timestamp_bucket = self.get_timestamp_bucket(kill_time)

        # Lookup region
        region_id = self.get_region_from_system(system_id)
        if not region_id:
            return

        # Create buffer key
        buffer_key = (region_id, system_id, timestamp_bucket)

        # Initialize buffer entry if needed
        if buffer_key not in self.buffer:
            self.buffer[buffer_key] = {
                "ships": defaultdict(int),
                "killmail_ids": [],
                "total_pilots": 0,
                "pilot_ids": set()  # Track unique pilots
            }

        buffer_entry = self.buffer[buffer_key]

        # Check for duplicate killmail
        if killmail_id in buffer_entry["killmail_ids"]:
            return

        # Add killmail ID
        buffer_entry["killmail_ids"].append(killmail_id)

        # Count unique pilots
        victim_id = kill.get("victim", {}).get("character_id")
        if victim_id:
            buffer_entry["pilot_ids"].add(victim_id)

        for attacker in kill.get("attackers", []):
            attacker_id = attacker.get("character_id")
            if attacker_id:
                buffer_entry["pilot_ids"].add(attacker_id)

        # Update total pilot count
        buffer_entry["total_pilots"] = len(buffer_entry["pilot_ids"])

        # Aggregate ship types
        ship_types = self.extract_ship_types(kill)
        for ship_type_id, count in ship_types.items():
            buffer_entry["ships"][ship_type_id] += count

    def create_snapshot_from_buffer(
        self,
        buffer_key: Tuple[int, int, datetime],
        buffer_data: Dict
    ) -> FleetSnapshot:
        """Create a FleetSnapshot object from buffer data.

        Args:
            buffer_key: (region_id, system_id, timestamp_bucket)
            buffer_data: Aggregated data from buffer

        Returns:
            FleetSnapshot instance ready for database insertion
        """
        region_id, system_id, timestamp_bucket = buffer_key

        # Convert ship counts to ShipEntry list
        ships = [
            ShipEntry(type_id=type_id, count=count)
            for type_id, count in buffer_data["ships"].items()
        ]

        # Sort by count descending (most common ships first)
        ships.sort(key=lambda s: s.count, reverse=True)

        return FleetSnapshot(
            timestamp=timestamp_bucket,
            system_id=system_id,
            region_id=region_id,
            ships=ships,
            total_pilots=buffer_data["total_pilots"],
            killmail_ids=buffer_data["killmail_ids"],
            created_at=datetime.now()
        )

    async def save_snapshot(self, snapshot: FleetSnapshot) -> Optional[int]:
        """Save a fleet snapshot to the database.

        Args:
            snapshot: FleetSnapshot to save

        Returns:
            Inserted snapshot ID or None on failure
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Convert ships list to JSONB format
                    ships_json = [
                        {"type_id": ship.type_id, "count": ship.count}
                        for ship in snapshot.ships
                    ]

                    cur.execute("""
                        INSERT INTO doctrine_fleet_snapshots
                            (timestamp, system_id, region_id, ships, total_pilots, killmail_ids, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        snapshot.timestamp,
                        snapshot.system_id,
                        snapshot.region_id,
                        psycopg2.extras.Json(ships_json),
                        snapshot.total_pilots,
                        snapshot.killmail_ids,
                        snapshot.created_at
                    ))

                    row = cur.fetchone()
                    conn.commit()

                    snapshot_id = row[0] if row else None
                    if snapshot_id:
                        print(f"[SNAPSHOT] Saved snapshot {snapshot_id}: "
                              f"{snapshot.total_pilots} pilots, {len(snapshot.ships)} ship types, "
                              f"system={snapshot.system_id}, time={snapshot.timestamp}")

                    return snapshot_id

        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return None

    async def flush_old_snapshots(self, current_time: datetime) -> int:
        """Flush snapshots from buffer that are older than current window.

        Args:
            current_time: Current timestamp (snapshots before this window are flushed)

        Returns:
            Number of snapshots flushed
        """
        current_bucket = self.get_timestamp_bucket(current_time)

        # Find snapshots to flush (all buckets before current)
        to_flush = []
        for buffer_key, buffer_data in list(self.buffer.items()):  # Use list() to avoid RuntimeError
            _, _, timestamp_bucket = buffer_key

            # Only flush if bucket is strictly before current
            if timestamp_bucket < current_bucket:
                # Apply minimum fleet size filter
                if buffer_data["total_pilots"] >= self.min_fleet_size:
                    to_flush.append((buffer_key, buffer_data))

        # Flush snapshots
        flushed_count = 0
        for buffer_key, buffer_data in to_flush:
            # Check if key still exists (concurrent flush protection)
            if buffer_key not in self.buffer:
                continue

            snapshot = self.create_snapshot_from_buffer(buffer_key, buffer_data)
            snapshot_id = await self.save_snapshot(snapshot)

            if snapshot_id:
                flushed_count += 1

            # Remove from buffer (only if still exists)
            if buffer_key in self.buffer:
                del self.buffer[buffer_key]

        return flushed_count

    async def receive_kill(self, kill: Dict) -> None:
        """Hook method to receive kills from zkillboard service.

        This is the main integration point. The zkillboard live service
        should call this method for each processed kill.

        Args:
            kill: Killmail dict from zkillboard
        """
        # Buffer the kill
        self.buffer_kill(kill)

        # Auto-flush old snapshots
        current_time = datetime.now()
        await self.flush_old_snapshots(current_time)


# Global singleton instance
_collector_instance: Optional[FleetSnapshotCollector] = None


def get_collector() -> FleetSnapshotCollector:
    """Get the global FleetSnapshotCollector instance.

    Returns:
        FleetSnapshotCollector singleton
    """
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = FleetSnapshotCollector()
    return _collector_instance
