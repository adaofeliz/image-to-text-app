"""Main FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import init_db
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes import router as api_router
from app.utils.logger import logger


load_dotenv()


APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("APP_DEBUG", "False")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan event handler for startup and shutdown events."""
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to initialize database: %s", exc, exc_info=True)
        raise

    yield

    logger.info("Application shutting down...")


app = FastAPI(title="Image to Text API", lifespan=lifespan)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(404)
async def not_found_handler(request: Request, _exc: HTTPException):
    """Handle 404 errors by serving the default error page."""
    logger.warning("404 Not Found: %s %s", request.method, request.url.path)
    error_page_path = Path(__file__).parent / "templates" / "NotFound.html"

    if error_page_path.exists():
        return FileResponse(
            path=error_page_path, status_code=404, media_type="text/html"
        )

    raise HTTPException(status_code=404, detail="Page not found")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception: %s %s - %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    raise HTTPException(status_code=500, detail="Internal server error") from exc
