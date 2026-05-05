"""Redis connection and configuration for Dramatiq queue broker."""

import os

from dotenv import load_dotenv
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results import Results
from dramatiq.results.backends.redis import RedisBackend

from app.utils.logger import logger

load_dotenv()

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Singleton instances
_redis_broker: RedisBroker | None = None
_result_backend: RedisBackend | None = None


def get_redis_url() -> str:
    """Get the Redis URL."""
    return REDIS_URL


def get_result_backend() -> RedisBackend:
    """Get or create the Redis result backend for Dramatiq."""
    global _result_backend
    if _result_backend is None:
        logger.debug("Initializing Redis result backend: %s", REDIS_URL)
        _result_backend = RedisBackend(url=REDIS_URL)
    return _result_backend


def get_redis_broker() -> RedisBroker:
    """Get or create the Redis broker for Dramatiq with Results middleware."""
    global _redis_broker
    if _redis_broker is None:
        logger.debug("Initializing Redis broker: %s", REDIS_URL)
        _redis_broker = RedisBroker(url=REDIS_URL)

    # Add Results middleware for storing job results
    result_backend = get_result_backend()
    _redis_broker.add_middleware(Results(backend=result_backend))  # type: ignore[union-attr]

    logger.info("Redis broker initialized with Results middleware")
    return _redis_broker
