"""Admin API routes."""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.dependencies.admin_auth import verify_admin_token
from app.queues.job_queue import _get_redis_client, JOB_TYPE_KEY_PREFIX, get_job_data
from app.queues.job_status import get_job_status
from app.schemas import AdminJobDetail
from app.utils.logger import logger

router = APIRouter(
    prefix="/admin/api",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)

SHARED_FILES_DIR = Path("/app/shared_files").resolve()


@router.get("/jobs")
def list_jobs():
    """List all jobs (admin only)."""
    jobs = []
    client = _get_redis_client()
    prefix = JOB_TYPE_KEY_PREFIX

    try:
        for key in client.scan_iter(match=f"{prefix}*"):
            if len(jobs) >= 100:
                break

            try:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                message_id = key_str[len(prefix):]

                status_info = get_job_status(message_id)

                job = {
                    "message_id": message_id,
                    "status": status_info.get("status", "unknown"),
                    "job_type": status_info.get("job_type") or "image",
                    "filename": "",
                    "email": "",
                    "session_id": "",
                }

                result = status_info.get("result")
                if isinstance(result, dict):
                    job["filename"] = result.get("filename", "")
                    job["email"] = result.get("email", "")
                    job["session_id"] = result.get("session_id", "")

                if not job["filename"]:
                    job_data = get_job_data(message_id)
                    if isinstance(job_data, dict):
                        job["filename"] = job_data.get("filename", "")
                        job["email"] = job_data.get("email", "")
                        job["session_id"] = job_data.get("session_id", "")

                jobs.append(job)
            except Exception:
                logger.exception("Error processing job key %s", key)
                continue
    except Exception:
        logger.exception("Error listing jobs from Redis")

    return jobs


@router.get(
    "/jobs/{message_id}",
    response_model=AdminJobDetail,
)
def get_job(message_id: str):
    """Get job details by ID (admin only)."""
    try:
        status_info = get_job_status(message_id)
    except Exception as exc:
        logger.error("Failed to get job status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status.",
        ) from exc

    # Handle missing job: job_type is None and status is pending means
    # the job was never registered in Redis.
    if status_info.get("job_type") is None and status_info["status"] == "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    response = {
        "message_id": message_id,
        "status": status_info["status"],
        "job_type": status_info.get("job_type"),
        "error": status_info.get("error"),
    }

    if status_info["status"] == "finished" and status_info.get("result"):
        result = status_info["result"]
        response.update({
            "content": result.get("content"),
            "filename": result.get("filename"),
            "segments_count": result.get("segments_count"),
            "email": result.get("email"),
            "session_id": result.get("session_id"),
        })
    else:
        response.update({
            "content": None,
            "filename": None,
            "segments_count": None,
            "email": None,
            "session_id": None,
        })

    return response


@router.get("/images/{message_id}")
def get_image(message_id: str):
    """Stream image file by job ID (admin only)."""
    # 1. Try to get image_file_path from job status result
    image_file_path = None
    try:
        status_info = get_job_status(message_id)
        result = status_info.get("result")
        if isinstance(result, dict):
            image_file_path = result.get("image_file_path")
    except Exception as exc:
        logger.error("Failed to get job status for image: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status.",
        ) from exc

    # 2. Fallback to job_data if not in result
    if not image_file_path:
        try:
            job_data = get_job_data(message_id)
            if isinstance(job_data, dict):
                image_file_path = job_data.get("image_file_path")
        except Exception as exc:
            logger.error("Failed to get job data for image: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve job data.",
            ) from exc

    # 3. If still no path, return 404
    if not image_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found for this job.",
        )

    # 4. Resolve path and validate against path traversal
    try:
        file_path = Path(image_file_path).resolve()
    except Exception as exc:
        logger.error("Invalid image file path: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file path.",
        ) from exc

    # Ensure resolved path is within SHARED_FILES_DIR
    try:
        file_path.relative_to(SHARED_FILES_DIR)
    except ValueError as exc:
        logger.warning(
            "Path traversal blocked for message_id %s: %s",
            message_id,
            file_path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        ) from exc

    # 5. Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found.",
        )

    # 6. Guess MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"

    # 7. Return FileResponse with inline disposition
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        headers={"Content-Disposition": "inline"},
    )


@router.get("/verify")
def verify_admin():
    """Verify admin token is valid."""
    return {"valid": True}
