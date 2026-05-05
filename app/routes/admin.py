"""Admin API routes."""

from fastapi import APIRouter, Depends

from app.dependencies.admin_auth import verify_admin_token

router = APIRouter(
    prefix="/admin/api",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/jobs")
def list_jobs():
    """List all jobs (admin only)."""
    return {}


@router.get("/jobs/{message_id}")
def get_job(message_id: str):
    """Get job details by ID (admin only)."""
    return {}


@router.get("/images/{message_id}")
def get_image(message_id: str):
    """Get image details by ID (admin only)."""
    return {}


@router.get("/verify")
def verify_admin():
    """Verify admin token is valid."""
    return {"valid": True}
