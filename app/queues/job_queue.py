"""Dramatiq queue utilities for background job processing."""

import asyncio
import os
from typing import Dict, Any

import dramatiq
import redis

from app.database.redis import get_redis_broker, get_result_backend, get_redis_url
from app.queues.rag_worker import process_rag_job_async
from app.queues.sound_worker import process_sound_job_sync
from app.utils.logger import logger


redis_broker = get_redis_broker()
result_backend = get_result_backend()

# Redis client for job type tracking
_redis_client: redis.Redis | None = None


def _get_redis_client() -> redis.Redis:
    """Get Redis client for job type tracking."""
    global _redis_client  # pylint: disable=global-statement
    if _redis_client is None:
        _redis_client = redis.from_url(get_redis_url())
    return _redis_client


# Job type constants
JOB_TYPE_RAG = "rag"
JOB_TYPE_SOUND = "sound"
JOB_TYPE_KEY_PREFIX = "job:type:"
JOB_TYPE_TTL = 86400 * int(os.getenv("JOB_TYPE_TTL_DAYS", "7"))

# Set the broker for dramatiq
dramatiq.set_broker(redis_broker)


def _store_job_type(message_id: str, job_type: str) -> None:
    """Store job type in Redis for later lookup."""
    client = _get_redis_client()
    key = f"{JOB_TYPE_KEY_PREFIX}{message_id}"
    client.setex(key, JOB_TYPE_TTL, job_type)
    logger.debug("Stored job type '%s' for message_id: %s", job_type, message_id)


# =============================================================================
# RAG PDF Processing
# =============================================================================


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
    _store_job_type(message.message_id, JOB_TYPE_RAG)
    logger.info("Enqueued RAG job with message ID: %s", message.message_id)
    return message.message_id


# =============================================================================
# Sound-to-Text Processing
# =============================================================================


@dramatiq.actor(store_results=True, max_retries=3, time_limit=300000)
def process_sound_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a sound-to-text job using Dramatiq."""
    try:
        logger.info("Starting sound-to-text job processing")
        result = process_sound_job_sync(job_data)
        logger.info("Sound-to-text job completed successfully")
        return result
    except Exception as e:
        logger.error("Error processing sound-to-text job: %s", e, exc_info=True)
        raise


def enqueue_sound_job(job_data: Dict[str, Any]) -> str:
    """Enqueue a sound-to-text processing job."""
    message = process_sound_job.send(job_data)
    _store_job_type(message.message_id, JOB_TYPE_SOUND)
    logger.info("Enqueued sound-to-text job with message ID: %s", message.message_id)
    return message.message_id
