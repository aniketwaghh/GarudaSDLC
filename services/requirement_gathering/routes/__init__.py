from fastapi import APIRouter
from .meetings import router as meetings_router
from .webhooks import router as webhooks_router
from .requirements import router as requirements_router
from .schedules import router as schedules_router
from .videos import router as videos_router
from .custom_requirements import router as custom_requirements_router

# Aggregate all routers
router = APIRouter()
router.include_router(meetings_router)
router.include_router(webhooks_router)
router.include_router(requirements_router)
router.include_router(schedules_router)
router.include_router(videos_router)
router.include_router(custom_requirements_router)
