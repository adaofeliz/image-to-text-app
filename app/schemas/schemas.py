"""Pydantic schemas for API requests and responses."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResponseItem(BaseModel):
    """Generic response schema"""

    content: str = Field(min_length=0)
    description: Optional[str] = None
    request_id: Optional[str] = None


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


class ImageJobResult(BaseModel):
    """Response schema for completed image-to-text job result."""

    content: str = Field(..., description="Extracted text from image")
    filename: Optional[str] = Field(None, description="Original filename")
    segments_count: Optional[int] = Field(
        None, description="Number of text segments extracted"
    )
    email: Optional[str] = Field(None, description="Optional email provided with the request")
    session_id: Optional[str] = Field(None, description="Optional session ID provided with the request")


class AdminJobDetail(BaseModel):
    """Response schema for admin job detail endpoint."""

    message_id: str = Field(..., description="Unique job identifier")
    status: Literal["finished", "pending", "failed", "unknown"] = Field(
        ..., description="Job status"
    )
    job_type: Optional[str] = Field(None, description="Job type (e.g., image)")
    filename: Optional[str] = Field(None, description="Original filename")
    email: Optional[str] = Field(None, description="Optional email provided with the request")
    session_id: Optional[str] = Field(None, description="Optional session ID provided with the request")
    content: Optional[str] = Field(None, description="Extracted text from image")
    segments_count: Optional[int] = Field(
        None, description="Number of text segments extracted"
    )
    error: Optional[str] = Field(None, description="Error message if job failed")
