"""Job status utilities for checking background job results."""

from typing import Dict, Any

from dramatiq.results.errors import ResultMissing, ResultTimeout, ResultFailure

from app.queues.job_queue import (
    _get_redis_client,
    result_backend,
    process_rag_job,
    process_sound_job,
    process_image_job,
    JOB_TYPE_RAG,
    JOB_TYPE_SOUND,
    JOB_TYPE_IMAGE,
    JOB_TYPE_KEY_PREFIX,
)
from app.utils.logger import logger


def _get_job_type(message_id: str) -> str | None:
    """Get job type from Redis."""
    client = _get_redis_client()
    key = f"{JOB_TYPE_KEY_PREFIX}{message_id}"
    job_type_bytes = client.get(key)
    if job_type_bytes and isinstance(job_type_bytes, bytes):
        return job_type_bytes.decode("utf-8")
    return None


def get_job_status(message_id: str) -> Dict[str, Any]:
    """Get the status of any job by message ID.

    Automatically determines the job type and queries the appropriate actor.
    """
    try:
        logger.info("Checking job status for message_id: %s", message_id)

        # Look up job type
        job_type = _get_job_type(message_id)
        logger.info("Job type for message_id %s: %s", message_id, job_type)

        # Select the appropriate actor based on job type
        if job_type == JOB_TYPE_SOUND:
            actor = process_sound_job
        elif job_type == JOB_TYPE_RAG:
            actor = process_rag_job
        elif job_type == JOB_TYPE_IMAGE:
            actor = process_image_job
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        result = _try_get_result(actor, message_id)
        result["job_type"] = job_type
        return result

    except Exception as e:
        logger.error("Error fetching job status: %s", e, exc_info=True)
        return {
            "message_id": message_id,
            "status": "unknown",
            "error": str(e),
        }


def _try_get_result(actor, message_id: str) -> Dict[str, Any]:
    """Try to get result from a specific actor."""
    try:
        logger.info("Trying to get result for message_id: %s", message_id)
        message = actor.message_with_options(args=({},)).copy(message_id=message_id)

        try:
            result = message.get_result(backend=result_backend, block=False)
            logger.info("Job completed for message_id: %s", message_id)
            return {
                "message_id": message_id,
                "status": "finished",
                "result": result,
            }
        except ResultMissing:
            logger.info("Result not yet available for message_id: %s", message_id)
            return {
                "message_id": message_id,
                "status": "pending",
                "message": "Job is being processed",
            }
        except ResultTimeout:
            logger.info("Result timeout for message_id: %s", message_id)
            return {
                "message_id": message_id,
                "status": "pending",
                "message": "Job is being processed",
            }
        except ResultFailure as e:
            logger.error("Job failed for message_id: %s - %s", message_id, e)
            return {
                "message_id": message_id,
                "status": "failed",
                "error": str(e),
            }
    except Exception as e:
        logger.error("Error in _try_get_result: %s", e, exc_info=True)
        return {
            "message_id": message_id,
            "status": "unknown",
            "error": str(e),
        }
