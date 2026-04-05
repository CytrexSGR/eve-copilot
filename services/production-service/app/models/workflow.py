"""
Production Workflow Models

Pydantic models for production job management and tracking.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MaterialDecision(BaseModel):
    """Material with make-or-buy decision"""
    material_type_id: int = Field(..., description="Material type ID")
    quantity_needed: int = Field(..., ge=1, description="Quantity needed")
    decision: str = Field(..., pattern="^(make|buy)$", description="Make or buy decision")
    cost_per_unit: Optional[float] = Field(None, ge=0, description="Cost per unit in ISK")
    total_cost: Optional[float] = Field(None, ge=0, description="Total cost in ISK")


class WorkflowJobCreate(BaseModel):
    """Request model for creating a production job"""
    character_id: int = Field(..., description="Character ID")
    item_type_id: int = Field(..., description="Item type ID to produce")
    blueprint_type_id: int = Field(..., description="Blueprint type ID")
    me_level: int = Field(default=0, ge=0, le=10, description="Material Efficiency level")
    te_level: int = Field(default=0, ge=0, le=20, description="Time Efficiency level")
    runs: int = Field(default=1, ge=1, description="Number of production runs")
    materials: List[MaterialDecision] = Field(..., description="Materials with decisions")
    facility_id: Optional[int] = Field(None, description="Facility ID")
    system_id: Optional[int] = Field(None, description="Solar system ID")


class WorkflowJobUpdate(BaseModel):
    """Request model for updating a production job"""
    status: Optional[str] = Field(
        None,
        pattern="^(planned|active|completed|cancelled)$",
        description="Job status"
    )
    actual_revenue: Optional[float] = Field(None, ge=0, description="Actual revenue when sold")


class WorkflowJob(BaseModel):
    """Production job response model"""
    job_id: int = Field(..., description="Job ID")
    item_type_id: int = Field(..., description="Item type ID")
    item_name: str = Field(..., description="Item name")
    runs: int = Field(..., description="Number of runs")
    status: str = Field(..., description="Job status")
    me_level: int = Field(..., description="Material Efficiency level")
    te_level: int = Field(..., description="Time Efficiency level")
    total_cost: Optional[float] = Field(None, description="Total production cost")
    expected_revenue: Optional[float] = Field(None, description="Expected revenue")
    actual_revenue: Optional[float] = Field(None, description="Actual revenue")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class WorkflowJobCreated(BaseModel):
    """Response model for created job"""
    job_id: int = Field(..., description="Created job ID")
    status: str = Field(default="planned", description="Initial status")
    total_cost: float = Field(..., description="Total material cost")


class WorkflowJobsResponse(BaseModel):
    """Response model for job listing"""
    character_id: int = Field(..., description="Character ID")
    status_filter: Optional[str] = Field(None, description="Applied status filter")
    jobs: List[WorkflowJob] = Field(default_factory=list, description="List of jobs")
    total_jobs: int = Field(..., description="Total number of jobs")


class WorkflowJobUpdated(BaseModel):
    """Response model for updated job"""
    job_id: int = Field(..., description="Updated job ID")
    updated: bool = Field(default=True, description="Update success flag")
