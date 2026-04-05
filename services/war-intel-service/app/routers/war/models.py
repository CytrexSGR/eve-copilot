"""
Pydantic models for War Intel API responses.

All models use CamelModel base class for automatic snake_case → camelCase
field aliasing in API responses.
"""

from datetime import datetime
from typing import Optional, List

from app.models.base import CamelModel


class BattleAllianceInfo(CamelModel):
    """Alliance participation in a battle."""
    alliance_id: int
    alliance_name: Optional[str] = None
    kill_count: int


class BattleSummary(CamelModel):
    """Battle summary response - compatible with ectmap format."""
    battle_id: int
    # Standard fields
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    started_at: datetime
    last_kill_at: datetime
    ended_at: Optional[datetime] = None
    total_kills: int
    total_isk_destroyed: float
    status: str
    status_level: str = "gank"  # gank, brawl, battle, hellcamp
    last_milestone: int = 0
    # Ectmap compatibility fields
    system_id: Optional[int] = None  # Alias for solar_system_id
    system_name: Optional[str] = None  # Alias for solar_system_name
    security: Optional[float] = None
    duration_minutes: Optional[int] = None
    telegram_sent: bool = False
    intensity: str = "low"  # extreme, high, moderate, low
    x: Optional[float] = None
    z: Optional[float] = None
    # Top alliances involved (attackers by kill count)
    top_alliances: Optional[List[BattleAllianceInfo]] = None


class KillmailSummary(CamelModel):
    """Killmail summary response."""
    killmail_id: int
    killmail_time: datetime
    solar_system_id: int
    ship_type_id: int
    ship_name: Optional[str] = None
    victim_name: Optional[str] = None
    victim_corporation_id: Optional[int] = None
    victim_corporation_name: Optional[str] = None
    victim_alliance_id: Optional[int] = None
    victim_alliance_name: Optional[str] = None
    coalition_id: Optional[int] = None
    coalition_name: Optional[str] = None
    ship_value: float
    attacker_count: int


class ActiveBattleInfo(CamelModel):
    """Active battle in a system."""
    battle_id: int
    total_kills: int
    total_isk_destroyed: float
    started_at: str


class SystemDanger(CamelModel):
    """System danger level response."""
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_name: Optional[str] = None
    constellation_name: Optional[str] = None
    security: Optional[float] = None
    sov_alliance_id: Optional[int] = None
    sov_alliance_name: Optional[str] = None
    danger_score: float
    kills_1h: int = 0
    kills_24h: int
    capital_kills: int
    isk_destroyed_24h: float = 0.0
    gate_camp_risk: float
    active_battles: List[ActiveBattleInfo] = []


class ActiveBattlesResponse(CamelModel):
    """Active battles response with metadata."""
    battles: List[BattleSummary]
    total_active: int


class AllianceInfo(CamelModel):
    """Alliance information for Telegram alerts."""
    alliance_id: int
    alliance_name: str
    kills: Optional[int] = None
    losses: Optional[int] = None


class TelegramAlert(CamelModel):
    """Telegram alert information."""
    battle_id: int
    system_name: str
    region_name: str
    security: float
    alert_type: str
    milestone: int
    total_kills: int
    total_isk_destroyed: float
    telegram_message_id: int
    sent_at: datetime
    status: str
    attackers: Optional[List[AllianceInfo]] = None
    victims: Optional[List[AllianceInfo]] = None


# Coalition Conflict Models

class CoalitionInfo(CamelModel):
    """Coalition information in a conflict."""
    leader_id: int
    leader_name: str
    leader_ticker: str
    member_count: int  # alliances active in this conflict
    kills: int
    losses: int
    isk_destroyed: float
    isk_lost: float
    efficiency: float  # isk_destroyed / (isk_destroyed + isk_lost) as percentage


class ConflictBattle(CamelModel):
    """A battle within a conflict."""
    battle_id: int
    system_name: str
    region_name: str
    status_level: str  # gank, brawl, battle, hellcamp
    total_kills: int
    total_isk: float
    last_kill_at: str
    minutes_ago: int


class ConflictHighValueKill(CamelModel):
    """A high-value kill within a conflict."""
    killmail_id: int
    ship_name: str
    ship_type_id: int
    value: float
    victim_alliance_ticker: str
    attacker_alliance_ticker: str


class Conflict(CamelModel):
    """A conflict between two coalitions."""
    conflict_id: str  # "{coalition_a_id}_{coalition_b_id}"
    coalition_a: CoalitionInfo
    coalition_b: CoalitionInfo
    regions: List[str]
    total_kills: int
    total_isk: float
    capital_kills: int
    last_kill_at: Optional[str] = None
    started_at: Optional[str] = None
    time_status: str  # '10m', '1h', '12h', '24h', '7d'
    trend: str  # 'escalating', 'stable', 'cooling'
    battles: List[ConflictBattle]
    high_value_kills: List[ConflictHighValueKill]


class ConflictsResponse(CamelModel):
    """Response for /api/war/conflicts endpoint."""
    filter_minutes: int
    conflicts: List[Conflict]
    total_battles: int
    total_kills: int
    error: Optional[str] = None
