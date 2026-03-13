import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core import models
from schemas import MeetJoinRequest, MeetJoinResponse
from utils.vector_store import get_vector_store
from utils.s3_storage import get_s3_manager

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


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a meeting completely:
    - Vectors from S3 Vectors
    - Chunk contents from database
    - Recording files from S3 (video, audio, transcripts)
    - Database record
    """
    meeting = db.query(models.MeetHistory).filter(
        models.MeetHistory.id == meeting_id
    ).first()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    try:
        print(f"🗑️  Deleting meeting: {meeting.bot_name} ({meeting_id})")
        
        # 1. Delete vectors from vector store
        vector_store = get_vector_store()
        try:
            deleted_vectors = vector_store.delete_vectors_by_meeting(meeting_id, db)
            print(f"✓ Deleted {deleted_vectors} vectors")
        except Exception as e:
            print(f"⚠️  Failed to delete vectors: {str(e)}")
        
        # 2. Delete files from S3
        s3_manager = get_s3_manager()
        files_to_delete = []
        
        if meeting.mp4_s3_key:
            files_to_delete.append(meeting.mp4_s3_key)
        if meeting.audio_s3_key:
            files_to_delete.append(meeting.audio_s3_key)
        if meeting.transcript_s3_key:
            files_to_delete.append(meeting.transcript_s3_key)
        
        # Also try to delete other transcript files (txt, srt, vtt, tsv)
        if meeting.bot_id:
            try:
                # List and delete all files for this bot_id
                bot_files = s3_manager.list_files(meeting.bot_id)
                for file_info in bot_files:
                    files_to_delete.append(file_info['key'])
            except Exception as e:
                print(f"⚠️  Failed to list bot files: {str(e)}")
        
        # Delete all collected S3 files
        deleted_files = 0
        for s3_key in files_to_delete:
            try:
                s3_manager.delete_file(s3_key)
                deleted_files += 1
            except Exception as e:
                print(f"⚠️  Failed to delete {s3_key}: {str(e)}")
        
        print(f"✓ Deleted {deleted_files} files from S3")
        
        # 3. Delete database record
        db.delete(meeting)
        db.commit()
        print(f"✓ Deleted database record")
        
        return {
            "status": "deleted",
            "meeting_id": meeting_id,
            "bot_name": meeting.bot_name,
            "deleted_vectors": deleted_vectors if 'deleted_vectors' in locals() else 0,
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        db.rollback()
        print(f"✗ Deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")
