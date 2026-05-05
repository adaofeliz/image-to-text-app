"""Webhook notification utility with retry logic."""

import threading
import time
from typing import Dict, Any

import requests

from app.utils.logger import logger


def send_webhook(url: str, payload: Dict[str, Any]) -> None:
    """Send webhook notification in a background thread with retry.
    
    Retries on 5xx status codes and network errors with backoff:
    30 seconds * attempt_number, up to 10 retries.
    Does NOT retry on 4xx client errors.
    """
    def _send():
        max_retries = 10
        for attempt in range(1, max_retries + 1):
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
                else:
                    logger.warning(
                        "Webhook to %s returned %d, retrying in %ds (attempt %d/%d)",
                        url, response.status_code, 30 * attempt, attempt, max_retries
                    )
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "Webhook to %s failed with %s, retrying in %ds (attempt %d/%d)",
                    url, type(e).__name__, 30 * attempt, attempt, max_retries
                )
            
            if attempt < max_retries:
                time.sleep(30 * attempt)
        
        logger.error("Webhook to %s failed after %d attempts", url, max_retries)
    
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
