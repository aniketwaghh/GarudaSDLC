import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Requirement gathering service URL
REQUIREMENT_SERVICE_URL = os.getenv(
    "REQUIREMENT_SERVICE_URL", 
    "http://localhost:8001"
)


class JoinMeetingRequest(BaseModel):
    """Request to join a meeting"""
    meeting_url: str
    bot_name: str = "Garuda Bot"
    project_id: str


class JoinMeetingResponse(BaseModel):
    """Response from joining a meeting"""
    id: str
    bot_id: str
    meeting_url: str
    bot_name: str
    project_id: str
    status: str
    message: str


@router.post("/join", response_model=JoinMeetingResponse, status_code=status.HTTP_201_CREATED)
def join_meeting(
    request: JoinMeetingRequest,
):
    """
    Send a bot to join a meeting
    
    This endpoint proxies the request to the requirement gathering service.
    Requires authentication.
    """
    try:
        # Call requirement gathering service
        response = requests.post(
            f"{REQUIREMENT_SERVICE_URL}/api/meetings/join",
            json={
                "meeting_url": request.meeting_url,
                "bot_name": request.bot_name,
                "project_id": request.project_id
            },
            timeout=30.0
        )
        
        if response.status_code != 201:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to join meeting: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
