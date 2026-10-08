from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import InputType, ProcessingStatus
from app.schemas.core import ClaimVerificationResult, VerificationResult


class CheckCreateRequest(BaseModel):
    """Payload for submitting a verification check for asynchronous background processing."""
    input_type: Union[InputType, str] = Field(
        default=InputType.TEXT,
        description="Format channel: TEXT, URL, PDF, SCREENSHOT, VOICE, WHATSAPP",
    )
    text: Optional[str] = Field(
        default=None,
        description="Factual claim or forwarded text message to verify",
    )
    content: Optional[str] = Field(
        default=None,
        description="Alternative alias field for text input",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional submitting citizen user ID",
    )
    check_id: Optional[str] = Field(
        default=None,
        description="Optional custom check ID (e.g. chk_001)",
    )
    is_demo: bool = Field(
        default=False,
        description="Whether explicitly requesting demo cached record",
    )

    @model_validator(mode="after")
    def validate_text_or_content(self) -> "CheckCreateRequest":
        if not self.text and not self.content:
            raise ValueError("Field 'text' or 'content' is required and cannot be empty.")
        if not self.text:
            self.text = self.content
        if isinstance(self.input_type, str):
            try:
                self.input_type = InputType(self.input_type.upper())
            except ValueError:
                self.input_type = InputType.TEXT
        return self


class CheckCreateResponse(BaseModel):
    """Response returned upon accepting a verification check."""
    check_id: str = Field(..., description="Unique check ID (e.g. chk_001)")
    status: str = Field(default="RECEIVED", description="Initial check status (RECEIVED)")


class CheckStatusResponse(BaseModel):
    """Status and progress tracking details for an asynchronous verification check."""
    check_id: str = Field(..., description="Unique check identifier")
    stage: str = Field(default="RECEIVED", description="Current active stage: RECEIVED, EXTRACTING, CLAIMING, RETRIEVING, VALIDATING, VERIFYING, COMPLETED, FAILED")
    status: str = Field(default="RUNNING", description="Stage execution status: RUNNING, COMPLETED, FAILED")
    started_at: Optional[datetime] = Field(None, description="Timestamp when stage began")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when stage/check completed")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")
    error_code: Optional[str] = Field(None, description="Sanitized client-safe error classification code")
    processing_stage: Optional[str] = Field(default=None, description="Alias for stage")
    stages: List[Any] = Field(default_factory=list, description="Historical timeline of stages")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def sync_stage_and_processing_stage(self) -> "CheckStatusResponse":
        if not self.processing_stage and self.stage:
            self.processing_stage = self.stage
        elif not self.stage and self.processing_stage:
            self.stage = self.processing_stage
        return self


class CheckClaimsResponse(BaseModel):
    """Extracted and verified atomic claims belonging to a check."""
    check_id: str = Field(..., description="Unique check identifier")
    claims: List[ClaimVerificationResult] = Field(default_factory=list, description="Verified claims list")


class CheckEvidenceResponse(BaseModel):
    """Grounding evidence items supporting or refuting claims in a check."""
    check_id: str = Field(..., description="Unique check identifier")
    evidence: List[Any] = Field(default_factory=list, description="Validated grounding evidence")


class CheckDetailResponse(BaseModel):
    """Comprehensive details and progress record of a verification check."""
    check_id: str = Field(..., description="Unique check identifier")
    status: str = Field(..., description="Current processing status")
    input_type: str = Field(default="TEXT", description="Submission format")
    text: str = Field(..., description="Original input message")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    claims: List[ClaimVerificationResult] = Field(default_factory=list)
    result: Optional[VerificationResult] = None
    error: Optional[str] = None
