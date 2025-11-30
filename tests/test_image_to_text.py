"""Tests for image to text conversion routes."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.database import User
from app.utils import create_access_token, get_password_hash


@pytest.mark.asyncio
async def test_convert_image_unauthorized(client: AsyncClient):
    """Test image conversion without authentication."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text", files={"image": ("test.png", img_bytes, "image/png")}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_convert_image_invalid_file_type(
    client: AsyncClient, authenticated_user: dict
):
    """Test image conversion with invalid file type."""
    text_file = BytesIO(b"This is not an image")

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.txt", text_file, "text/plain")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.image_to_text.logger")
async def test_convert_image_httpexception_logging(
    mock_logger, client: AsyncClient, authenticated_user: dict
):
    """Test that HTTPException errors are logged and return 400 status code."""
    text_file = BytesIO(b"This is not an image")

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.txt", text_file, "text/plain")},
        headers=authenticated_user["headers"],
    )
    
    # Verify 400 status code is returned
    assert response.status_code == 400
    
    # Verify error logging was called
    mock_logger.error.assert_called_once()
    error_call_args = mock_logger.error.call_args[0]
    assert "HTTP error" in error_call_args[0]
    assert "Status:" in error_call_args[0]
    
    # Verify error detail is preserved in response
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_invalid_mime_type(
    client: AsyncClient, authenticated_user: dict
):
    """Test image conversion with invalid MIME type."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "application/pdf")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "mime" in data["detail"].lower() or "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_missing_file(
    client: AsyncClient, authenticated_user: dict
):
    """Test image conversion without file."""
    response = await client.post(
        "/convert/image/text", headers=authenticated_user["headers"]
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.routes.image_to_text.PaddleOCR")
async def test_convert_image_success(
    mock_paddleocr, client: AsyncClient, authenticated_user: dict
):
    """Test successful image to text conversion."""
    mock_ocr_instance = MagicMock()
    mock_ocr_instance.predict.return_value = [{"rec_texts": ["Hello", "World", "Test"]}]
    mock_paddleocr.return_value = mock_ocr_instance

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "image/png")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    message = data["message"]
    assert "Hello" in message or "World" in message or "Test" in message


@pytest.mark.asyncio
@patch("app.routes.image_to_text.PaddleOCR")
async def test_convert_image_empty_result(
    mock_paddleocr, client: AsyncClient, authenticated_user: dict
):
    """Test image conversion with empty OCR result."""
    mock_ocr_instance = MagicMock()
    mock_ocr_instance.predict.return_value = [{"rec_texts": []}]
    mock_paddleocr.return_value = mock_ocr_instance

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "image/png")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "" or len(data["message"]) == 0


@pytest.mark.asyncio
@patch("app.routes.image_to_text.PaddleOCR")
async def test_convert_image_ocr_error(
    mock_paddleocr, client: AsyncClient, authenticated_user: dict
):
    """Test image conversion when OCR fails."""
    mock_ocr_instance = MagicMock()
    mock_ocr_instance.predict.side_effect = Exception("OCR processing failed")
    mock_paddleocr.return_value = mock_ocr_instance

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "image/png")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_image_different_formats(
    client: AsyncClient, authenticated_user: dict
):
    """Test image conversion with different image formats."""
    formats = [
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
    ]

    for format_name, mime_type in formats:
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format=format_name)
        img_bytes.seek(0)

        with patch("app.routes.image_to_text.PaddleOCR") as mock_paddleocr:
            mock_ocr_instance = MagicMock()
            mock_ocr_instance.predict.return_value = [{"rec_texts": ["Test"]}]
            mock_paddleocr.return_value = mock_ocr_instance

            response = await client.post(
                "/convert/image/text",
                files={"image": (f"test.{format_name.lower()}", img_bytes, mime_type)},
                headers=authenticated_user["headers"],
            )
            assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_convert_image_unverified_user(
    client: AsyncClient, db_session, test_user_data
):
    """Test image conversion with unverified user."""

    user = User(
        name=test_user_data["name"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_verified=False,
        verification_token=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {access_token}"}

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "image/png")},
        headers=headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "verified" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.image_to_text.PaddleOCR")
async def test_convert_image_large_result(
    mock_paddleocr, client: AsyncClient, authenticated_user: dict
):
    """Test image conversion with large OCR result."""
    large_text = ["Word"] * 100
    mock_ocr_instance = MagicMock()
    mock_ocr_instance.predict.return_value = [{"rec_texts": large_text}]
    mock_paddleocr.return_value = mock_ocr_instance

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = await client.post(
        "/convert/image/text",
        files={"image": ("test.png", img_bytes, "image/png")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert len(data["message"]) > 0
