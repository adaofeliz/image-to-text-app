from fastapi import APIRouter

from .health import router as health_router
from .image_to_text import router as image_to_text_router

router = APIRouter()

router.include_router(health_router)
router.include_router(image_to_text_router)
