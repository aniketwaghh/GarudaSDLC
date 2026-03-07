import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db
from routes import router as api_router



# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Requirement Gathering Service",
    description="Service for gathering requirements from meetings using MeetingBaaS API",
    version="2.0.0"
)

# Configure CORS (optional - for internal service)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "service": "Requirement Gathering Service",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "join_meeting": "/api/meetings/join",
            "webhook": "/api/webhooks/meeting"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


