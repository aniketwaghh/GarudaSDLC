from fastapi import APIRouter
from routes.workspaces import router as workspaces_router
from routes.projects import router as projects_router
from routes.meetings import router as meetings_router

# Aggregate all routers
router = APIRouter()
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(meetings_router)
