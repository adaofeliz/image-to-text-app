"""Tests for sound to text conversion routes."""

from io import BytesIO
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.database import User
from app.utils import create_access_token, get_password_hash


@pytest.mark.asyncio
async def test_convert_sound_unauthorized(client: AsyncClient):
    """Test sound conversion without authentication."""
    # Create a mock audio file (WAV format)
    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text", files={"file": ("test.wav", audio_bytes, "audio/wav")}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_convert_sound_invalid_file_type(
    client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion with invalid file type."""
    text_file = BytesIO(b"This is not an audio file")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.txt", text_file, "text/plain")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_convert_sound_missing_file(
    client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion without file."""
    response = await client.post(
        "/convert/sound/text", headers=authenticated_user["headers"]
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_success(
    mock_convert_sound, client: AsyncClient, authenticated_user: dict
):
    """Test successful sound to text conversion."""
    mock_convert_sound.return_value = "This is a test transcription"

    # Create a mock audio file (WAV format)
    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["content"] == "This is a test transcription"
    mock_convert_sound.assert_called_once()


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_empty_result(
    mock_convert_sound, client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion with empty transcription result."""
    mock_convert_sound.return_value = ""

    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["content"] == ""


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_conversion_error(
    mock_convert_sound, client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion when conversion fails."""
    from fastapi import HTTPException

    mock_convert_sound.side_effect = HTTPException(
        status_code=500, detail="Audio processing failed"
    )

    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=authenticated_user["headers"],
    )
    # The route catches all exceptions and returns 500
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_general_exception(
    mock_convert_sound, client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion when a general exception occurs."""
    mock_convert_sound.side_effect = Exception("Unexpected error")

    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_convert_sound_unverified_user(
    client: AsyncClient, db_session, test_user_data
):
    """Test sound conversion with unverified user."""
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

    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "verified" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_different_formats(
    mock_convert_sound, client: AsyncClient, authenticated_user: dict
):
    """Test sound conversion with different audio formats."""
    mock_convert_sound.return_value = "Transcribed text"

    formats = [
        ("wav", "audio/wav"),
        ("mp3", "audio/mpeg"),
        ("m4a", "audio/mp4"),
    ]

    for ext, mime_type in formats:
        audio_bytes = BytesIO(b"fake audio content")

        response = await client.post(
            "/convert/sound/text",
            files={"file": (f"test.{ext}", audio_bytes, mime_type)},
            headers=authenticated_user["headers"],
        )
        # Should either succeed or fail validation, but not crash
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
@patch("app.routes.sound_to_text.logger")
@patch("app.routes.sound_to_text.convert_sound_to_text")
async def test_convert_sound_logging(
    mock_convert_sound, mock_logger, client: AsyncClient, authenticated_user: dict
):
    """Test that sound conversion logs appropriately."""
    mock_convert_sound.return_value = "Test transcription"

    audio_bytes = BytesIO(b"fake audio content")

    response = await client.post(
        "/convert/sound/text",
        files={"file": ("test.wav", audio_bytes, "audio/wav")},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    # Verify logging was called
    assert mock_logger.info.called
    # Check that conversion logging was called
    log_calls = [str(call) for call in mock_logger.info.call_args_list]
    assert any(
        "Converting sound file" in str(call) for call in mock_logger.info.call_args_list
    )
    assert any(
        "Converted sound file to text" in str(call)
        for call in mock_logger.info.call_args_list
    )
