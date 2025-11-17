from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as health_router
from .image_to_text import router as image_to_text_router
from .webhook import router as webhook_router
from .rag_with_pdf import router as rag_with_pdf_router
from .sound_to_text import router as sound_to_text_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(image_to_text_router)
router.include_router(webhook_router)
router.include_router(rag_with_pdf_router)
router.include_router(sound_to_text_router)