
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")  

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.auth import get_user
from core.database import init_db
from routes import router as api_router


# Initialize database
init_db()

app = FastAPI(title="Garuda API", version="0.1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api")


@app.get("/hello")
def hello(user: dict = Depends(get_user)):
    """Protected endpoint that requires valid Cognito token"""
    return {
        "message": f"Hello, {user.get('username', 'User')}!",
        "user": user
    }


@app.get("/health")
def health_check():
    """Health check endpoint (no auth required)"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)