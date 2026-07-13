from fastapi import APIRouter
from app.api import documents, chat, sessions, export, traces, images

router = APIRouter()

router.include_router(documents.router)
router.include_router(images.router)
router.include_router(chat.router)
router.include_router(sessions.router)
router.include_router(export.router)
router.include_router(traces.router)
