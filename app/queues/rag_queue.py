"""Dramatiq queue utilities for RAG PDF processing jobs."""

import asyncio
from typing import Dict, Any

import dramatiq
from dramatiq.results.errors import ResultMissing, ResultTimeout, ResultFailure

from app.database.redis import get_redis_broker, get_result_backend
from app.queues.rag_worker import process_rag_job_async
from app.utils.logger import logger


redis_broker = get_redis_broker()
result_backend = get_result_backend()

# Set the broker for dramatiq
dramatiq.set_broker(redis_broker)


@dramatiq.actor(store_results=True, max_retries=3, time_limit=600000)
def process_rag_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a RAG PDF job using Dramatiq."""
    try:
        logger.info("Starting RAG job processing")
        result = asyncio.run(process_rag_job_async(job_data))
        logger.info("RAG job completed successfully: %s", result.get("request_id"))
        return result
    except Exception as e:
        logger.error("Error processing RAG job: %s", e, exc_info=True)
        raise


def enqueue_rag_job(job_data: Dict[str, Any]) -> str:
    """Enqueue a RAG PDF processing job."""
    message = process_rag_job.send(job_data)
    logger.info("Enqueued RAG job with message ID: %s", message.message_id)
    return message.message_id


def get_job_status(message_id: str) -> Dict[str, Any]:
    """Get the status of a job by message ID."""
    try:
        logger.info("Checking job status for message_id: %s", message_id)

        # To call message.get_result(), we need a message object. But we only have a message_id string.
        # This is a workaround to get the message object.
        message = process_rag_job.message_with_options(args=({},)).copy(
            message_id=message_id
        )

        try:
            # Try to get result with no blocking
            result = message.get_result(backend=result_backend, block=False)
            logger.info("Job completed for message_id: %s", message_id)
            return {
                "message_id": message_id,
                "status": "finished",
                "result": result,
            }
        except ResultMissing:
            # Result not yet available - job is still processing or queued
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
        logger.error("Error fetching job status: %s", e, exc_info=True)
        return {
            "message_id": message_id,
            "status": "unknown",
            "error": str(e),
        }
