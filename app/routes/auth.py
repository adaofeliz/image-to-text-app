"""Authentication routes."""

import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from app.schemas import (
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_token,
    get_password_hash,
    verify_password,
)
from app.database import TokenBlacklist, User, get_db
from app.dependencies import get_current_user

load_dotenv()

router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer()


def send_verification_email(email: str, verification_token: str):
    """Send verification email to user."""

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    app_url = os.getenv("APP_URL")

    try:
        verification_url = f"{app_url}/auth/verify-email?token={verification_token}"
        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = email
        msg["Subject"] = "Verify Your Email - Image to Text API"

        body = f"""
        Please verify your email by clicking the link below:
        {verification_url}

        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")


@router.post(
    "/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    verification_token = generate_verification_token()
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        is_verified=False,
        verification_token=verification_token,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send verification email
    send_verification_email(user_data.email, verification_token)

    return MessageResponse(
        message="User registered successfully. Please check your email to verify your account."
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return access and refresh tokens."""
    # Find user by email
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create tokens
    user_id = str(user.id)
    access_token = create_access_token(data={"sub": user_id})
    user_refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(access_token=access_token, refresh_token=user_refresh_token)


@router.get(
    "/verify-email", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify user email with verification token from query parameter."""
    stmt = select(User).where(User.verification_token == token)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if user.is_verified:
        return MessageResponse(message="Email already verified")

    # Update user as verified
    user.is_verified = True
    user.verification_token = None
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token. Requires valid refresh token."""
    token = request.refresh_token

    # Check if token is blacklisted
    stmt = select(TokenBlacklist).where(TokenBlacklist.token == token)
    result = await db.execute(stmt)
    blacklisted = result.scalar_one_or_none()
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # Decode refresh token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User ID",
        ) from exc

    # Verify user exists
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new access token
    access_token = create_access_token(data={"sub": user_id_str})

    return TokenResponse(
        access_token=access_token, refresh_token=token
    )


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: RefreshTokenRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout user by blacklisting access and refresh tokens."""
    access_token = credentials.credentials
    user_refresh_token = request.refresh_token

    # Blacklist access token
    if access_token:
        payload = decode_token(access_token)
        if payload:
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            blacklist_entry = TokenBlacklist(
                token=access_token,
                user_id=current_user.id,
                expires_at=expires_at,
            )
            db.add(blacklist_entry)

    # Blacklist refresh token
    if user_refresh_token:
        payload = decode_token(user_refresh_token)
        if payload:
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)

            blacklist_entry = TokenBlacklist(
                token=user_refresh_token,
                user_id=current_user.id,
                expires_at=expires_at,
            )
            db.add(blacklist_entry)

    await db.commit()

    return MessageResponse(message="Logged out successfully.")
