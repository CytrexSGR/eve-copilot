"""
Planetary Industry (PI) Models
Pydantic models for PI schematics, production chains, profitability, and colony management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from eve_shared.constants import JITA_REGION_ID


class PISchematicInput(BaseModel):
    """Input material for a PI schematic."""

    type_id: int
    type_name: str
    quantity: int


class PISchematic(BaseModel):
    """PI production schematic (recipe)."""

    schematic_id: int
    schematic_name: str
    cycle_time: int  # seconds
    tier: int  # 1-4 (P1-P4)
    inputs: List[PISchematicInput]
    output_type_id: int
    output_name: str
    output_quantity: int


class PIChainNode(BaseModel):
    """Node in a PI production chain tree."""

    type_id: int
    type_name: str
    tier: int  # 0-4 (P0 raw to P4 advanced)
    quantity_needed: float
    schematic_id: Optional[int] = None
    children: List["PIChainNode"] = []


class PIProfitability(BaseModel):
    """Profitability analysis for a PI product."""

    type_id: int
    type_name: str
    tier: int
    schematic_id: int
    input_cost: float
    output_value: float
    profit_per_run: float
    profit_per_hour: float
    roi_percent: float
    cycle_time: int  # seconds


class PIColony(BaseModel):
    """Character PI colony."""

    id: int
    character_id: int
    planet_id: int
    planet_type: str
    solar_system_id: int
    solar_system_name: Optional[str] = None
    upgrade_level: int
    num_pins: int
    last_update: Optional[datetime] = None
    last_sync: datetime


class PIPin(BaseModel):
    """Building (pin) on a PI colony."""

    pin_id: int
    type_id: int
    type_name: Optional[str] = None
    schematic_id: Optional[int] = None
    schematic_name: Optional[str] = None
    product_type_id: Optional[int] = None
    product_name: Optional[str] = None
    expiry_time: Optional[datetime] = None
    qty_per_cycle: Optional[int] = None
    cycle_time: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PIRoute(BaseModel):
    """Material route between pins."""

    route_id: int
    source_pin_id: int
    destination_pin_id: int
    content_type_id: int
    content_name: Optional[str] = None
    quantity: int


class PIColonyDetail(BaseModel):
    """Colony with full pin and route details."""

    colony: PIColony
    pins: List[PIPin]
    routes: List[PIRoute]


class PICharacterSummary(BaseModel):
    """Summary of character's PI operations."""

    character_id: int
    character_name: str
    total_colonies: int
    active_extractors: int
    active_factories: int
    products: List[dict]  # {type_id, type_name, quantity_per_day}
    expiring_soon: List[dict]  # Extractors expiring within 24h


class PICharacterSkills(BaseModel):
    """Character PI skills from ESI."""

    character_id: int
    interplanetary_consolidation: int = 0  # Skill ID 2495
    command_center_upgrades: int = 0       # Skill ID 2505
    max_planets: int = 1                   # 1 + interplanetary_consolidation
    updated_at: Optional[datetime] = None


class PISystemPlanet(BaseModel):
    """Planet in a system for PI optimization."""

    planet_id: int
    system_id: int
    system_name: str
    planet_type: str
    planet_index: int


class PICharacterSlots(BaseModel):
    """Character slot availability for PI optimizer."""

    character_id: int
    character_name: str
    max_planets: int
    used_planets: int
    free_planets: int


class PIRecommendation(BaseModel):
    """PI production recommendation from optimizer."""

    type_id: int
    type_name: str
    tier: int
    profit_per_hour: float
    roi_percent: float
    required_planet_types: List[str]
    planets_needed: int
    complexity_score: int  # 1-5 scale
    feasible: bool
    reason: Optional[str] = None


class PIProjectCreate(BaseModel):
    """Request model for creating a PI project."""

    character_id: int
    name: str
    strategy: str = "market_driven"  # 'market_driven' or 'vertical'
    target_product_type_id: Optional[int] = None
    target_profit_per_hour: Optional[float] = None


class PIProject(BaseModel):
    """PI optimization project."""

    project_id: int
    character_id: int
    name: str
    strategy: str  # 'market_driven' or 'vertical'
    target_product_type_id: Optional[int] = None
    target_profit_per_hour: Optional[float] = None
    status: str  # 'planning', 'active', 'paused', 'completed'
    created_at: datetime
    updated_at: datetime


class PIProjectListItem(BaseModel):
    """PI project with computed fields for list view."""

    project_id: int
    character_id: int
    character_name: Optional[str] = None
    name: str
    target_product_type_id: Optional[int] = None
    target_product_name: Optional[str] = None
    target_tier: Optional[int] = None
    status: str  # 'planning', 'active', 'paused', 'completed'
    created_at: datetime
    assigned_count: int = 0
    total_materials: int = 0


class PIProjectColony(BaseModel):
    """Colony assignment within a PI project."""

    id: int
    project_id: int
    planet_id: int
    role: Optional[str] = None
    expected_output_type_id: Optional[int] = None
    expected_output_per_hour: Optional[float] = None
    actual_output_per_hour: Optional[float] = None
    last_sync: Optional[datetime] = None


class PIMaterialAssignment(BaseModel):
    """Material to colony assignment within a PI project."""

    id: int
    project_id: int
    material_type_id: int
    material_name: Optional[str] = None
    tier: int
    colony_id: Optional[int] = None
    colony_name: Optional[str] = None
    planet_type: Optional[str] = None
    status: str = "unassigned"  # 'active', 'planned', 'unassigned'
    is_auto_assigned: bool = True
    # Output tracking fields (from ESI sync)
    actual_output_per_hour: Optional[float] = None
    expected_output_per_hour: Optional[float] = None
    output_percentage: Optional[int] = None
    # SOLL planning fields (user-defined targets)
    soll_output_per_hour: Optional[float] = None
    soll_notes: Optional[str] = None
    soll_variance_percent: Optional[float] = None  # Computed: (actual - soll) / soll * 100


class PIMaterialAssignmentUpdate(BaseModel):
    """Request model for updating a material assignment."""

    colony_id: Optional[int] = None


class PIMaterialAssignmentSollUpdate(BaseModel):
    """Request model for updating SOLL planning values."""

    soll_output_per_hour: Optional[float] = None
    soll_notes: Optional[str] = None


class PIProjectDetail(BaseModel):
    """Project with full colony details and tracking metrics."""

    project: PIProject
    colonies: List[PIProjectColony]
    total_expected_output: float
    total_actual_output: float
    variance_percent: float
    expiring_extractors: int


class PIProjectSollSummary(BaseModel):
    """SOLL vs IST summary for a project."""

    project_id: int
    total_soll_output: float
    total_ist_output: float
    overall_variance_percent: float
    materials_on_target: int      # variance within +/- 10%
    materials_under_target: int   # variance < -10%
    materials_over_target: int    # variance > +10%
    materials_no_soll: int        # no SOLL defined


class MakeOrBuyRecommendation(str, Enum):
    """Recommendation for make-or-buy decision."""
    MAKE = "MAKE"
    BUY = "BUY"


class MakeOrBuyResult(BaseModel):
    """Result of make-or-buy analysis for a PI product."""

    type_id: int
    type_name: str
    tier: int  # 1-4 (P1-P4)
    quantity: int
    market_price: float  # Cost to buy from market
    make_cost: float  # Cost to produce from direct inputs
    recommendation: MakeOrBuyRecommendation
    savings_isk: float  # Absolute savings
    savings_percent: float  # Percentage savings
    inputs: List[PISchematicInput]  # Direct schematic inputs with quantities
    p0_cost: Optional[float] = None  # Full P0 chain cost (optional)


# ==================== Empire Models ====================


class EmpireConfiguration(BaseModel):
    """Configuration for empire-scale PI analysis."""

    total_planets: int = 18
    extraction_planets: int = 12
    factory_planets: int = 6
    characters: int = 3
    poco_tax_rate: float = 0.10
    region_id: int = JITA_REGION_ID


class EmpirePlanetNeed(BaseModel):
    """Planet type requirements for empire production."""

    planet_type: str
    count_needed: int
    p0_materials: List[str]


class P4EmpireProfitability(BaseModel):
    """P4 product profitability at empire scale."""

    type_id: int
    type_name: str
    tier: int = 4
    monthly_output: int
    sell_price: float
    monthly_revenue: float
    monthly_costs: dict  # {poco_tax, import_tax, total}
    monthly_profit: float
    profit_per_planet: float
    roi_percent: float
    complexity: str  # 'low', 'medium', 'high'
    logistics_score: int  # 1-10
    p0_count: int
    planets_needed: dict  # {extraction: {planet_type: count}, factory: {...}}
    recommendation: str  # 'excellent', 'good', 'fair', 'poor'


class EmpireProfitabilityResponse(BaseModel):
    """Response for empire profitability analysis."""

    configuration: EmpireConfiguration
    products: List[P4EmpireProfitability]
    comparison: dict  # {best_profit, best_passive, best_balanced}


class EmpirePlanCreate(BaseModel):
    """Request model for creating an empire plan."""

    name: str = Field(..., min_length=1, max_length=255)
    target_product_id: int = Field(..., gt=0)
    target_product_name: Optional[str] = None
    home_system_id: Optional[int] = Field(None, gt=0)
    home_system_name: Optional[str] = None
    total_planets: int = Field(default=18, ge=6, le=36)
    extraction_planets: int = Field(default=12, ge=0, le=30)
    factory_planets: int = Field(default=6, ge=0, le=18)
    poco_tax_rate: float = Field(default=0.10, ge=0.0, le=1.0)


class EmpirePlanAssignmentCreate(BaseModel):
    """Request model for adding character assignment."""

    character_id: int
    character_name: str
    role: str = "extractor"  # 'extractor', 'factory', 'hybrid'
    planets: List[dict] = []


class EmpirePlanAssignment(BaseModel):
    """Character assignment within an empire plan."""

    id: int
    plan_id: int
    character_id: int
    character_name: Optional[str] = None
    role: str = "extractor"  # 'extractor', 'factory', 'hybrid'
    planets: List[dict] = []  # JSONB planets config


class EmpirePlan(BaseModel):
    """Complete empire plan with character assignments."""

    plan_id: int
    name: str
    target_product: dict  # {id, name}
    status: str
    character_assignments: List[EmpirePlanAssignment]
    material_flow: List[dict] = []  # [{from_char, to_char, material, quantity}]
    estimated_monthly_output: Optional[int] = None
    estimated_monthly_profit: Optional[float] = None
    created_at: datetime


# ==================== Logistics Models ====================


class PIPickupStop(BaseModel):
    """Single stop in a pickup route."""

    character_id: int
    character_name: str
    system_id: int
    system_name: str
    planets: int
    estimated_time_minutes: int
    materials_volume_m3: float


class PIPickupSchedule(BaseModel):
    """Optimized pickup schedule for PI empire."""

    optimal_frequency_hours: int
    next_pickup: Optional[datetime] = None
    route: List[PIPickupStop]
    total_time_minutes: int
    total_jumps: int
    total_cargo_volume_m3: float


class PITransfer(BaseModel):
    """Cross-character material transfer."""

    id: int
    from_character_id: int
    from_character_name: str
    to_character_id: int
    to_character_name: str
    materials: List[Dict]  # [{type_id, type_name, quantity, volume_m3}]
    total_volume_m3: float
    method: str  # 'contract', 'direct_trade', 'corp_hangar'
    station_id: Optional[int] = None
    station_name: Optional[str] = None
    frequency_hours: int = 48


class PIHubStation(BaseModel):
    """Recommended hub station for transfers."""

    station_id: int
    station_name: str
    system_id: int
    system_name: str
    security: float
    avg_jumps_to_colonies: float
    reason: str


class PILogisticsPlan(BaseModel):
    """Complete logistics plan for an empire."""

    plan_id: int
    pickup_schedule: PIPickupSchedule
    transfers: List[PITransfer]
    hub_station: PIHubStation
    estimated_weekly_trips: int
    estimated_weekly_time_hours: float


# ==================== Planet Recommendation Models ====================


class PlanetInfo(BaseModel):
    """Basic planet information."""

    planet_id: int
    planet_name: str
    planet_type: str
    system_id: int
    system_name: str
    security: float
    jumps_from_home: int = 0
    resources: List[str] = []


class PlanetRecommendationItem(BaseModel):
    """Planet recommendation with scoring."""

    planet_id: int
    planet_name: str
    planet_type: str
    system_id: int
    system_name: str
    security: float
    jumps_from_home: int
    resources: List[str]
    recommendation_score: float
    reason: str


class PlanetRecommendationResponse(BaseModel):
    """Response for planet recommendation endpoint."""

    search_center: str
    search_radius: int
    systems_searched: int
    planets_found: int
    recommendations: List[PlanetRecommendationItem]
    by_planet_type: dict  # {planet_type: count}
    by_resource: dict  # {resource_name: [planet_names]}


# ==================== Multi-Character Overview Models ====================


class PIExtractorStatus(BaseModel):
    """Extractor status for multi-character overview."""

    character_id: int
    character_name: str
    planet_id: int
    planet_name: str
    planet_type: str
    product_type_id: int
    product_name: str
    qty_per_cycle: int
    cycle_time: int
    expiry_time: Optional[datetime] = None
    hours_remaining: Optional[float] = None
    status: str  # 'active', 'expiring', 'stopped'


class PIAlert(BaseModel):
    """Alert for PI operations."""

    type: str  # 'extractor_depleting', 'extractor_stopped', 'storage_full'
    severity: str  # 'warning', 'critical'
    character_id: int
    character_name: str
    planet_name: str
    message: str
    expiry_time: Optional[datetime] = None


class PIMultiCharacterDetail(BaseModel):
    """Extended multi-character PI detail with extractors and alerts."""

    summary: dict  # Existing summary structure
    extractors: List[PIExtractorStatus]
    alerts: List[PIAlert]


# ==================== PI Alert Models ====================


class PIAlertType(str, Enum):
    """Types of PI alerts."""
    EXTRACTOR_DEPLETING = "extractor_depleting"
    EXTRACTOR_STOPPED = "extractor_stopped"
    STORAGE_FULL = "storage_full"
    STORAGE_ALMOST_FULL = "storage_almost_full"
    FACTORY_IDLE = "factory_idle"
    PICKUP_REMINDER = "pickup_reminder"


class PIAlertSeverity(str, Enum):
    """Alert severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"


class PIAlertLog(BaseModel):
    """Logged PI alert."""

    id: int
    character_id: int
    alert_type: str
    severity: str
    planet_id: Optional[int] = None
    planet_name: Optional[str] = None
    pin_id: Optional[int] = None
    product_type_id: Optional[int] = None
    product_name: Optional[str] = None
    message: str
    details: Optional[Dict] = None
    is_read: bool = False
    is_acknowledged: bool = False
    discord_sent: bool = False
    created_at: datetime
    expires_at: Optional[datetime] = None


class PIAlertConfig(BaseModel):
    """Per-character PI alert configuration."""

    character_id: int
    discord_webhook_url: Optional[str] = None
    discord_enabled: bool = True
    extractor_warning_hours: int = 12
    extractor_critical_hours: int = 4
    storage_warning_percent: int = 75
    storage_critical_percent: int = 90
    alert_extractor_depleting: bool = True
    alert_extractor_stopped: bool = True
    alert_storage_full: bool = True
    alert_factory_idle: bool = True
    alert_pickup_reminder: bool = True
    pickup_reminder_hours: int = 48


class PIAlertConfigUpdate(BaseModel):
    """Update model for PI alert configuration."""

    discord_webhook_url: Optional[str] = None
    discord_enabled: Optional[bool] = None
    extractor_warning_hours: Optional[int] = None
    extractor_critical_hours: Optional[int] = None
    storage_warning_percent: Optional[int] = None
    storage_critical_percent: Optional[int] = None
    alert_extractor_depleting: Optional[bool] = None
    alert_extractor_stopped: Optional[bool] = None
    alert_storage_full: Optional[bool] = None
    alert_factory_idle: Optional[bool] = None
    alert_pickup_reminder: Optional[bool] = None
    pickup_reminder_hours: Optional[int] = None


class PIMonitoringStatus(BaseModel):
    """Status from PI monitoring job."""

    characters_checked: int
    colonies_checked: int
    alerts_generated: int
    alerts_by_type: Dict[str, int]
    discord_notifications_sent: int
    duration_ms: int
    timestamp: datetime


# Enable forward reference resolution for recursive PIChainNode
PIChainNode.model_rebuild()
