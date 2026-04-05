"""Thera routing models."""
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class ShipSize(str, Enum):
    """Wormhole ship size classes."""
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"
    CAPITAL = "capital"


class SecurityClass(str, Enum):
    """System security classification."""
    HIGHSEC = "hs"
    LOWSEC = "ls"
    NULLSEC = "ns"
    WORMHOLE = "wh"


class HubType(str, Enum):
    """Wormhole hub types."""
    THERA = "thera"
    TURNUR = "turnur"
    ALL = "all"


class SystemInfo(BaseModel):
    """Basic system information."""
    system_id: int
    system_name: str
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    security_class: Optional[str] = None
    security_status: Optional[float] = None


class TheraConnection(BaseModel):
    """A single Thera/Turnur wormhole connection."""
    id: str
    wh_type: str
    max_ship_size: str
    remaining_hours: int
    expires_at: datetime

    # Hub side (Thera or Turnur)
    out_system_id: int
    out_system_name: str
    out_signature: str

    # K-Space destination
    in_system_id: int
    in_system_name: str
    in_system_class: str
    in_region_id: int
    in_region_name: str
    in_signature: Optional[str] = None

    # Metadata
    completed: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def supports_ship_size(self, size: str) -> bool:
        """Check if this connection supports the given ship size."""
        size_order = ["medium", "large", "xlarge", "capital"]
        try:
            required_idx = size_order.index(size.lower())
            connection_idx = size_order.index(self.max_ship_size.lower())
            return connection_idx >= required_idx
        except ValueError:
            return False


class TheraRouteSegment(BaseModel):
    """A route segment through Thera."""
    entry_connection: TheraConnection
    exit_connection: TheraConnection
    entry_jumps: int = Field(description="Jumps from origin to entry WH")
    exit_jumps: int = Field(description="Jumps from exit WH to destination")
    total_jumps: int = Field(description="Total jumps including Thera transit")


class RouteSavings(BaseModel):
    """Route comparison savings."""
    jumps_saved: int
    percentage: float = Field(description="Percentage of jumps saved")
    estimated_time_saved_minutes: Optional[float] = None


class TheraRoute(BaseModel):
    """Complete Thera route calculation result."""
    origin: SystemInfo
    destination: SystemInfo
    direct_jumps: int
    thera_route: Optional[TheraRouteSegment] = None
    savings: RouteSavings
    recommended: str = Field(description="'direct' or 'thera'")


class TheraConnectionList(BaseModel):
    """List of active Thera connections."""
    count: int
    hub: str
    last_updated: datetime
    connections: list[TheraConnection]


class TheraStatus(BaseModel):
    """Thera service status."""
    status: str = "healthy"
    thera_connections: int = 0
    turnur_connections: int = 0
    cache_age_seconds: Optional[int] = None
    last_fetch: Optional[datetime] = None
    eve_scout_reachable: bool = True
