"""Image to text conversion route."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import get_current_active_user
from app.database import User
from app.schemas import JobQueuedResponse
from app.queues import enqueue_image_job
from app.utils import validate_image_file, delete_temp_file
from app.utils.logger import logger


router = APIRouter()

# Shared directory for image files
SHARED_IMAGE_DIR = Path("/app/shared_files")


@router.post(
    "/convert/image/text",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobQueuedResponse,
)
async def convert_image_to_text(
    image: UploadFile = File(...),
    _current_user: User = Depends(get_current_active_user),
) -> JobQueuedResponse:
    """Queue an image-to-text conversion job.

    Returns a job ID that can be used to check the status via GET /job/{message_id}.
    """
    logger.info(
        "Image-to-text request from user: %s (ID: %s) - File: %s",
        _current_user.email,
        _current_user.id,
        image.filename,
    )

    # Validate that the uploaded file is an image
    try:
        validate_image_file(image)
    except HTTPException as http_exc:
        logger.error(
            "Invalid image file from user %s: %s - %s",
            _current_user.email,
            image.filename,
            http_exc.detail,
        )
        raise

    image_file_path: str | None = None
    try:
        # Save image to shared volume for worker access
        SHARED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        suffix = Path(image.filename).suffix if image.filename else ".png"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=str(SHARED_IMAGE_DIR)
        ) as tmp_file:
            content = await image.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded image file is empty.",
                )
            tmp_file.write(content)
            image_file_path = tmp_file.name

        # Enqueue the job
        job_data = {
            "image_file_path": image_file_path,
            "filename": image.filename or "image.png",
            "user_id": str(_current_user.id),
        }
        job_id = enqueue_image_job(job_data)

        logger.info(
            "Image-to-text job enqueued for user %s (ID: %s) - Job ID: %s",
            _current_user.email,
            _current_user.id,
            job_id,
        )

        return JobQueuedResponse(
            message_id=job_id,
            status="queued",
            message="Job has been queued for processing. Use GET /job/{message_id} to check status.",
        )

    except HTTPException:
        delete_temp_file(image_file_path, silent=True)
        raise
    except Exception as exc:
        logger.error("Failed to enqueue image-to-text job: %s", exc, exc_info=True)
        delete_temp_file(image_file_path, silent=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue the job. Please try again later.",
        ) from exc
