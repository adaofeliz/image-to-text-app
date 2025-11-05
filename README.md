# Image to Text API

A FastAPI-based REST API service that converts images to text using OCR (Optical Character Recognition) powered by PaddleOCR.

## Features

- 🖼️ **Image to Text Conversion**: Upload images and extract text using advanced OCR
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔄 **Auto-reload**: Development mode with automatic file watching and reloading
- 📚 **Interactive API Docs**: Swagger UI documentation at `/docs`
- ✅ **Health Check**: Monitor API server status at `/health`
- 🎨 **Custom Error Pages**: Beautiful 404 error page for invalid routes

## Tech Stack

- **Framework**: FastAPI
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
   cp .env.example .env  # Create .env file with your configuration
   ```

3. **Start the service**:
   ```bash
   docker-compose up --build
   ```

4. **Access the API**:
   - API Base URL: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## API Endpoints

### POST `/convert/image/text`

Convert an uploaded image to text using OCR.

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

### GET `/health`

Check if the API server is running.

**Response**:
```json
{
  "status": "ok",
  "message": "API server is up and running"
}
```

### GET `/docs`

Interactive API documentation (Swagger UI).

## Project Structure

```
image-to-text-app/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── schemas.py           # Pydantic models for API
│   ├── routes/
│   │   ├── __init__.py      # Router initialization
│   │   ├── health.py        # Health check endpoint
│   │   └── image_to_text.py # Image to text conversion endpoint
│   └── templates/
│       └── NotFound.html    # 404 error page
├── Dockerfile               # Docker image configuration
├── docker-compose.yml       # Docker Compose configuration
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Docker Configuration

### Development Mode

The `docker-compose.yml` includes:
- Volume mounting for hot-reload during development
- Automatic file watching with `--reload` flag
- Environment variable loading from `.env` file

## Error Handling

- **404 Not Found**: Custom HTML error page with available endpoints
- **500 Internal Server Error**: Standard FastAPI error responses

## Dependencies

Key dependencies include:
- `fastapi` - Web framework
- `paddleocr` - OCR engine
- `torch` - PyTorch for ML models
- `uvicorn` - ASGI server
- `pydantic` - Data validation

See `requirements.txt` for the complete list.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request

