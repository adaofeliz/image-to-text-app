"""Tests for image to text conversion routes."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from PIL import Image


@pytest.mark.asyncio
async def test_convert_image_invalid_file_type(client: AsyncClient):
    """Test image conversion with invalid file type."""
    text_file = BytesIO(b"This is not an image")

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.txt", text_file, "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_invalid_mime_type(client: AsyncClient):
    """Test image conversion with invalid MIME type."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "mime" in data["detail"].lower() or "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_missing_file(client: AsyncClient):
    """Test image conversion without file."""
    response = await client.post("/convert/image/text")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_convert_image_job_queued(
    client: AsyncClient, tmp_path: Path
):
    """Test successful image-to-text job queueing."""
    with patch("app.routes.image_to_text.enqueue_image_job") as mock_enqueue, \
         patch("app.routes.image_to_text.SHARED_IMAGE_DIR", tmp_path):
        mock_enqueue.return_value = "test-job-id-123"

        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = await client.post(
            "/convert/image/text",
            files={"image": ("test.png", img_bytes, "image/png")},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["message_id"] == "test-job-id-123"
        assert data["status"] == "queued"
        assert "message" in data

        # Verify enqueue was called
        mock_enqueue.assert_called_once()
        call_args = mock_enqueue.call_args[0][0]
        assert "image_file_path" in call_args
        assert call_args["filename"] == "test.png"


@pytest.mark.asyncio
async def test_convert_image_different_formats(
    client: AsyncClient, tmp_path: Path
):
    """Test image queueing with different image formats."""
    formats = [
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
    ]

    for format_name, mime_type in formats:
        with patch("app.routes.image_to_text.enqueue_image_job") as mock_enqueue, \
             patch("app.routes.image_to_text.SHARED_IMAGE_DIR", tmp_path):
            mock_enqueue.return_value = "test-job-id-456"

            img = Image.new("RGB", (100, 100), color="red")
            img_bytes = BytesIO()
            img.save(img_bytes, format=format_name)
            img_bytes.seek(0)

            response = await client.post(
                "/convert/image/text",
                files={"image": (f"test.{format_name.lower()}", img_bytes, mime_type)},
            )
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_convert_image_with_email_and_session_id(
    client: AsyncClient, tmp_path: Path
):
    """Test image conversion with optional email and session_id."""
    with patch("app.routes.image_to_text.enqueue_image_job") as mock_enqueue, \
         patch("app.routes.image_to_text.SHARED_IMAGE_DIR", tmp_path):
        mock_enqueue.return_value = "test-job-id-789"

        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = await client.post(
            "/convert/image/text",
            files={"image": ("test.png", img_bytes, "image/png")},
            data={"email": "user@example.com", "session_id": "abc-123"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["message_id"] == "test-job-id-789"
        assert data["status"] == "queued"

        mock_enqueue.assert_called_once()
        call_args = mock_enqueue.call_args[0][0]
        assert call_args["email"] == "user@example.com"
        assert call_args["session_id"] == "abc-123"


@pytest.mark.asyncio
async def test_convert_image_enqueue_error(
    client: AsyncClient, tmp_path: Path
):
    """Test image conversion when enqueueing fails."""
    with patch("app.routes.image_to_text.enqueue_image_job") as mock_enqueue, \
         patch("app.routes.image_to_text.SHARED_IMAGE_DIR", tmp_path):
        mock_enqueue.side_effect = Exception("Queue service unavailable")

        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        response = await client.post(
            "/convert/image/text",
            files={"image": ("test.png", img_bytes, "image/png")},
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "enqueue" in data["detail"].lower() or "failed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_empty_file(
    client: AsyncClient, tmp_path: Path
):
    """Test image conversion with empty file content."""
    with patch("app.routes.image_to_text.enqueue_image_job") as mock_enqueue, \
         patch("app.routes.image_to_text.SHARED_IMAGE_DIR", tmp_path):
        empty_bytes = BytesIO(b"")

        response = await client.post(
            "/convert/image/text",
            files={"image": ("test.png", empty_bytes, "image/png")},
        )
        # Should fail validation or return 400
        assert response.status_code in [400, 422]

        # Enqueue should not be called for empty files
        mock_enqueue.assert_not_called()
