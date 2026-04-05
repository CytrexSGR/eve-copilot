"""Battle Event Models and Types."""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class BattleEventSeverity(str, Enum):
    """Event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BattleEventType(str, Enum):
    """Battle event types."""
    # Critical
    TITAN_KILLED = "titan_killed"
    SUPERCARRIER_KILLED = "supercarrier_killed"

    # High
    HOT_ZONE_SHIFT = "hot_zone_shift"
    WAR_ESCALATION = "war_escalation"
    CAPITAL_KILLED = "capital_killed"
    ISK_SPIKE = "isk_spike"

    # Medium
    NEW_CONFLICT = "new_conflict"
    ALLIANCE_ENGAGEMENT = "alliance_engagement"
    EFFICIENCY_CHANGE = "efficiency_change"
    LAST_TITAN = "last_titan"
    LAST_SUPERCARRIER = "last_supercarrier"

    # Low
    REGIONAL_ACTIVITY = "regional_activity"
    DREAD_KILLED = "dread_killed"
    CARRIER_KILLED = "carrier_killed"
    FAX_KILLED = "fax_killed"


# Mapping of event types to severity
EVENT_SEVERITY_MAP: Dict[BattleEventType, BattleEventSeverity] = {
    BattleEventType.TITAN_KILLED: BattleEventSeverity.CRITICAL,
    BattleEventType.SUPERCARRIER_KILLED: BattleEventSeverity.CRITICAL,
    BattleEventType.HOT_ZONE_SHIFT: BattleEventSeverity.HIGH,
    BattleEventType.WAR_ESCALATION: BattleEventSeverity.HIGH,
    BattleEventType.CAPITAL_KILLED: BattleEventSeverity.HIGH,
    BattleEventType.ISK_SPIKE: BattleEventSeverity.HIGH,
    BattleEventType.NEW_CONFLICT: BattleEventSeverity.MEDIUM,
    BattleEventType.ALLIANCE_ENGAGEMENT: BattleEventSeverity.MEDIUM,
    BattleEventType.EFFICIENCY_CHANGE: BattleEventSeverity.MEDIUM,
    BattleEventType.LAST_TITAN: BattleEventSeverity.MEDIUM,
    BattleEventType.LAST_SUPERCARRIER: BattleEventSeverity.MEDIUM,
    BattleEventType.REGIONAL_ACTIVITY: BattleEventSeverity.LOW,
    BattleEventType.DREAD_KILLED: BattleEventSeverity.LOW,
    BattleEventType.CARRIER_KILLED: BattleEventSeverity.LOW,
    BattleEventType.FAX_KILLED: BattleEventSeverity.LOW,
}


class BattleEvent(BaseModel):
    """A detected battle event."""
    model_config = ConfigDict(use_enum_values=True)

    id: Optional[int] = None
    event_type: BattleEventType
    severity: BattleEventSeverity
    title: str = Field(..., max_length=200)
    description: Optional[str] = None

    # Related entities
    system_id: Optional[int] = None
    system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None

    # Flexible event data
    event_data: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    event_time: Optional[datetime] = None

    # Deduplication
    event_hash: Optional[str] = None


class BattleEventResponse(BaseModel):
    """API response for battle events."""
    events: List[BattleEvent]
    total: int
    since: Optional[datetime] = None
