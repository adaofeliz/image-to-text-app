"""Unified job status routes."""

from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    ImageJobResult,
    JobStatusFailed,
    JobStatusPending,
)
from app.queues import get_job_status
from app.utils.logger import logger

router = APIRouter()


@router.get(
    "/job/{message_id}",
    status_code=status.HTTP_200_OK,
    response_model=ImageJobResult
    | JobStatusPending
    | JobStatusFailed,
)
def get_job_status_endpoint(
    message_id: str,
) -> ImageJobResult | JobStatusPending | JobStatusFailed:
    """Get the status of a background image-to-text job.

    Returns the job status and result if completed.
    """
    try:
        status_info = get_job_status(message_id)

        if status_info["status"] == "finished" and status_info.get("result"):
            result = status_info["result"]
            return ImageJobResult(
                content=result.get("content", ""),
                filename=result.get("filename"),
                segments_count=result.get("segments_count"),
                email=result.get("email"),
                session_id=result.get("session_id"),
            )

        if status_info["status"] in ("queued", "pending"):
            return JobStatusPending(
                message_id=message_id,
                status="pending",
                message=status_info.get("message", "Job is being processed"),
            )

        job_status = status_info["status"]
        if job_status not in ("failed", "unknown"):
            job_status = "unknown"
        return JobStatusFailed(
            message_id=message_id,
            status=job_status,
            error=status_info.get("error", "Unknown error"),
        )

    except Exception as exc:
        logger.error("Failed to get job status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status.",
        ) from exc
