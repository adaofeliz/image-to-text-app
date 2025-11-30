"""RAG with PDF route."""

import os
import tempfile
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from app.database import User
from app.dependencies import get_current_active_user
from app.schemas import (
    RAGJobQueuedResponse,
    RAGJobStatusFailed,
    RAGJobStatusPending,
    ResponseItem,
)
from app.utils import models_supported
from app.queues import enqueue_rag_job, get_job_status
from app.utils.logger import logger

router = APIRouter()

load_dotenv()


@router.post(
    "/pdf/get/response",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RAGJobQueuedResponse,
)
async def rag_with_pdf(
    pdf: UploadFile | None = File(None),
    query: str = Form(...),
    model: str = Form(...),
    past_request_id: Optional[str] = Form(None),
    openai_pass: Optional[str] = Form(None),
    _current_user: User = Depends(get_current_active_user),
) -> RAGJobQueuedResponse:
    """Queue a PDF RAG processing job.

    Either upload a new PDF or query an existing one using past_request_id.
    Returns a job ID that can be used to check the status and retrieve results.
    """
    # Validate model first
    if model not in models_supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model."
        )

    if model == models_supported["openai"] and openai_pass != os.getenv("OPENAI_PASS"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect OpenAI password.",
        )

    # Handle optional PDF file - check if it has a valid filename
    if pdf and (not pdf.filename or not pdf.filename.strip()):
        pdf = None

    # Validate that either PDF or past_request_id is provided
    if not pdf and not past_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either PDF file or past_request_id must be provided.",
        )

    if pdf and past_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both PDF and past_request_id. Use past_request_id to query an existing PDF.",
        )

    try:
        job_data = {
            "query": query,
            "model": model,
            "user_id": str(_current_user.id),
            "past_request_id": past_request_id,
            "openai_pass": openai_pass,
        }

        # If PDF is provided, save it to shared volume for worker access
        pdf_file_path: str | None = None
        if pdf:
            # Save PDF to shared volume (accessible by both web and worker containers)
            shared_pdf_dir = Path("/app/shared_pdfs")
            shared_pdf_dir.mkdir(parents=True, exist_ok=True)

            suffix = Path(pdf.filename).suffix if pdf.filename else ".pdf"
            # Use tempfile to generate unique filename, but save to shared dir
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, dir=str(shared_pdf_dir)
            ) as tmp_file:
                content = await pdf.read()
                if not content:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded PDF file is empty.",
                    )
                tmp_file.write(content)
                pdf_file_path = tmp_file.name

            job_data["pdf_file_path"] = pdf_file_path
            job_data["pdf_filename"] = pdf.filename or "uploaded.pdf"

        # Enqueue the job
        job_id = enqueue_rag_job(job_data)

        logger.info(
            "RAG job enqueued for user %s (ID: %s) - Job ID: %s",
            _current_user.email,
            _current_user.id,
            job_id,
        )

        return RAGJobQueuedResponse(
            message_id=job_id,
            status="queued",
            message="Job has been queued for processing. Use the message_id to check status.",
        )

    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to enqueue RAG job: %s", exc, exc_info=True)
        # Clean up temp file if created
        if pdf_file_path and Path(pdf_file_path).exists():
            try:
                Path(pdf_file_path).unlink(missing_ok=True)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue the job. Please try again later.",
        ) from exc


@router.get(
    "/job/{message_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseItem | RAGJobStatusPending | RAGJobStatusFailed,
)
def get_rag_job_status(
    message_id: str,
    _current_user: User = Depends(get_current_active_user),
) -> ResponseItem | RAGJobStatusPending | RAGJobStatusFailed:
    """Get the status of a RAG PDF processing job.

    Returns the job status and result if completed.
    """
    try:
        status_info = get_job_status(message_id)

        # If job is finished, return result
        if status_info["status"] == "finished" and status_info.get("result"):
            result = status_info["result"]
            return ResponseItem(
                content=result.get("content", ""),
                request_id=result.get("request_id"),
            )

        # If job is pending
        if status_info["status"] == "pending":
            return RAGJobStatusPending(
                message_id=message_id,
                status="pending",
                message=status_info.get("message", "Job is being processed"),
            )

        # If job failed or unknown status
        job_status = status_info["status"]
        if job_status not in ("failed", "unknown"):
            job_status = "unknown"
        return RAGJobStatusFailed(
            message_id=message_id,
            status=job_status,  # type: ignore[arg-type]
            error=status_info.get("error", "Unknown error"),
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to get job status: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status.",
        ) from exc
