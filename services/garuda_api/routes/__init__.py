from fastapi import APIRouter
from routes.workspaces import router as workspaces_router
from routes.projects import router as projects_router
from routes.meetings import router as meetings_router
from routes.schedules import router as schedules_router
from routes.chat import router as chat_router
from routes.custom_requirements import router as custom_requirements_router

# Aggregate all routers
router = APIRouter()
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(meetings_router)
router.include_router(schedules_router)
router.include_router(chat_router)
router.include_router(custom_requirements_router)
