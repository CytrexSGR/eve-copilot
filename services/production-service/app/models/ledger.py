"""
Production Ledger Models
Pydantic models for multi-stage manufacturing project tracking
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Create/Update Models (Input)
# =============================================================================

class LedgerCreate(BaseModel):
    """Schema for creating a production ledger."""

    character_id: int = Field(..., description="Character ID owning this ledger")
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    target_type_id: Optional[int] = Field(None, description="Target product type ID")
    target_quantity: int = Field(1, gt=0, description="Target quantity to produce")
    tax_profile_id: Optional[int] = Field(None, description="Tax profile to use")
    facility_id: Optional[int] = Field(None, description="Manufacturing facility ID")


class LedgerUpdate(BaseModel):
    """Schema for updating a production ledger."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(
        None,
        description="Ledger status: planning, active, completed, cancelled"
    )


class StageCreate(BaseModel):
    """Schema for creating a production stage."""

    name: str = Field(..., min_length=1, max_length=255, description="Stage name")
    stage_order: int = Field(..., ge=0, description="Order of stage in production sequence")


class StageUpdate(BaseModel):
    """Schema for updating a production stage."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(
        None,
        description="Stage status: pending, in_progress, completed"
    )


class JobCreate(BaseModel):
    """Schema for creating a production job."""

    type_id: int = Field(..., description="Type ID of item to produce")
    quantity: int = Field(..., gt=0, description="Total quantity to produce")
    runs: int = Field(..., gt=0, description="Number of blueprint runs")
    me_level: int = Field(0, ge=0, le=10, description="Material Efficiency level")
    te_level: int = Field(0, ge=0, le=20, description="Time Efficiency level")


class JobUpdate(BaseModel):
    """Schema for updating a production job."""

    status: Optional[str] = Field(
        None,
        description="Job status: pending, started, completed, cancelled"
    )
    esi_job_id: Optional[int] = Field(None, description="ESI industry job ID")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MaterialUpsert(BaseModel):
    """Schema for upserting a material requirement."""

    type_id: int = Field(..., description="Material type ID")
    type_name: Optional[str] = Field(None, description="Material name")
    total_needed: int = Field(..., ge=0, description="Total quantity needed")
    total_acquired: int = Field(0, ge=0, description="Quantity already acquired")
    estimated_cost: int = Field(0, ge=0, description="Estimated total cost in ISK")
    source: str = Field(
        "buy",
        description="Material source: buy, build, inventory"
    )


# =============================================================================
# Response Models (Output)
# =============================================================================

class Ledger(BaseModel):
    """Production ledger entity."""

    id: int
    character_id: int
    name: str
    target_type_id: Optional[int]
    target_type_name: Optional[str] = None
    target_quantity: int
    status: str
    tax_profile_id: Optional[int]
    facility_id: Optional[int]
    total_material_cost: int
    total_job_cost: int
    total_cost: int
    expected_revenue: int
    expected_profit: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class Stage(BaseModel):
    """Production stage entity."""

    id: int
    ledger_id: int
    name: str
    stage_order: int
    status: str
    material_cost: int
    job_cost: int
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class Job(BaseModel):
    """Production job entity."""

    id: int
    ledger_id: int
    stage_id: int
    type_id: int
    type_name: Optional[str] = None
    blueprint_type_id: Optional[int] = None
    quantity: int
    runs: int
    me_level: int
    te_level: int
    facility_id: Optional[int]
    material_cost: int
    job_cost: int
    production_time: int
    status: str
    esi_job_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class Material(BaseModel):
    """Material requirement entity."""

    id: int
    ledger_id: int
    type_id: int
    type_name: Optional[str]
    total_needed: int
    total_acquired: int
    estimated_cost: int
    source: str


# =============================================================================
# Composite Models (Nested responses)
# =============================================================================

class StageWithJobs(Stage):
    """Stage with nested jobs."""

    jobs: List[Job] = Field(default_factory=list)


class LedgerWithDetails(Ledger):
    """Ledger with nested stages and materials."""

    stages: List[StageWithJobs] = Field(default_factory=list)
    materials: List[Material] = Field(default_factory=list)
