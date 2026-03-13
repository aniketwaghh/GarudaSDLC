"""
Video streaming endpoints for meeting recordings.
Serves videos from S3 using presigned URLs.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from core.database import get_db
from core import models
from utils.s3_storage import get_s3_manager


router = APIRouter(prefix="/videos", tags=["videos"])


class VideoInfoResponse(BaseModel):
    """Video information response"""
    meeting_id: str = Field(..., description="Meeting ID (bot_id)")
    video_s3_key: Optional[str] = Field(None, description="S3 key of video file")
    exists: bool = Field(..., description="Whether video file exists")
    video_url: Optional[str] = Field(None, description="Presigned URL for video access (valid for 1 hour)")


class VideoUrlResponse(BaseModel):
    """Video URL response with presigned URLs"""
    video_url: str = Field(..., description="Presigned URL for video streaming")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    meeting_id: str = Field(..., description="Meeting ID (bot_id)")


@router.get("/{meeting_id}/info", response_model=VideoInfoResponse)
async def get_video_info(meeting_id: str, db: Session = Depends(get_db)):
    """
    Get video file information for a meeting from database.
    
    Args:
        meeting_id: The meeting/bot ID
        db: Database session
        
    Returns:
        Video file information including S3 key and presigned URL
    """
    try:
        # Find meeting in database
        meeting = db.query(models.MeetHistory).filter(
            models.MeetHistory.bot_id == meeting_id
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail=f"Meeting not found: {meeting_id}"
            )
        
        # Check if video exists in S3
        if not meeting.mp4_s3_key:
            return VideoInfoResponse(
                meeting_id=meeting_id,
                video_s3_key=None,
                exists=False,
                video_url=None
            )
        
        # Generate presigned URL
        s3_manager = get_s3_manager()
        
        # Check if file exists in S3
        if not s3_manager.file_exists(meeting.mp4_s3_key):
            return VideoInfoResponse(
                meeting_id=meeting_id,
                video_s3_key=meeting.mp4_s3_key,
                exists=False,
                video_url=None
            )
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_manager.get_presigned_url(meeting.mp4_s3_key, expiration=3600)
        
        return VideoInfoResponse(
            meeting_id=meeting_id,
            video_s3_key=meeting.mp4_s3_key,
            exists=True,
            video_url=presigned_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get video info: {str(e)}"
        )


@router.get("/{meeting_id}/stream", response_model=VideoUrlResponse)
async def stream_video(meeting_id: str, expiration: int = 3600, db: Session = Depends(get_db)):
    """
    Get presigned URL for streaming video from S3.
    
    Args:
        meeting_id: The meeting/bot ID
        expiration: URL expiration time in seconds (default: 1 hour, max: 7 days)
        db: Database session
        
    Returns:
        Presigned URL for video streaming
    """
    try:
        # Validate expiration (max 7 days)
        if expiration > 604800:
            expiration = 604800
        
        # Find meeting in database
        meeting = db.query(models.MeetHistory).filter(
            models.MeetHistory.bot_id == meeting_id
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail=f"Meeting not found: {meeting_id}"
            )
        
        if not meeting.mp4_s3_key:
            raise HTTPException(
                status_code=404,
                detail=f"No video file found for meeting: {meeting_id}"
            )
        
        # Generate presigned URL
        s3_manager = get_s3_manager()
        
        # Check if file exists
        if not s3_manager.file_exists(meeting.mp4_s3_key):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found in S3: {meeting.mp4_s3_key}"
            )
        
        presigned_url = s3_manager.get_presigned_url(meeting.mp4_s3_key, expiration=expiration)
        
        return VideoUrlResponse(
            video_url=presigned_url,
            expires_in=expiration,
            meeting_id=meeting_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate video URL: {str(e)}"
        )


@router.get("/{meeting_id}/files")
async def list_meeting_files(meeting_id: str, db: Session = Depends(get_db)):
    """
    List all files for a meeting from S3.
    
    Args:
        meeting_id: The meeting/bot ID
        db: Database session
        
    Returns:
        List of files with presigned URLs
    """
    try:
        # Find meeting in database
        meeting = db.query(models.MeetHistory).filter(
            models.MeetHistory.bot_id == meeting_id
        ).first()
        
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail=f"Meeting not found: {meeting_id}"
            )
        
        s3_manager = get_s3_manager()
        
        # Get all files from S3
        files = s3_manager.list_files(meeting_id)
        
        # Generate presigned URLs for each file
        files_with_urls = []
        for file_info in files:
            presigned_url = s3_manager.get_presigned_url(file_info['key'], expiration=3600)
            files_with_urls.append({
                **file_info,
                'presigned_url': presigned_url,
                'url_expires_in': 3600
            })
        
        return {
            "meeting_id": meeting_id,
            "files": files_with_urls,
            "total_files": len(files_with_urls)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )
