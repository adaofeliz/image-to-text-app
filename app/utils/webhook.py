"""Webhook notification utility with retry logic."""

import threading
import time
from typing import Dict, Any

import requests

from app.utils.logger import logger


def send_webhook(url: str, payload: Dict[str, Any]) -> None:
    """Send webhook notification in a background thread with retry.

    Retries on 5xx status codes and network errors with linear backoff:
    30 seconds * retry_number, up to 10 retries (11 total attempts).
    Does NOT retry on 4xx client errors or other non-5xx responses.
    """
    def _send():
        max_retries = 10
        for attempt in range(1, max_retries + 2):  # 1..11 → 11 attempts = 10 retries
            try:
                response = requests.post(url, json=payload, timeout=30)
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
                    retry_num = attempt  # attempt 1 → retry 1, etc.
                    logger.warning(
                        "Webhook to %s returned %d, retrying in %ds (retry %d/%d)",
                        url, response.status_code, 30 * retry_num, retry_num, max_retries
                    )
                else:
                    # 1xx / 3xx / other 2xx — treat as unexpected, no retry
                    logger.error(
                        "Webhook to %s returned unexpected status %d (no retry)",
                        url, response.status_code
                    )
                    return
            except requests.exceptions.RequestException as e:
                retry_num = attempt
                logger.warning(
                    "Webhook to %s failed with %s, retrying in %ds (retry %d/%d)",
                    url, type(e).__name__, 30 * retry_num, retry_num, max_retries
                )

            if attempt <= max_retries:  # sleep after attempts 1..10, not after attempt 11
                time.sleep(30 * attempt)

        logger.error("Webhook to %s failed after %d retries", url, max_retries)
    
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
