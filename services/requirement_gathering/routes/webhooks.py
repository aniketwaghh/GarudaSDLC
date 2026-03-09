import os
import requests
import aiofiles
import subprocess
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core import models
from schemas import CompleteEvent, FailedEvent
from utils.vector_store import get_vector_store

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Configuration
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "")
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


async def download_file(url: str, output_path: Path) -> None:
    """Download a file from a URL to a local path"""
    try:
        response = requests.get(url, timeout=300.0, stream=True)
        response.raise_for_status()
        
        # Write file in chunks to handle large files
        async with aiofiles.open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    await f.write(chunk)
            
        print(f"✓ Downloaded: {output_path}")
    except Exception as e:
        print(f"✗ Failed to download {url}: {str(e)}")
        raise


async def transcribe_audio(audio_path: Path) -> dict:
    """Transcribe audio file using OpenAI Whisper"""
    try:
        print(f"🎤 Starting transcription for: {audio_path}")
        
        # Run whisper command asynchronously
        # This will create multiple output files in the same directory:
        # - .txt (plain text)
        # - .json (word-level timestamps)
        # - .srt (subtitles)
        # - .vtt (web subtitles)
        # - .tsv (tab-separated values)
        process = await asyncio.create_subprocess_exec(
            "whisper",
            str(audio_path),
            "--model", "tiny",  # Use tiny model for speed (options: tiny, base, small, medium, large)
            "--output_format", "all",  # Generate all formats
            "--output_dir", str(audio_path.parent),  # Save in same directory as audio
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # Whisper creates files with the same name but different extensions
            base_name = audio_path.stem
            transcript_dir = audio_path.parent
            
            transcript_files = {
                "txt": str(transcript_dir / f"{base_name}.txt"),
                "json": str(transcript_dir / f"{base_name}.json"),
                "srt": str(transcript_dir / f"{base_name}.srt"),
                "vtt": str(transcript_dir / f"{base_name}.vtt"),
                "tsv": str(transcript_dir / f"{base_name}.tsv")
            }
            
            print(f"✓ Transcription completed: {audio_path}")
            print(f"  Generated files: {', '.join(transcript_files.keys())}")
            return transcript_files
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
        
        # Download files in background if URLs are available
        bot_dir = DOWNLOAD_DIR / event_data.bot_id
        bot_dir.mkdir(exist_ok=True)
        
        # Download video
        if event_data.video:
            video_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}.mp4"
            mp4_path = bot_dir / video_filename
            await download_file(event_data.video, mp4_path)
            meeting.mp4_local_path = str(mp4_path)
        
        # Download audio
        if event_data.audio:
            audio_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}.mp3"
            audio_path = bot_dir / audio_filename
            await download_file(event_data.audio, audio_path)
            meeting.audio_local_path = str(audio_path)
            
            # Transcribe the audio using Whisper
            try:
                transcript_files = await transcribe_audio(audio_path)
                # Save the JSON transcript path to database (contains word-level timestamps)
                if transcript_files.get("json"):
                    meeting.transcript_local_path = transcript_files["json"]
                    print(f"✓ Whisper transcription saved for bot: {event_data.bot_id}")
                
                # Process TSV transcript and store in vector database
                if transcript_files.get("tsv"):
                    try:
                        print(f"📊 Processing transcript for vector storage...")
                        vector_store = get_vector_store()
                        tsv_path = Path(transcript_files["tsv"])
                        
                        num_chunks = await vector_store.process_and_store_transcript(
                            tsv_path=tsv_path,
                            bot_id=event_data.bot_id,
                            meeting_id=str(meeting.id),
                            project_id=str(meeting.project_id),
                        )
                        print(f"✓ Stored {num_chunks} transcript chunks in vector database")
                    except Exception as vec_err:
                        print(f"⚠ Failed to store in vector database: {str(vec_err)}")
                        # Don't fail the entire process if vectorization fails
                        
            except Exception as e:
                print(f"⚠ Whisper transcription failed: {str(e)}")
                # Fallback to MeetingBaaS transcription if available
                if event_data.transcription:
                    print(f"  → Falling back to MeetingBaaS transcription")
                    transcript_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}_transcript.json"
                    transcript_path = bot_dir / transcript_filename
                    try:
                        await download_file(event_data.transcription, transcript_path)
                        meeting.transcript_local_path = str(transcript_path)
                        print(f"✓ MeetingBaaS transcription downloaded")
                    except Exception as download_err:
                        print(f"⚠ Failed to download MeetingBaaS transcription: {str(download_err)}")
        elif event_data.transcription:
            # If no audio but transcription is available from MeetingBaaS
            transcript_filename = f"{event_data.bot_id}_{event_data.sent_at.replace(':', '-')}_transcript.json"
            transcript_path = bot_dir / transcript_filename
            await download_file(event_data.transcription, transcript_path)
            meeting.transcript_local_path = str(transcript_path)
        
        db.commit()
        
        print(f"✓ Meeting completed and recording saved: {event_data.bot_id}")
        
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


