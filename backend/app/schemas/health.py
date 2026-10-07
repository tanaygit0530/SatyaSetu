from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for system health status response."""
    status: str = Field(default="ok", description="Operational status flag")
    service: str = Field(default="sachcheck-backend", description="Service identifier")
    version: str = Field(default="0.1.0", description="Semantic service version")
