"""
Video streaming endpoints for meeting recordings.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


router = APIRouter(prefix="/videos", tags=["videos"])

# Base directory for downloaded meeting recordings
DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"


class VideoInfoResponse(BaseModel):
    """Video information response"""
    meeting_id: str = Field(..., description="Meeting ID")
    video_path: str = Field(..., description="Relative path to video file")
    exists: bool = Field(..., description="Whether video file exists")


def ranged_request(
    file_path: Path,
    start: int = 0,
    end: int = None,
    chunk_size: int = 1024 * 1024  # 1MB chunks
):
    """
    Generator function to stream video with range request support.
    """
    file_size = file_path.stat().st_size
    
    if end is None or end >= file_size:
        end = file_size - 1
    
    with open(file_path, "rb") as video_file:
        video_file.seek(start)
        remaining = end - start + 1
        
        while remaining > 0:
            chunk = video_file.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/{meeting_id}/info", response_model=VideoInfoResponse)
async def get_video_info(meeting_id: str):
    """
    Get video file information for a meeting.
    
    Args:
        meeting_id: The meeting/bot ID
        
    Returns:
        Video file information including path and availability
    """
    try:
        # Find the meeting directory
        meeting_dir = DOWNLOADS_DIR / meeting_id
        
        if not meeting_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Meeting directory not found: {meeting_id}"
            )
        
        # Find MP4 file in the directory
        mp4_files = list(meeting_dir.glob("*.mp4"))
        
        if not mp4_files:
            return VideoInfoResponse(
                meeting_id=meeting_id,
                video_path="",
                exists=False
            )
        
        # Use the first MP4 file found
        video_file = mp4_files[0]
        relative_path = str(video_file.relative_to(DOWNLOADS_DIR))
        
        return VideoInfoResponse(
            meeting_id=meeting_id,
            video_path=relative_path,
            exists=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get video info: {str(e)}"
        )


@router.get("/{meeting_id}/stream")
async def stream_video(request: Request, meeting_id: str):
    """
    Stream video file for a meeting with range request support.
    
    Args:
        request: HTTP request with Range header
        meeting_id: The meeting/bot ID
        
    Returns:
        Video file stream with proper range support
    """
    try:
        # Find the meeting directory
        meeting_dir = DOWNLOADS_DIR / meeting_id
        
        if not meeting_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Meeting directory not found: {meeting_id}"
            )
        
        # Find MP4 file in the directory
        mp4_files = list(meeting_dir.glob("*.mp4"))
        
        if not mp4_files:
            raise HTTPException(
                status_code=404,
                detail=f"No video file found for meeting: {meeting_id}"
            )
        
        # Use the first MP4 file found
        video_file = mp4_files[0]
        
        if not video_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {video_file}"
            )
        
        file_size = video_file.stat().st_size
        
        # Handle range requests for video seeking
        range_header = request.headers.get("range")
        
        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
            
            # Ensure end doesn't exceed file size
            end = min(end, file_size - 1)
            
            content_length = end - start + 1
            
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": "video/mp4",
            }
            
            return StreamingResponse(
                ranged_request(video_file, start, end),
                status_code=206,  # Partial Content
                headers=headers,
                media_type="video/mp4"
            )
        
        # No range request - return full video
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(
            ranged_request(video_file, 0, file_size - 1),
            status_code=200,
            headers=headers,
            media_type="video/mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stream video: {str(e)}"
        )
