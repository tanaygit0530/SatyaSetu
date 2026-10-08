from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.core import VerificationResult


class JobStatus(str, Enum):
    """Lifecycle status of an asynchronous verification job."""
    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VerificationJob(BaseModel):
    """Job entity representing a verification work unit."""
    job_id: str = Field(..., description="Unique job execution identifier")
    check_id: str = Field(..., description="Associated check ID")
    status: JobStatus = Field(default=JobStatus.RECEIVED, description="Current job status")
    input_type: str = Field(default="TEXT", description="Format channel (TEXT, URL, PDF, etc.)")
    text: str = Field(..., description="Raw text statement to verify")
    user_id: Optional[str] = Field(default=None, description="Citizen user ID if authenticated")
    is_demo: bool = Field(default=False, description="Whether demo cached response requested")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_stage: Optional[str] = Field(default="RECEIVED", description="Active pipeline stage")
    stage_status: str = Field(default="RUNNING", description="Active stage status: RUNNING, COMPLETED, FAILED")
    duration_ms: Optional[int] = Field(default=None, ge=0)
    error_code: Optional[str] = None
    stages: List[Any] = Field(default_factory=list, description="Historical timeline of stages")
    error: Optional[str] = None
    result: Optional[VerificationResult] = None


class AbstractJobWorker(ABC):
    """
    Abstract worker interface for the verification pipeline.
    Decouples job submission from background execution so worker implementation
    can seamlessly transition from FastAPI BackgroundTasks to Celery/Redis/Cloud PubSub.
    """

    @abstractmethod
    def enqueue_job(self, job: VerificationJob, **kwargs) -> str:
        """
        Enqueues job for non-blocking asynchronous processing.
        Returns the queued job/task identifier.
        """
        pass

    @abstractmethod
    def execute_job(self, job: VerificationJob) -> VerificationResult:
        """
        Executes verification pipeline synchronously on worker thread/process.
        """
        pass
