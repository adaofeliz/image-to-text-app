"""Main FastAPI application entry point."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router as api_router
from app.utils.logger import logger

import app.queues.job_queue  # noqa: F401


load_dotenv()

app = FastAPI(title="Image-to-Text API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

app.mount("/dashboard", StaticFiles(directory="app/static/dashboard", html=True), name="dashboard")


@app.exception_handler(404)
def not_found_handler(request: Request, _exc: HTTPException):
    """Handle 404 errors by redirecting to external URL or serving SPA index."""
    logger.warning("404 Not Found: %s %s", request.method, request.url.path)
    
    if request.url.path.startswith("/dashboard"):
        index_path = Path("app/static/dashboard/index.html")
        if index_path.exists():
            return FileResponse(str(index_path))
    
    return RedirectResponse(url="https://ash-speed.hetzner.com/10GB.bin")


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception: %s %s - %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    raise HTTPException(status_code=500, detail="Internal server error") from exc
