"""Pytest configuration and fixtures."""
# pylint: disable=import-error,redefined-outer-name,unused-argument,unexpected-keyword-arg,no-member

from contextlib import asynccontextmanager
from io import BytesIO
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image

from app.routes import router as api_router


try:
    from httpx import ASGITransport
except ImportError:
    ASGITransport = None

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@asynccontextmanager
async def test_lifespan(_app: FastAPI):
    """Mock lifespan for testing."""
    yield


test_app = FastAPI(title="Test Image-to-Text API", lifespan=test_lifespan)
test_app.include_router(api_router)


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    try:
        if ASGITransport is not None:
            transport = ASGITransport(app=test_app)  # type: ignore[call-arg]
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
        else:
            raise AttributeError("ASGITransport not available")
    except (TypeError, AttributeError):
        async with AsyncClient(app=test_app, base_url="http://test") as ac:  # type: ignore[call-arg]
            yield ac


@pytest.fixture
def mock_image_file():
    """Fixture for a mock image file."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return ("test_image.png", img_bytes, "image/png")
