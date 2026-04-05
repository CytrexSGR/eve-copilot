"""Job definition models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobTriggerType(str, Enum):
    """Job trigger types."""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"


class JobDefinition(BaseModel):
    """Job definition for scheduling."""
    id: str = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Human-readable job name")
    description: Optional[str] = None
    
    # Trigger configuration
    trigger_type: JobTriggerType = JobTriggerType.CRON
    trigger_args: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution
    func: str = Field(..., description="Function path to execute")
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    
    # Settings
    enabled: bool = True
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: int = 60
    
    # Metadata
    tags: List[str] = Field(default_factory=list)


class JobRun(BaseModel):
    """Job execution record."""
    id: str
    job_id: str
    status: JobStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class JobInfo(BaseModel):
    """Job information response."""
    id: str
    name: str
    description: Optional[str]
    trigger_type: str
    next_run_time: Optional[datetime]
    enabled: bool
    tags: List[str]
    last_run: Optional[JobRun] = None


class JobListResponse(BaseModel):
    """List of jobs response."""
    jobs: List[JobInfo]
    total: int
