import os
import requests
import aiofiles
import subprocess
import asyncio
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core import models
from schemas import CompleteEvent, FailedEvent
from utils.vector_store import get_vector_store
from utils.s3_storage import get_s3_manager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Configuration
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "")


async def download_to_temp(url: str) -> Path:
    """
    Download a file from a URL to a temporary location.
    
    Args:
        url: URL to download from
        
    Returns:
        Path to temporary file
    """
    try:
        response = requests.get(url, timeout=300.0, stream=True)
        response.raise_for_status()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = Path(temp_file.name)
        
        # Write file in chunks to handle large files
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"✓ Downloaded to temp: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"✗ Failed to download {url}: {str(e)}")
        raise


async def transcribe_audio(audio_path: Path, bot_id: str) -> dict:
    """
    Transcribe audio file using OpenAI Whisper and upload results to S3.
    
    Args:
        audio_path: Path to temporary audio file
        bot_id: Meeting/bot ID for S3 organization
        
    Returns:
        Dictionary with S3 keys of transcript files
    """
    try:
        print(f"🎤 Starting transcription for: {audio_path}")
        
        # Create temporary directory for whisper output
        temp_dir = Path(tempfile.mkdtemp())
        
        # Run whisper command
        process = await asyncio.create_subprocess_exec(
            "whisper",
            str(audio_path),
            "--model", "tiny",
            "--output_format", "all",
            "--output_dir", str(temp_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            base_name = audio_path.stem
            s3_manager = get_s3_manager()
            
            # Upload all transcript files to S3
            transcript_s3_keys = {}
            extensions = ['txt', 'json', 'srt', 'vtt', 'tsv']
            
            for ext in extensions:
                transcript_file = temp_dir / f"{base_name}.{ext}"
                if transcript_file.exists():
                    filename = f"{bot_id}_{transcript_file.name}"
                    s3_key = await s3_manager.upload_file(transcript_file, bot_id, filename)
                    transcript_s3_keys[ext] = s3_key
                    
                    # Keep local TSV file temporarily for vector processing
                    if ext == 'tsv':
                        transcript_s3_keys['tsv_local_path'] = str(transcript_file)
            
            print(f"✓ Transcription completed and uploaded to S3")
            print(f"  Generated files: {', '.join(transcript_s3_keys.keys())}")
            
            return transcript_s3_keys
        else:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            print(f"✗ Transcription failed: {error_msg}")
            raise Exception(f"Whisper transcription failed: {error_msg}")
            
    except FileNotFoundError:
        print("✗ Whisper not found. Please install: pip install openai-whisper")
        raise Exception("Whisper not installed")
    except Exception as e:
        print(f"✗ Error during transcription: {str(e)}")
        raise


async def handle_completed_event(event_data: CompleteEvent, db: Session):
    """Handle the 'bot.completed' callback - meeting recording is ready"""
    try:
        # Find meeting history by bot_id
        meeting = db.query(models.MeetHistory).filter(
            models.MeetHistory.bot_id == event_data.bot_id
        ).first()
        
        if not meeting:
            print(f"⚠ Meeting not found in database: {event_data.bot_id}")
            return
        
        # Update meeting with recording data
        meeting.status = "completed"
        if event_data.event_id:
            meeting.event_uuid = event_data.event_id
        
        # Extract speaker names from the speakers list
        speaker_names = [s.name for s in event_data.speakers if s.name]
        meeting.speakers = speaker_names
        
        meeting.duration_seconds = event_data.duration_seconds
        meeting.mp4_url = event_data.video
        meeting.audio_url = event_data.audio
        
        db.commit()
        
        # Get S3 manager
        s3_manager = get_s3_manager()
        
        # Download and upload video to S3
        if event_data.video:
            try:
                video_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}.mp4"
                s3_key = await s3_manager.download_and_upload(
                    event_data.video, 
                    event_data.bot_id, 
                    video_filename
                )
                meeting.mp4_s3_key = s3_key
                print(f"✓ Video uploaded to S3: {s3_key}")
            except Exception as e:
                print(f"⚠ Failed to upload video to S3: {str(e)}")
        
        # Download audio, transcribe, and upload to S3
        if event_data.audio:
            try:
                # Download audio to temp location
                audio_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}.mp3"
                temp_audio = await download_to_temp(event_data.audio)
                
                # Upload audio to S3
                audio_s3_key = await s3_manager.upload_file(
                    temp_audio, 
                    event_data.bot_id, 
                    audio_filename
                )
                meeting.audio_s3_key = audio_s3_key
                print(f"✓ Audio uploaded to S3: {audio_s3_key}")
                
                # Transcribe the audio using Whisper and upload
                try:
                    transcript_s3_keys = await transcribe_audio(temp_audio, event_data.bot_id)
                    
                    # Save transcript S3 keys to database
                    if transcript_s3_keys.get("json"):
                        meeting.transcript_s3_key = transcript_s3_keys["json"]
                        print(f"✓ Whisper transcription saved to S3")
                    
                    # Process TSV transcript and store in vector database
                    if transcript_s3_keys.get("tsv_local_path"):
                        try:
                            print(f"📊 Processing transcript for vector storage...")
                            vector_store = get_vector_store()
                            tsv_path = Path(transcript_s3_keys["tsv_local_path"])
                            
                            num_chunks = await vector_store.process_and_store_transcript(
                                tsv_path=tsv_path,
                                bot_id=event_data.bot_id,
                                meeting_id=str(meeting.id),
                                project_id=str(meeting.project_id),
                                db=db
                            )
                            
                            # Update meeting with total_chunks count
                            meeting.total_chunks = num_chunks
                            db.commit()
                            
                            print(f"✓ Stored {num_chunks} transcript chunks in vector database")
                            
                            # Clean up temp TSV file
                            tsv_path.unlink(missing_ok=True)
                        except Exception as vec_err:
                            print(f"⚠ Failed to store in vector database: {str(vec_err)}")
                            
                except Exception as e:
                    print(f"⚠ Whisper transcription failed: {str(e)}")
                    # Fallback to MeetingBaaS transcription if available
                    if event_data.transcription:
                        print(f"  → Falling back to MeetingBaaS transcription")
                        transcript_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}_transcript.json"
                        try:
                            transcript_s3_key = await s3_manager.download_and_upload(
                                event_data.transcription,
                                event_data.bot_id,
                                transcript_filename
                            )
                            meeting.transcript_s3_key = transcript_s3_key
                            print(f"✓ MeetingBaaS transcription uploaded to S3")
                        except Exception as download_err:
                            print(f"⚠ Failed to upload MeetingBaaS transcription: {str(download_err)}")
                
                # Clean up temp audio file
                temp_audio.unlink(missing_ok=True)
                
            except Exception as e:
                print(f"⚠ Audio processing failed: {str(e)}")
        
        elif event_data.transcription:
            # If no audio but transcription is available from MeetingBaaS
            try:
                transcript_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}_transcript.json"
                transcript_s3_key = await s3_manager.download_and_upload(
                    event_data.transcription,
                    event_data.bot_id,
                    transcript_filename
                )
                meeting.transcript_s3_key = transcript_s3_key
                print(f"✓ Transcription uploaded to S3")
            except Exception as e:
                print(f"⚠ Failed to upload transcription: {str(e)}")
        
        db.commit()
        
        print(f"✓ Meeting completed and files saved to S3: {event_data.bot_id}")
        
    except Exception as e:
        print(f"✗ Error handling completed event: {str(e)}")
        db.rollback()
        raise


async def handle_failed_event(event_data: FailedEvent, db: Session):
    """Handle the 'bot.failed' event - meeting bot failed"""
    try:
        meeting = db.query(models.MeetHistory).filter(
            models.MeetHistory.bot_id == event_data.bot_id
        ).first()
        
        if not meeting:
            print(f"⚠ Meeting not found in database: {event_data.bot_id}")
            return
        
        # Update meeting status to failed
        meeting.status = "failed"
        db.commit()
        
        error_msg = f"{event_data.error_code}: {event_data.error_message}" if event_data.error_code else "Unknown error"
        print(f"✓ Marked meeting as failed: {event_data.bot_id}, reason: {error_msg}")
        
    except Exception as e:
        print(f"✗ Error handling failed event: {str(e)}")
        db.rollback()
        raise


@router.post("/callback")
async def bot_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Callback endpoint for MeetingBaaS bot-specific events
    
    Handles:
    - bot.completed: Meeting recording is ready
    - bot.failed: Bot failed to join/record
    """
    try:
        # Verify callback secret
        provided_secret = request.headers.get("x-mb-secret")
        if CALLBACK_SECRET and provided_secret != CALLBACK_SECRET:
            print("✗ Invalid callback secret")
            raise HTTPException(status_code=401, detail="Invalid callback secret")
        
        # Parse callback data
        data = await request.json()
        event_type = data.get("event")
        event_data = data.get("data")
        
        print(f"📥 Received callback: {event_type}")
        print(f"   Data: {event_data}")
        
        # Route to appropriate handler
        if event_type == "bot.completed":
            event = CompleteEvent(**event_data)
            # Process in background to avoid timeout
            background_tasks.add_task(handle_completed_event, event, db)
            
        elif event_type == "bot.failed":
            event = FailedEvent(**event_data)
            await handle_failed_event(event, db)
        
        else:
            print(f"⚠ Unknown event type: {event_type}")
        
        return {"status": "received", "event": event_type}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Callback processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


