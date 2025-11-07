"""Health check route."""
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.utils.logger import logger

load_dotenv()

router = APIRouter()


@router.get("/health", status_code=200)
def health_check():
    """Health check endpoint to verify the API server is running."""
    logger.debug("Health check requested")
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": f"{os.getenv('ENVIRONMENT', 'API').capitalize()} API server is up and running!!!! 🚀",
        },
    )
