# Image-to-Text API

A focused FastAPI service that converts images to text using PaddleOCR, with asynchronous background job processing via Dramatiq and Redis.

## Features

- **Image to Text Conversion**: Upload images and extract text using PaddleOCR
- **Background Job Processing**: OCR tasks processed asynchronously via Dramatiq and Redis
- **Job Status Tracking**: Check job progress and retrieve results via message ID
- **Docker Support**: Fully containerized with Docker and Docker Compose
- **Interactive API Docs**: Swagger UI documentation at `/docs`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/convert/image/text` | Upload an image to convert to text |
| GET  | `/job/{message_id}` | Check the status/result of a conversion job |
| GET  | `/health` | Health check |

### POST /convert/image/text

**Parameters:**
- `image` (required): Image file to process
- `email` (optional): Email address for reference
- `session_id` (optional): Session identifier for tracking

**Response:**
```json
{
  "message_id": "abc123-def456",
  "status": "queued",
  "message": "Job has been queued for processing. Use GET /job/{message_id} to check status."
}
```

### GET /job/{message_id}

Returns job status:
- `pending`: Job is still processing
- `finished`: Job completed, returns extracted text
- `failed`: Job failed, returns error message

## Tech Stack

- **Framework**: FastAPI
- **Queue/Cache**: Redis with Dramatiq
- **OCR Engine**: PaddleOCR
- **Python Version**: 3.11
- **Container**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Running with Docker

1. **Create environment file**:

   ```bash
   cp .env.example .env
   ```

2. **Start the service**:

   ```bash
   docker-compose up --build
   ```

3. **Access the API**:

   - API Base URL: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## Project Structure

```
image-to-text-app/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── database/
│   │   ├── redis.py             # Redis broker configuration
│   ├── dependencies/
│   ├── middleware/
│   │   └── logging_middleware.py  # Request/response logging
│   ├── queues/
│   │   ├── job_queue.py         # Dramatiq actors and job enqueuing
│   │   └── job_status.py        # Job status checking
│   ├── workers/
│   │   └── image_worker.py      # Image-to-text processing worker
│   ├── schemas/
│   │   └── schemas.py           # Pydantic models
│   ├── utils/
│   │   ├── file_utils.py        # File utilities
│   │   ├── logger.py            # Logging configuration
│   │   └── utils.py             # Image validation and OCR helpers
│   └── routes/
│       ├── health.py            # Health check endpoint
│       ├── image_to_text.py     # Image to text conversion endpoint
│       └── jobs.py              # Job status endpoint
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_image_to_text.py    # Image conversion route tests
│   └── test_jobs.py             # Job status endpoint tests
├── docker-compose.yml           # Docker Compose configuration
├── docker-compose.prod.yml      # Docker Compose production config
├── Dockerfile                   # Docker image configuration
└── requirements.txt             # Python dependencies
```

## Docker Configuration

### Development Mode

The `docker-compose.yml` includes:

- Redis service for job queuing and results storage
- Web service with hot-reload for development
- Worker service for background job processing (Dramatiq)
- Volume mounting for hot-reload during development
- Shared volume for temporary files between web and worker services

### Production Mode

The `docker-compose.prod.yml` includes:

- Redis service for job queuing and results storage
- Web service without hot-reload
- Worker service for background job processing (Dramatiq)
- Persistent data volume for Redis

## Dependencies

Key dependencies include:

- `fastapi` - Web framework
- `paddleocr` - OCR engine
- `paddlepaddle` - PaddleOCR runtime
- `pillow` - Image processing
- `dramatiq[redis]` - Background task queue
- `redis` - Redis Python client
- `uvicorn` - ASGI server
- `pydantic` - Data validation

See `requirements.txt` for the complete list.

## Error Handling

- **400 Bad Request**: Invalid file type, missing parameters, or validation errors
- **404 Not Found**: Invalid routes redirect to external URL
- **500 Internal Server Error**: Standard FastAPI error responses

## Testing

The project includes tests using `pytest` and `pytest-asyncio` for async testing.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_image_to_text.py

# Run with verbose output
pytest -v
```

### Test Structure

- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_image_to_text.py` - Image-to-text route tests
- `tests/test_jobs.py` - Job status endpoint tests
