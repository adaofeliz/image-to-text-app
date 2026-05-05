"""Webhook notification utility with retry logic."""

import threading
import time
from typing import Dict, Any

import requests

from app.utils.logger import logger

_MAX_RETRIES = 10
_REQUEST_TIMEOUT = 30
_BACKOFF_SECONDS = 30


def send_webhook(url: str, payload: Dict[str, Any]) -> None:
    """Send webhook notification in a background thread with retry.

    Retries on 5xx status codes and network errors with linear backoff:
    _BACKOFF_SECONDS * retry_number, up to _MAX_RETRIES retries.
    Does NOT retry on 4xx client errors or other non-5xx responses.
    """
    def _send():
        for attempt in range(1, _MAX_RETRIES + 2):  # 1..11 → 11 attempts = 10 retries
            will_retry = attempt <= _MAX_RETRIES
            try:
                response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
                if response.status_code == 200:
                    logger.info("Webhook sent successfully to %s", url)
                    return
                elif 400 <= response.status_code < 500:
                    logger.error(
                        "Webhook failed to %s with client error %d (no retry)",
                        url, response.status_code
                    )
                    return
                elif response.status_code >= 500:
                    if will_retry:
                        logger.warning(
                            "Webhook to %s returned %d, retrying in %ds (retry %d/%d)",
                            url, response.status_code, _BACKOFF_SECONDS * attempt,
                            attempt, _MAX_RETRIES
                        )
                    else:
                        logger.error(
                            "Webhook to %s returned %d on final attempt, giving up",
                            url, response.status_code
                        )
                else:
                    # 1xx / 3xx / other 2xx — treat as unexpected, no retry
                    logger.error(
                        "Webhook to %s returned unexpected status %d (no retry)",
                        url, response.status_code
                    )
                    return
            except requests.exceptions.RequestException as e:
                if will_retry:
                    logger.warning(
                        "Webhook to %s failed with %s, retrying in %ds (retry %d/%d)",
                        url, type(e).__name__, _BACKOFF_SECONDS * attempt,
                        attempt, _MAX_RETRIES
                    )
                else:
                    logger.error(
                        "Webhook to %s failed with %s on final attempt, giving up",
                        url, type(e).__name__
                    )

            if will_retry:
                time.sleep(_BACKOFF_SECONDS * attempt)

        logger.error("Webhook to %s failed after %d retries", url, _MAX_RETRIES)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
