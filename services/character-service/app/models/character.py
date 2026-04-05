"""Character data models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class WalletBalance(BaseModel):
    """Character wallet balance."""
    character_id: int
    balance: float
    formatted: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        self.formatted = f"{self.balance:,.2f} ISK"


class Asset(BaseModel):
    """Character asset item."""
    item_id: int
    type_id: int
    type_name: str = "Unknown"
    group_id: int = 0
    group_name: str = "Unknown"
    category_id: int = 0
    category_name: str = "Unknown"
    location_id: int
    location_name: str = "Unknown"
    quantity: int = 1
    is_singleton: bool = False
    location_flag: Optional[str] = None
    location_type: Optional[str] = None


class AssetList(BaseModel):
    """Character asset list."""
    character_id: int
    total_items: int
    assets: List[Asset]


class ValuedAsset(BaseModel):
    """Character asset item with market valuation."""
    item_id: int
    type_id: int
    type_name: str = "Unknown"
    group_id: int = 0
    group_name: str = "Unknown"
    category_id: int = 0
    category_name: str = "Unknown"
    location_id: int
    location_name: str = "Unknown"
    quantity: int = 1
    is_singleton: bool = False
    location_flag: Optional[str] = None
    location_type: Optional[str] = None
    unit_price: float = 0.0
    total_value: float = 0.0
    volume: float = 0.0
    total_volume: float = 0.0


class LocationSummary(BaseModel):
    """Asset location summary."""
    location_id: int
    location_name: str = "Unknown"
    location_type: Optional[str] = None
    total_value: float = 0.0
    total_volume: float = 0.0
    item_count: int = 0
    type_count: int = 0


class ValuedAssetList(BaseModel):
    """Character valued asset list with summaries."""
    character_id: int
    total_value: float = 0.0
    total_volume: float = 0.0
    total_items: int = 0
    total_types: int = 0
    location_summaries: List[LocationSummary] = []
    assets: List[ValuedAsset] = []


class Skill(BaseModel):
    """Character skill."""
    skill_id: int
    skill_name: str = "Unknown"
    level: int = 0
    trained_level: int = 0
    skillpoints: int = 0
    group_name: str = "Unknown"


class SkillData(BaseModel):
    """Character skills data."""
    character_id: int
    total_sp: int = 0
    unallocated_sp: int = 0
    skill_count: int = 0
    skills: List[Skill] = []


class SkillQueueItem(BaseModel):
    """Skill queue entry."""
    skill_id: int
    skill_name: str = "Unknown"
    skill_description: str = ""
    finish_date: Optional[str] = None
    start_date: Optional[str] = None
    finished_level: int = 0
    queue_position: int = 0
    level_start_sp: int = 0
    level_end_sp: int = 0
    training_start_sp: int = 0
    sp_remaining: int = 0
    training_progress: float = 0.0


class SkillQueue(BaseModel):
    """Character skill queue."""
    character_id: int
    queue_length: int = 0
    queue: List[SkillQueueItem] = []


class MarketOrder(BaseModel):
    """Character market order."""
    order_id: int
    type_id: int
    type_name: str = "Unknown"
    is_buy_order: bool = False
    price: float = 0.0
    volume_total: int = 0
    volume_remain: int = 0
    location_id: int = 0
    location_name: str = "Unknown"
    region_id: int = 0
    issued: Optional[str] = None
    duration: int = 0
    min_volume: int = 1
    range_: str = Field(default="station", alias="range")


class MarketOrderList(BaseModel):
    """Character market orders."""
    character_id: int
    total_orders: int = 0
    buy_orders: int = 0
    sell_orders: int = 0
    orders: List[MarketOrder] = []


class IndustryJob(BaseModel):
    """Character industry job."""
    job_id: int
    activity_id: int
    blueprint_id: int
    blueprint_type_id: int
    blueprint_type_name: str = "Unknown"
    product_type_id: Optional[int] = None
    product_type_name: str = "Unknown"
    status: str
    runs: int = 1
    licensed_runs: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: int = 0
    station_id: int = 0
    station_name: str = "Unknown"
    cost: float = 0.0


class IndustryJobList(BaseModel):
    """Character industry jobs."""
    character_id: int
    total_jobs: int = 0
    active_jobs: int = 0
    jobs: List[IndustryJob] = []


class Blueprint(BaseModel):
    """Character blueprint."""
    item_id: int
    type_id: int
    type_name: str = "Unknown"
    location_id: int = 0
    location_name: str = "Unknown"
    quantity: int  # -1 = original, -2 = copy
    runs: int = -1  # -1 = unlimited (BPO)
    material_efficiency: int = 0
    time_efficiency: int = 0


class BlueprintList(BaseModel):
    """Character blueprints."""
    character_id: int
    total_blueprints: int = 0
    originals: int = 0
    copies: int = 0
    blueprints: List[Blueprint] = []


class CharacterInfo(BaseModel):
    """Public character information."""
    character_id: int
    name: str
    corporation_id: int
    alliance_id: Optional[int] = None
    birthday: Optional[str] = None
    security_status: float = 0.0
    title: Optional[str] = None
    description: Optional[str] = None


class CharacterLocation(BaseModel):
    """Character current location."""
    character_id: int
    solar_system_id: int
    solar_system_name: str = "Unknown"
    station_id: Optional[int] = None
    station_name: Optional[str] = None
    structure_id: Optional[int] = None


class CharacterShip(BaseModel):
    """Character current ship."""
    character_id: int
    ship_type_id: int
    ship_type_name: str = "Unknown"
    ship_item_id: int
    ship_name: str = ""


class CharacterAttributes(BaseModel):
    """Character attributes."""
    character_id: int
    perception: int = 20
    memory: int = 20
    willpower: int = 20
    intelligence: int = 20
    charisma: int = 19
    bonus_remaps: int = 0
    last_remap_date: Optional[str] = None
    accrued_remap_cooldown_date: Optional[str] = None


class Implant(BaseModel):
    """Character implant."""
    type_id: int
    type_name: str = "Unknown"
    slot: int = 1
    perception_bonus: int = 0
    memory_bonus: int = 0
    willpower_bonus: int = 0
    intelligence_bonus: int = 0
    charisma_bonus: int = 0


class CharacterImplants(BaseModel):
    """Character active implants."""
    character_id: int
    implants: List[Implant] = []


class WalletJournalEntry(BaseModel):
    """Wallet journal entry."""
    id: int
    date: str
    ref_type: str
    amount: float = 0.0
    balance: float = 0.0
    description: Optional[str] = None
    first_party_id: Optional[int] = None
    second_party_id: Optional[int] = None
    reason: Optional[str] = None
    context_id: Optional[int] = None
    context_id_type: Optional[str] = None


class WalletJournal(BaseModel):
    """Character wallet journal."""
    character_id: int
    entries: List[WalletJournalEntry] = []
    total_entries: int = 0


class WalletTransaction(BaseModel):
    """Wallet transaction."""
    transaction_id: int
    date: str
    type_id: int
    type_name: str = "Unknown"
    quantity: int = 0
    unit_price: float = 0.0
    is_buy: bool = False
    location_id: int = 0
    location_name: str = "Unknown"
    client_id: int = 0


class WalletTransactions(BaseModel):
    """Character wallet transactions."""
    character_id: int
    transactions: List[WalletTransaction] = []
    total_transactions: int = 0
