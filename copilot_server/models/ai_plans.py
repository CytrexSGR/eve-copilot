# copilot_server/models/ai_plans.py
"""
Pydantic models for AI Copilot persistence layer.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class GoalType(str, Enum):
    SHIP = "ship"
    ISK = "isk"
    SKILL = "skill"
    PRODUCTION = "production"
    PI = "pi"
    CUSTOM = "custom"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TrackingType(str, Enum):
    SKILL = "skill"
    WALLET = "wallet"
    SHOPPING_LIST = "shopping_list"
    LEDGER = "ledger"
    PI_PROJECT = "pi_project"
    MANUAL = "manual"
    ESI = "esi"


class ResourceType(str, Enum):
    SHOPPING_LIST = "shopping_list"
    LEDGER = "ledger"
    PI_PROJECT = "pi_project"
    FITTING = "fitting"


# Request Models
class CreatePlanRequest(BaseModel):
    character_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    goal_type: GoalType
    target_data: dict = Field(default_factory=dict)
    target_date: Optional[datetime] = None


class UpdatePlanRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[PlanStatus] = None
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    target_date: Optional[datetime] = None


class CreateMilestoneRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sequence_order: int = 0
    tracking_type: Optional[TrackingType] = None
    tracking_config: dict = Field(default_factory=dict)
    target_value: Optional[float] = None


class UpdateMilestoneRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[MilestoneStatus] = None
    current_value: Optional[float] = None


class LinkResourceRequest(BaseModel):
    resource_type: ResourceType
    resource_id: int


class SetContextRequest(BaseModel):
    context_key: str = Field(..., min_length=1, max_length=100)
    context_value: Any
    source: str = "user_stated"
    expires_at: Optional[datetime] = None


class CreateSummaryRequest(BaseModel):
    session_id: str
    character_id: int
    summary: str
    key_decisions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    active_plan_ids: List[int] = Field(default_factory=list)


# Response Models
class MilestoneResponse(BaseModel):
    id: int
    plan_id: int
    title: str
    description: Optional[str]
    sequence_order: int
    tracking_type: Optional[TrackingType]
    tracking_config: dict
    target_value: Optional[float]
    current_value: float
    status: MilestoneStatus
    created_at: datetime
    completed_at: Optional[datetime]


class ResourceResponse(BaseModel):
    id: int
    plan_id: int
    resource_type: ResourceType
    resource_id: int
    created_at: datetime


class PlanResponse(BaseModel):
    id: int
    character_id: int
    title: str
    description: Optional[str]
    goal_type: GoalType
    target_data: dict
    target_date: Optional[datetime]
    status: PlanStatus
    progress_pct: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    milestones: List[MilestoneResponse] = Field(default_factory=list)
    resources: List[ResourceResponse] = Field(default_factory=list)


class PlanListResponse(BaseModel):
    plans: List[PlanResponse]
    total: int


class ContextResponse(BaseModel):
    id: int
    character_id: int
    context_key: str
    context_value: Any
    source: str
    confidence: float
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]


class ContextListResponse(BaseModel):
    contexts: List[ContextResponse]


class SessionSummaryResponse(BaseModel):
    id: int
    session_id: str
    character_id: int
    summary: str
    key_decisions: List[str]
    open_questions: List[str]
    active_plan_ids: List[int]
    created_at: datetime
