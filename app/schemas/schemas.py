from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResponseItem(BaseModel):
    """Generic response schema"""

    content: str = Field(min_length=0)
    description: Optional[str] = None
    request_id: Optional[str] = None


# =============================================================================
# Generic Job Queue Schemas (shared by RAG and Sound jobs)
# =============================================================================


class JobQueuedResponse(BaseModel):
    """Response schema when a job is successfully queued."""

    message_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued"] = Field(default="queued", description="Job status")
    message: str = Field(..., description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "abc123-def456",
                "status": "queued",
                "message": "Job has been queued for processing. Use the message_id to check status.",
            }
        }
    }


class JobStatusPending(BaseModel):
    """Response schema when a job is still pending/processing."""

    message_id: str = Field(..., description="Unique job identifier")
    status: Literal["pending"] = Field(..., description="Job status")
    message: str = Field(..., description="Status message")


class JobStatusFailed(BaseModel):
    """Response schema when a job has failed."""

    message_id: str = Field(..., description="Unique job identifier")
    status: Literal["failed", "unknown"] = Field(..., description="Job status")
    error: str = Field(..., description="Error message")


# Aliases for backward compatibility
RAGJobQueuedResponse = JobQueuedResponse
RAGJobStatusPending = JobStatusPending
RAGJobStatusFailed = JobStatusFailed


# =============================================================================
# Sound-to-Text Response Schemas
# =============================================================================


class SoundJobResult(BaseModel):
    """Response schema for completed sound-to-text job result."""

    content: str = Field(..., description="Transcribed text")
    filename: Optional[str] = Field(None, description="Original filename")
