"""Tests for admin API endpoints."""

import os
from unittest.mock import patch

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
@patch("app.routes.admin.get_job_status")
async def test_admin_jobs_valid_token(mock_get_status, admin_client):
    """Test admin jobs endpoint with valid token returns 200."""
    mock_get_status.return_value = {
        "status": "finished",
        "job_type": "image",
        "result": {"filename": "test.png"},
    }
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
@patch("app.routes.admin.get_job_status")
async def test_admin_job_detail_valid_token(mock_get_status, admin_client):
    """Test admin job detail endpoint with valid token returns 200."""
    mock_get_status.return_value = {
        "status": "finished",
        "job_type": "image",
        "result": {"content": "test", "filename": "test.png"},
    }
    response = admin_client.get(
        "/admin/api/jobs/test-job-id",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@patch("app.routes.admin.get_job_data")
@patch("app.routes.admin.get_job_status")
async def test_admin_image_detail_file_not_found(mock_get_status, mock_get_data, admin_client):
    """Test admin image detail endpoint returns 404 when file missing."""
    mock_get_status.return_value = {
        "status": "finished",
        "job_type": "image",
        "result": {"image_file_path": "/app/shared_files/nonexistent.png"},
    }
    mock_get_data.return_value = None
    
    response = admin_client.get(
        "/admin/api/images/test-image-id",
        headers={"X-Dashboard-Token": "test-token"}
    )

    assert response.status_code == 404
