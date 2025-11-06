"""Tests for authentication routes."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@patch("app.routes.auth.send_verification_email")
async def test_register_success(
    mock_send_email, client: AsyncClient, test_user_data: dict
):
    """Test successful user registration."""
    mock_send_email.return_value = None
    response = await client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "registered successfully" in data["message"].lower()


@pytest.mark.asyncio
@patch("app.routes.auth.send_verification_email")
async def test_register_duplicate_email(
    mock_send_email, client: AsyncClient, test_user_data: dict, registered_user
):
    """Test registration with duplicate email."""
    mock_send_email.return_value = None
    response = await client.post("/auth/register", json=test_user_data)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "already registered" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient, registered_user, test_user_data: dict
):
    """Test successful login."""
    response = await client.post(
        "/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "name" in data
    assert data["name"] == test_user_data["name"]
    assert "user_id" in data
    assert data["user_id"] == str(registered_user.id)


@pytest.mark.asyncio
async def test_login_invalid_password(
    client: AsyncClient, registered_user, test_user_data: dict
):
    """Test login with incorrect password."""
    response = await client.post(
        "/auth/login",
        json={"email": test_user_data["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, authenticated_user: dict):
    """Test successful token refresh."""
    response = await client.post(
        "/auth/refresh", json={"refresh_token": authenticated_user["refresh_token"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, authenticated_user: dict):
    """Test successful logout."""
    response = await client.post(
        "/auth/logout",
        json={"refresh_token": authenticated_user["refresh_token"]},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_access_protected_route_without_auth(client: AsyncClient):
    """Test accessing protected route without authentication."""
    response = await client.post("/convert/image/text")
    assert response.status_code == 403
