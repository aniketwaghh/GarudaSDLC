from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Request/Response Schemas
class MeetJoinRequest(BaseModel):
    meeting_url: str = Field(..., description="Meeting URL (Zoom, Google Meet, Teams, etc.)")
    bot_name: str = Field(default="Garuda Bot", description="Name to display for the bot")
    project_id: str = Field(..., description="Project ID to associate with this meeting")


class MeetJoinResponse(BaseModel):
    id: str
    bot_id: str
    meeting_url: str
    bot_name: str
    project_id: str
    status: str
    message: str = "Bot successfully created and will join the meeting"


# Callback Event Schemas (bot.completed and bot.failed only)
class Participant(BaseModel):
    name: Optional[str] = None


class Speaker(BaseModel):
    name: Optional[str] = None


class CompleteEvent(BaseModel):
    bot_id: str
    event_id: Optional[str] = None
    participants: List[Participant] = []
    speakers: List[Speaker] = []
    duration_seconds: Optional[int] = None
    joined_at: Optional[str] = None
    exited_at: Optional[str] = None
    data_deleted: bool = False
    video: Optional[str] = None  # Signed URL for MP4
    audio: Optional[str] = None  # Signed URL for audio
    diarization: Optional[str] = None
    raw_transcription: Optional[str] = None
    transcription: Optional[str] = None
    transcription_provider: Optional[str] = None
    transcription_ids: Optional[List[str]] = None
    sent_at: str
    extra: Optional[dict] = None


class FailedEvent(BaseModel):
    bot_id: str
    event_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    extra: Optional[dict] = None
