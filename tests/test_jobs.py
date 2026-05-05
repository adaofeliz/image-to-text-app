"""Tests for unified job status endpoint."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.queues import JOB_TYPE_IMAGE


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_pending(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting job status when job is pending."""
    mock_get_status.return_value = {
        "status": "pending",
        "message": "Job is being processed",
        "job_type": JOB_TYPE_IMAGE,
    }

    response = await client.get("/job/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_image_finished(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting image job status when job is finished."""
    mock_get_status.return_value = {
        "status": "finished",
        "job_type": JOB_TYPE_IMAGE,
        "result": {
            "content": "Extracted text from image",
            "filename": "test.png",
            "segments_count": 5,
        },
    }

    response = await client.get("/job/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Extracted text from image"
    assert data["filename"] == "test.png"
    assert data["segments_count"] == 5


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_image_with_email_and_session_id(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting image job status with email and session_id metadata."""
    mock_get_status.return_value = {
        "status": "finished",
        "job_type": JOB_TYPE_IMAGE,
        "result": {
            "content": "Extracted text from image",
            "filename": "test.png",
            "segments_count": 3,
            "email": "user@example.com",
            "session_id": "sess-456",
        },
    }

    response = await client.get("/job/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Extracted text from image"
    assert data["email"] == "user@example.com"
    assert data["session_id"] == "sess-456"


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_failed(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting job status when job has failed."""
    mock_get_status.return_value = {
        "status": "failed",
        "error": "Processing failed",
        "job_type": JOB_TYPE_IMAGE,
    }

    response = await client.get("/job/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error"] == "Processing failed"


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_unknown(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting job status when job type is unknown."""
    mock_get_status.return_value = {
        "status": "unknown",
        "error": "Job not found",
        "job_type": "unknown",
    }

    response = await client.get("/job/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unknown"


@pytest.mark.asyncio
@patch("app.routes.jobs.get_job_status")
async def test_get_job_status_error(
    mock_get_status,
    client: AsyncClient,
):
    """Test getting job status when an error occurs."""
    mock_get_status.side_effect = Exception("Redis connection failed")

    response = await client.get("/job/test-job-id")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()
