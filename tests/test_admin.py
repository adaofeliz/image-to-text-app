"""Tests for admin API endpoints."""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.admin import router as admin_router


@pytest.fixture
def admin_client():
    """Create a test client with admin router."""
    os.environ["DASHBOARD_TOKEN"] = "test-token"

    app = FastAPI()
    app.include_router(admin_router)

    return TestClient(app)


@pytest.mark.asyncio
async def test_admin_jobs_valid_token(admin_client):
    """Test admin jobs endpoint with valid token returns 200."""
    response = admin_client.get(
        "/admin/api/jobs",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_jobs_missing_token(admin_client):
    """Test admin jobs endpoint without token returns 401."""
    response = admin_client.get("/admin/api/jobs")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_jobs_invalid_token(admin_client):
    """Test admin jobs endpoint with invalid token returns 403."""
    response = admin_client.get(
        "/admin/api/jobs",
        headers={"X-Dashboard-Token": "wrong-token"}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_jobs_empty_token(admin_client):
    """Test admin jobs endpoint with empty token returns 403."""
    response = admin_client.get(
        "/admin/api/jobs",
        headers={"X-Dashboard-Token": ""}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_verify_valid_token(admin_client):
    """Test admin verify endpoint with valid token returns 200."""
    response = admin_client.get(
        "/admin/api/verify",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_admin_job_detail_valid_token(admin_client):
    """Test admin job detail endpoint with valid token returns 200."""
    response = admin_client.get(
        "/admin/api/jobs/test-job-id",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_image_detail_valid_token(admin_client):
    """Test admin image detail endpoint with valid token returns 200."""
    response = admin_client.get(
        "/admin/api/images/test-image-id",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 200
