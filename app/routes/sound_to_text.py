"""Sound to text conversion routes."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status

from app.database import User
from app.dependencies.dependencies import get_current_active_user
from app.schemas import JobQueuedResponse
from app.queues import enqueue_sound_job
from app.utils import delete_temp_file
from app.utils.logger import logger
from app.utils.utils import validate_sound_file

router = APIRouter()

# Shared directory for audio files (same as PDFs)
SHARED_AUDIO_DIR = Path("/app/shared_files")


@router.post(
    "/convert/sound/text",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobQueuedResponse,
)
async def transcribe_sound_to_text(
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_active_user),
) -> JobQueuedResponse:
    """Queue a sound-to-text conversion job.

    Returns a job ID that can be used to check the status via GET /job/{message_id}.
    """
    logger.info(
        "Sound-to-text request from user: %s (ID: %s) - File: %s",
        _current_user.email,
        _current_user.id,
        file.filename,
    )

    # Validate sound file
    if not validate_sound_file(file):
        logger.error("Invalid sound file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sound file.",
        )

    audio_file_path: str | None = None
    try:
        # Save audio to shared volume for worker access
        SHARED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename).suffix if file.filename else ".wav"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=str(SHARED_AUDIO_DIR)
        ) as tmp_file:
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded audio file is empty.",
                )
            tmp_file.write(content)
            audio_file_path = tmp_file.name

        # Enqueue the job
        job_data = {
            "audio_file_path": audio_file_path,
            "filename": file.filename or "audio.wav",
            "user_id": str(_current_user.id),
        }
        job_id = enqueue_sound_job(job_data)

        logger.info(
            "Sound-to-text job enqueued for user %s (ID: %s) - Job ID: %s",
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
        delete_temp_file(audio_file_path, silent=True)
        raise
    except Exception as exc:
        logger.error("Failed to enqueue sound-to-text job: %s", exc, exc_info=True)
        delete_temp_file(audio_file_path, silent=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue the job. Please try again later.",
        ) from exc
