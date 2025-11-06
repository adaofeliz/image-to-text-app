# Image to Text API

A FastAPI-based REST API service that converts images to text using OCR (Optical Character Recognition) powered by PaddleOCR.

## Features

- 🖼️ **Image to Text Conversion**: Upload images and extract text using advanced OCR
- 🔐 **Authentication System**: JWT-based authentication with PostgreSQL
- 👤 **User Management**: Register, login, email verification, and token refresh
- 🔒 **Protected Routes**: Secure endpoints with token-based authentication
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔄 **Auto-reload**: Development mode with automatic file watching and reloading
- 📚 **Interactive API Docs**: Swagger UI documentation at `/docs`
- ✅ **Health Check**: Monitor API server status at `/health`
- 🎨 **Custom Error Pages**: Beautiful 404 error page for invalid routes
- 🚀 **Deployment Webhook**: Automated deployment via webhook endpoint

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (with SQLAlchemy ORM)
- **Authentication**: JWT (PyJWT), bcrypt for password hashing
- **OCR Engine**: PaddleOCR
- **ML Framework**: PyTorch
- **Python Version**: 3.11
- **Container**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- (Optional) Python 3.11+ for local development

### Running with Docker

1. **Clone the repository** (if applicable):
   ```bash
   git clone https://github.com/kingrocfella/image-to-text-app
   cd image-to-text-app
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env  
   ```

3. **Start the service**:
   ```bash
   docker-compose up --build
   ```

4. **Access the API**:
   - API Base URL: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`
   - PostgreSQL: `postgresql://localhost:5432`

5. **Configure environment variables** (create `.env` file):
   ```env
  Make sure you update the .env.example with your own values


## API Endpoints

### Authentication Endpoints

#### POST `/auth/register`

Register a new user.

**Request**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "message": "User registered successfully. Please check your email to verify your account."
}
```

#### POST `/auth/login`

Login and receive access and refresh tokens.

**Request**:
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "name": "John Doe",
  "user_id": "user-uuid-here"
}
```

#### GET `/auth/verify-email`

Verify user email with verification token.

**Request**:
```
GET /auth/verify-email?token=verification-token-from-email
```

**Response**:
```json
{
  "message": "Email verified successfully"
}
```

#### POST `/auth/refresh`

Refresh access token using refresh token. **Protected route** - requires valid refresh token.

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "name": "John Doe",
  "user_id": "user-uuid-here"
}
```

#### POST `/auth/logout`

Logout user by invalidating tokens. **Protected route** - requires valid access token.

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "message": "Logged out successfully. Tokens revoked."
}
```

### Protected Endpoints

#### POST `/convert/image/text`

Convert an uploaded image to text using OCR. **Protected route** - requires valid access token.

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Image file (form field: `image`)

**Response**:
```json
{
  "message": "Extracted text from image"
}
```

### Public Endpoints

#### GET `/health`

Check if the API server is running.

**Response**:
```json
{
  "status": "ok",
  "message": "API server is up and running"
}
```

#### GET `/docs`

Interactive API documentation (Swagger UI).

### Webhook Endpoints

#### GET `/webhook/deploy`

Trigger deployment via webhook. Executes the `deploy.sh` script in the production environment.

**Security**: Requires a valid deployment token via query parameter.

**Request**:
```
GET /webhook/deploy?token=your-deployment-token&environment=production
```

**Query Parameters**:
- `token` (required): Deployment webhook token (must match `DEPLOY_WEBHOOK_TOKEN` environment variable)
- `environment` (optional): Deployment environment (defaults to "production")

**Response**:
```json
{
  "message": "Deployment triggered successfully",
  "environment": "production",
  "output": "deployment script output..."
}
```

**Environment Variable**:
```env
DEPLOY_WEBHOOK_TOKEN=your-secret-token-here
```

## Project Structure

```
image-to-text-app/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database/
│   │   ├── __init__.py      # Database module exports
│   │   ├── database.py      # PostgreSQL connection and configuration
│   │   └── models.py        # Database models (User, TokenBlacklist)
│   ├── dependencies/
│   │   ├── __init__.py      # Dependencies module exports
│   │   └── dependencies.py  # FastAPI dependencies for authentication
│   ├── schemas/
│   │   ├── __init__.py      # Schemas module exports
│   │   ├── schemas.py       # Pydantic models for API
│   │   └── auth_schemas.py  # Authentication request/response models
│   ├── utils/
│   │   ├── __init__.py      # Utils module exports
│   │   ├── auth_utils.py    # Authentication utilities (JWT, password hashing)
│   │   └── utils.py         # Utility functions for image processing
│   ├── routes/
│   │   ├── __init__.py      # Router initialization
│   │   ├── health.py        # Health check endpoint
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── image_to_text.py # Image to text conversion endpoint
│   │   └── webhook.py       # Deployment webhook endpoint
│   └── templates/
│       └── NotFound.html    # 404 error page
├── Dockerfile               # Docker image configuration
├── docker-compose.yml       # Docker Compose configuration (development)
├── docker-compose.prod.yml  # Docker Compose configuration (production)
├── deploy.sh                # Deployment script
├── requirements.txt         # Python dependencies
├── pytest.ini              # Pytest configuration
├── .pylintrc               # Pylint configuration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Docker Configuration

### Development Mode

The `docker-compose.yml` includes:
- PostgreSQL database service with health checks
- Volume mounting for hot-reload during development
- Automatic file watching with `--reload` flag
- Environment variable loading from `.env` file
- Persistent data volumes for PostgreSQL

## Error Handling

- **404 Not Found**: Custom HTML error page with available endpoints
- **500 Internal Server Error**: Standard FastAPI error responses

## Dependencies

Key dependencies include:
- `fastapi` - Web framework
- `sqlalchemy` - SQL toolkit and ORM
- `asyncpg` - Async PostgreSQL driver
- `PyJWT` - JWT token handling
- `passlib[bcrypt]` - Password hashing
- `python-jose` - JWT encoding/decoding
- `email-validator` - Email validation
- `paddleocr` - OCR engine
- `torch` - PyTorch for ML models
- `uvicorn` - ASGI server
- `pydantic` - Data validation

See `requirements.txt` for the complete list.

## Authentication

### Token Expiration
- **Access Token**: Expires after 1 hour
- **Refresh Token**: Expires after 7 days

### Token Usage
1. After login, you receive both `access_token` and `refresh_token`
2. Use `access_token` in the `Authorization` header for protected routes:
   ```
   Authorization: Bearer <access_token>
   ```
3. When the access token expires, use `/auth/refresh` to get a new access token
4. Call `/auth/logout` to invalidate tokens when logging out

### Protected Routes
- `/convert/image/text` - Requires valid access token and verified email
- `/auth/refresh` - Requires valid refresh token
- `/auth/logout` - Requires valid access token

### Webhook Routes
- `/webhook/deploy` - Requires valid deployment token (set `DEPLOY_WEBHOOK_TOKEN` environment variable)

## Testing

The project includes comprehensive tests using `pytest` and `pytest-asyncio` for async testing.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Structure

- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_auth.py` - Authentication route tests
- `tests/test_image_to_text.py` - Image conversion route tests

### Test Coverage

Tests cover:
- User registration and authentication
- Token refresh and logout
- Protected route access
- Image-to-text conversion
- Error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request

