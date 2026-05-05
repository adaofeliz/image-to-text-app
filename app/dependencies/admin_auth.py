"""Admin authentication dependencies."""

import os
from fastapi import Header, HTTPException


def verify_admin_token(
    x_dashboard_token: str | None = Header(None, alias="X-Dashboard-Token")
) -> bool:
    """Validate admin token from X-Dashboard-Token header.

    Args:
        x_dashboard_token: Token from request header.

    Returns:
        True if token is valid.

    Raises:
        HTTPException: 401 if token missing, 403 if invalid/empty.
    """
    expected_token = os.getenv("DASHBOARD_TOKEN", "")

    if x_dashboard_token is None:
        raise HTTPException(status_code=401, detail="Missing admin token")

    if x_dashboard_token.strip() == "":
        raise HTTPException(status_code=403, detail="Invalid admin token")

    if x_dashboard_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    return True
