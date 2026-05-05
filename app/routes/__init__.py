from fastapi import APIRouter

from .admin import router as admin_router
from .health import router as health_router
from .image_to_text import router as image_to_text_router
from .jobs import router as jobs_router

router = APIRouter()

router.include_router(admin_router)
router.include_router(health_router)
router.include_router(image_to_text_router)
router.include_router(jobs_router)
