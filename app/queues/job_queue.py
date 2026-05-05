"""Dramatiq queue utilities for background job processing."""

import os
import json
from typing import Dict, Any

import dramatiq
import redis
from dramatiq.middleware import CurrentMessage

from app.database.redis import get_redis_broker, get_result_backend, get_redis_url
from app.workers import process_image_job_sync
from app.utils import delete_temp_file
from app.utils.logger import logger
from app.utils.webhook import send_webhook


redis_broker = get_redis_broker()
result_backend = get_result_backend()

_redis_client: redis.Redis | None = None


def _get_redis_client() -> redis.Redis:
    """Get Redis client for job type tracking.""" 
    global _redis_client  # pylint: disable=global-statement
    if _redis_client is None:
        _redis_client = redis.from_url(get_redis_url())
    return _redis_client


JOB_TYPE_IMAGE = "image"
JOB_TYPE_KEY_PREFIX = "job:type:"
JOB_DATA_KEY_PREFIX = "job:data:"
JOB_TYPE_TTL = 86400 * int(os.getenv("JOB_TYPE_TTL_DAYS", "7"))

dramatiq.set_broker(redis_broker)
redis_broker.add_middleware(CurrentMessage())


def _store_job_type(message_id: str, job_type: str) -> None:
    """Store job type in Redis for later lookup."""
    client = _get_redis_client()
    key = f"{JOB_TYPE_KEY_PREFIX}{message_id}"
    client.setex(key, JOB_TYPE_TTL, job_type)
    logger.debug("Stored job type '%s' for message_id: %s", job_type, message_id)


def _store_job_data(message_id: str, job_data: Dict[str, Any]) -> None:
    """Store job data in Redis for later lookup."""
    client = _get_redis_client()
    key = f"{JOB_DATA_KEY_PREFIX}{message_id}"
    client.setex(key, JOB_TYPE_TTL, json.dumps(job_data))
    logger.debug("Stored job data for message_id: %s", message_id)


def get_job_data(message_id: str) -> Dict[str, Any] | None:
    """Get job data from Redis by message ID."""
    client = _get_redis_client()
    key = f"{JOB_DATA_KEY_PREFIX}{message_id}"
    data = client.get(key)
    if data and isinstance(data, bytes):
        return json.loads(data.decode("utf-8"))
    return None


# =============================================================================
# Image-to-Text Processing
# =============================================================================


def _is_file_not_found_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    if isinstance(exc, ValueError):
        msg = str(exc).lower()
        return "image file not found" in msg or "not found" in msg and "image" in msg
    return False


def _is_final_retry(message: Any) -> bool:
    try:
        retries = message.options.get("retries", 0)
        max_retries = message.actor_options.get("max_retries", 3)
        return retries >= max_retries
    except Exception:
        return True


@dramatiq.actor(store_results=True, max_retries=3, time_limit=300000)
def process_image_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process an image-to-text job using Dramatiq."""
    result = None
    error = None
    is_final = False
    image_file_path = job_data.get("image_file_path", "")

    try:
        logger.info("Starting image-to-text job processing")
        if not image_file_path:
            is_final = True
            raise ValueError("Missing image_file_path in job_data")
        result = process_image_job_sync(job_data)
        is_final = True
        logger.info("Image-to-text job completed successfully")
        return result
    except Exception as e:
        error = str(e)
        message = CurrentMessage.get_current_message()
        is_final = message is None or _is_final_retry(message)

        if _is_file_not_found_error(e):
            is_final = True
            logger.error("Image file not found, skipping further retries: %s", e)
        else:
            logger.error("Error processing image-to-text job: %s", e, exc_info=True)
        raise
    finally:
        if is_final:
            if image_file_path:
                delete_temp_file(image_file_path)

            webhook_url = os.getenv("WEBHOOK_URL", "").strip()
            if webhook_url:
                try:
                    message = CurrentMessage.get_current_message()
                    message_id = message.message_id if message else None

                    payload = {
                        "message_id": message_id,
                        "status": "finished" if error is None else "failed",
                        "result": result if error is None else None,
                        "error": error,
                    }
                    for key in ("email", "session_id", "filename"):
                        if key in job_data:
                            payload[key] = job_data[key]

                    send_webhook(webhook_url, payload)
                    logger.info("Webhook dispatched to %s for message_id: %s", webhook_url, message_id)
                except Exception:
                    logger.exception("Failed to dispatch webhook")


def enqueue_image_job(job_data: Dict[str, Any]) -> str:
    """Enqueue an image-to-text processing job."""
    message = process_image_job.send(job_data)
    _store_job_type(message.message_id, JOB_TYPE_IMAGE)
    _store_job_data(message.message_id, job_data)
    logger.info("Enqueued image-to-text job with message ID: %s", message.message_id)
    return message.message_id
