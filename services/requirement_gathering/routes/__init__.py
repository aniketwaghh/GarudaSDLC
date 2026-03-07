from fastapi import APIRouter
from .meetings import router as meetings_router
from .webhooks import router as webhooks_router

# Aggregate all routers
router = APIRouter()
router.include_router(meetings_router)
router.include_router(webhooks_router)
