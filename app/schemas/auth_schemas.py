"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """User registration schema."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)  


class UserLogin(BaseModel):
    """User login schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Message response schema."""

    message: str
