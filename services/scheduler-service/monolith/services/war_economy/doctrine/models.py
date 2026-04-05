"""Data models for doctrine detection engine.

This module provides Pydantic models for:
- FleetSnapshot: Aggregated killmail data in 5-minute windows
- DoctrineTemplate: Detected doctrine patterns from DBSCAN clustering
- ItemOfInterest: Market items derived from doctrine ship compositions
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ShipEntry(BaseModel):
    """Single ship type entry in fleet snapshot."""
    type_id: int
    count: int


class FleetSnapshot(BaseModel):
    """Fleet composition snapshot from zkillboard data.

    Represents a 5-minute aggregation window of killmails from the same
    system/region, used as input for DBSCAN clustering to detect doctrines.
    """

    id: Optional[int] = None
    timestamp: datetime
    system_id: int
    region_id: int
    ships: List[ShipEntry]  # [{"type_id": 11190, "count": 12}, ...]
    total_pilots: int
    killmail_ids: List[int]
    created_at: datetime

    def normalize_vector(self) -> Dict[str, float]:
        """Normalize ship composition to unit vector for cosine similarity.

        Converts absolute ship counts to proportions, then normalizes to
        unit magnitude for DBSCAN distance metric calculation.

        Returns:
            Dict mapping type_id to normalized proportion (0.0-1.0)

        Example:
            ships = [{"type_id": 11190, "count": 12}, {"type_id": 638, "count": 8}]
            total_pilots = 20
            normalized = {"11190": 0.6, "638": 0.4}
            magnitude = sqrt(0.6^2 + 0.4^2) ≈ 0.7211
            final = {"11190": 0.832, "638": 0.555}  # Unit vector
        """
        if self.total_pilots == 0:
            return {}

        # Convert ships list to dict for processing
        ships_dict = {str(entry.type_id): entry.count for entry in self.ships}

        # Step 1: Convert to proportions
        proportions = {
            type_id: count / self.total_pilots
            for type_id, count in ships_dict.items()
        }

        # Step 2: Calculate magnitude
        magnitude = sum(v ** 2 for v in proportions.values()) ** 0.5

        if magnitude == 0:
            return {}

        # Step 3: Normalize to unit vector
        return {
            type_id: proportion / magnitude
            for type_id, proportion in proportions.items()
        }


class DoctrineTemplate(BaseModel):
    """Detected doctrine pattern from DBSCAN clustering.

    Represents a statistically significant fleet composition pattern
    observed multiple times in zkillboard data. Used for market intelligence
    to identify which items are likely to be consumed in upcoming battles.
    """

    id: Optional[int] = None
    doctrine_name: str = "Unnamed Doctrine"
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None  # ESI alliance name
    region_id: Optional[int] = None
    region_name: Optional[str] = None  # SDE region name
    composition: Dict[str, float]  # {"type_id": normalized_ratio}
    composition_with_names: Optional[List[Dict[str, Any]]] = None  # [{"type_id": id, "type_name": name, "ratio": float}]
    confidence_score: float = 0.0
    observation_count: int = 0
    first_seen: datetime
    last_seen: datetime
    total_pilots_avg: Optional[int] = None
    primary_doctrine_type: Optional[str] = None  # 'subcap', 'capital', 'supercap'
    created_at: datetime
    updated_at: datetime

    def update_from_observation(
        self,
        composition: Dict[str, float],
        timestamp: datetime,
        pilot_count: int
    ) -> None:
        """Update doctrine template from new snapshot observation.

        Implements rolling average for composition, increases confidence score,
        updates temporal bounds, and recalculates average pilot count.

        Args:
            composition: Normalized ship composition from new snapshot
            timestamp: When this observation occurred
            pilot_count: Number of pilots in this observation
        """
        # Increment observation count
        self.observation_count += 1

        # Update temporal bounds
        self.last_seen = timestamp

        # Update average pilot count (rolling average)
        if self.total_pilots_avg is None:
            self.total_pilots_avg = pilot_count
        else:
            # Weighted rolling average
            total_count = self.observation_count
            self.total_pilots_avg = int(
                ((self.total_pilots_avg * (total_count - 1)) + pilot_count)
                / total_count
            )

        # Update composition (weighted rolling average)
        # Weight new observation: 0.3, existing: 0.7 (decay factor)
        new_composition = {}
        all_type_ids = set(self.composition.keys()) | set(composition.keys())

        for type_id in all_type_ids:
            existing_ratio = self.composition.get(type_id, 0.0)
            new_ratio = composition.get(type_id, 0.0)
            # Weighted average: 70% existing, 30% new
            updated_ratio = (existing_ratio * 0.7) + (new_ratio * 0.3)
            if updated_ratio > 0.01:  # Filter out noise below 1%
                new_composition[type_id] = updated_ratio

        self.composition = new_composition

        # Update confidence score (increases with observations, caps at 1.0)
        # Formula: 1 - (1 / sqrt(observation_count))
        self.confidence_score = min(
            1.0,
            1.0 - (1.0 / (self.observation_count ** 0.5))
        )

        # Update timestamp
        self.updated_at = datetime.now()


class ItemOfInterest(BaseModel):
    """Market item derived from doctrine ship composition.

    Represents ammunition, fuel, or modules that are likely to be consumed
    based on the ships in a detected doctrine. Used for market tracking.
    """

    id: Optional[int] = None
    doctrine_id: int
    type_id: int
    item_name: Optional[str] = None
    item_category: str  # 'ammunition', 'fuel', 'module'
    consumption_rate: Optional[float] = None
    priority: int = 2  # 1=critical, 2=high, 3=medium
    created_at: datetime

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Ensure priority is within valid range 1-3."""
        if not 1 <= v <= 3:
            raise ValueError("Priority must be between 1 and 3")
        return v
