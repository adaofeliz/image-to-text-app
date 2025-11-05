"""Main FastAPI application entry point."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routes import router as api_router


load_dotenv()


APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("APP_DEBUG", "false").lower() in ("1", "true", "yes")


app = FastAPI(title="Image to Text API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(api_router)


@app.exception_handler(404)
async def not_found_handler(_request: Request, _exc: HTTPException):
    """Handle 404 errors by serving the default error page."""
    error_page_path = Path(__file__).parent / "templates" / "NotFound.html"

    if error_page_path.exists():
        return FileResponse(
            path=error_page_path, status_code=404, media_type="text/html"
        )

    raise HTTPException(status_code=404, detail="Page not found")
