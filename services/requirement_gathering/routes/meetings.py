import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core import models
from schemas import MeetJoinRequest, MeetJoinResponse

router = APIRouter(prefix="/meetings", tags=["meetings"])

# MeetingBaaS API Configuration
BOT_BASS_KEY = os.getenv("BOT_BASS_KEY", "")
BOT_BASS_BASE_URL = "https://api.meetingbaas.com"
CALLBACK_URL = os.getenv("CALLBACK_URL", "")
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "")


@router.post("/join", response_model=MeetJoinResponse, status_code=201)
def join_meeting(
    request: MeetJoinRequest,
    db: Session = Depends(get_db)
):
    """
    Send a bot to join a meeting and create meeting history entry
    
    - **meeting_url**: URL of the meeting (Zoom, Google Meet, Teams, etc.)
    - **bot_name**: Display name for the bot
    - **project_id**: Project ID to associate with this meeting
    """
    try:
        print(f"[JOIN MEETING] Project: {request.project_id}, Bot: {request.bot_name}")
        
        # Prepare request to MeetingBaaS
        headers = {
            "x-meeting-baas-api-key": BOT_BASS_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "meeting_url": request.meeting_url,
            "bot_name": request.bot_name,
            "recording_mode": "speaker_view",
            "callback_enabled": True,
            "callback_config": {
                "url": CALLBACK_URL,
                "method": "POST",
                "secret": CALLBACK_SECRET
            }
        }

        print(headers, payload)
        
        # Send request to MeetingBaaS
        response = requests.post(
            f"{BOT_BASS_BASE_URL}/v2/bots",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create bot: {response.text}"
            )
        
        response_data = response.json()
        bot_id = response_data.get("data", {}).get("bot_id") or response_data.get("bot_id")
        
        if not bot_id:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response from MeetingBaaS: {response.text}"
            )
        
        # Create meeting history entry
        meeting_history = models.MeetHistory(
            project_id=request.project_id,
            meeting_url=request.meeting_url,
            bot_id=bot_id,
            bot_name=request.bot_name,
            status="pending"
        )
        
        db.add(meeting_history)
        db.commit()
        db.refresh(meeting_history)
        
        return MeetJoinResponse(
            id=meeting_history.id,
            bot_id=meeting_history.bot_id,
            meeting_url=meeting_history.meeting_url,
            bot_name=meeting_history.bot_name,
            project_id=meeting_history.project_id,
            status=meeting_history.status,
            message="Bot successfully created and will join the meeting"
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"HTTP error occurred: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
