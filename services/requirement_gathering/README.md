# Requirement Gathering Service

FastAPI service for gathering requirements from meetings using MeetingBaaS API.

## Features

- 🤖 Send AI bots to meetings (Zoom, Google Meet, Microsoft Teams)
- 📹 Automatic video/audio recording
- 📝 Automatic transcription with speaker identification
- 🔔 Webhook integration for real-time status updates
- 💾 Automatic download and storage of recordings
- 📊 Transcript extraction and storage

## Setup

### 1. Install Dependencies

```bash
cd services/requirement_gathering
uv sync
```

### 2. Configure Environment

Create a `.env` file with your MeetingBaaS API key:

```env
BOT_BASS_KEY=your_api_key_here
```

### 3. Run the Service

```bash
# Using uvicorn directly
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or using the script
uv run python main.py
```

The service will be available at `http://localhost:8000`

## API Endpoints

### 1. Send Bot to Meeting

**POST** `/meet/join`

Send a bot to join and record a meeting.

**Request Body:**
```json
{
  "meeting_url": "https://meet.google.com/xxx-yyyy-zzz",
  "bot_name": "Garuda SDLC Bot",
  "recording_mode": "speaker_view",
  "entry_message": "Hi! I'm recording this meeting for note-taking.",
  "speech_to_text": {
    "provider": "Default"
  },
  "automatic_leave": {
    "waiting_room_timeout": 600
  }
}
```

**Response:**
```json
{
  "bot_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Bot successfully sent to meeting. Bot ID: 123e4567-e89b-12d3-a456-426614174000"
}
```

**Parameters:**
- `meeting_url` (required): Meeting URL (Zoom, Google Meet, or Teams)
- `bot_name` (optional): Display name for the bot (default: "Garuda SDLC Bot")
- `recording_mode` (optional): "speaker_view" | "gallery_view" | "audio_only" (default: "speaker_view")
- `bot_image` (optional): URL for bot avatar image
- `entry_message` (optional): Message bot will send when joining
- `speech_to_text` (optional): Transcription settings
  - `provider`: "Default" | "Gladia" | "Runpod"
  - `api_key`: Required for Gladia/Runpod providers
- `automatic_leave` (optional): Auto-leave settings
  - `waiting_room_timeout`: Seconds to wait in waiting room (default: 600)
  - `noone_joined_timeout`: Seconds to wait if no one joins

### 2. Webhook Endpoint

**POST** `/webhooks/meeting`

Receives webhook events from MeetingBaaS. This endpoint:
- Validates the API key in headers
- Logs status changes
- Downloads recordings when complete
- Saves transcripts automatically

**Event Types:**
- `bot.status_change`: Live status updates
  - `joining_call`, `in_waiting_room`, `in_call_recording`, etc.
- `complete`: Recording finished with download links
- `failed`: Bot failed to record meeting
- `transcription_complete`: Transcription processed

### 3. List Downloads

**GET** `/downloads`

List all bots with downloaded files.

**Response:**
```json
{
  "bots": [
    {
      "bot_id": "123e4567-e89b-12d3-a456-426614174000",
      "file_count": 3
    }
  ],
  "total_bots": 1
}
```

**GET** `/downloads/{bot_id}`

List files downloaded for a specific bot.

**Response:**
```json
{
  "bot_id": "123e4567-e89b-12d3-a456-426614174000",
  "files": [
    {
      "filename": "20240101_120000_recording.mp4",
      "size_bytes": 15728640,
      "created_at": "2024-01-01T12:30:00"
    },
    {
      "filename": "20240101_120000_transcript.json",
      "size_bytes": 5432,
      "created_at": "2024-01-01T12:30:00"
    }
  ],
  "total_files": 2
}
```

## Usage Example

### Using cURL

```bash
# Send bot to meeting
curl -X POST "http://localhost:8000/meet/join" \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_url": "https://meet.google.com/xxx-yyyy-zzz",
    "bot_name": "Note Taker",
    "recording_mode": "speaker_view"
  }'

# List all downloads
curl "http://localhost:8000/downloads"

# List files for specific bot
curl "http://localhost:8000/downloads/123e4567-e89b-12d3-a456-426614174000"
```

### Using Python

```python
import requests

# Send bot to join meeting
response = requests.post(
    "http://localhost:8000/meet/join",
    json={
        "meeting_url": "https://meet.google.com/xxx-yyyy-zzz",
        "bot_name": "Garuda SDLC Bot",
        "recording_mode": "speaker_view",
        "speech_to_text": {
            "provider": "Default"
        }
    }
)

bot_data = response.json()
print(f"Bot ID: {bot_data['bot_id']}")
```

## File Storage

Downloaded files are stored in the `downloads/` directory:

```
downloads/
├── {bot_id_1}/
│   ├── 20240101_120000_recording.mp4
│   ├── 20240101_120000_audio.wav
│   └── 20240101_120000_transcript.json
└── {bot_id_2}/
    ├── 20240101_140000_recording.mp4
    └── 20240101_140000_transcript.json
```

## Webhook Configuration

For production, you need to configure your webhook URL:

1. Set up a public URL (e.g., using ngrok for testing)
2. Update the webhook URL in the `/meet/join` endpoint
3. Ensure your server is accessible from MeetingBaaS servers

### Using ngrok for testing:

```bash
ngrok http 8000
```

Then update the webhook URL in `main.py`:
```python
payload["webhook_url"] = "https://your-ngrok-url.ngrok.io/webhooks/meeting"
```

## Important Notes

- **MP4 URLs expire after 2 hours**: The service automatically downloads recordings in the background
- **API Key Security**: The webhook validates the API key in the `x-meeting-baas-api-key` header
- **Background Tasks**: Downloads happen in the background, so the webhook responds immediately
- **Storage**: Plan for adequate storage space for video files

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Status Codes

- **joining_call**: Bot acknowledged join request
- **in_waiting_room**: Bot waiting to be admitted
- **in_call_recording**: Bot actively recording
- **call_ended**: Recording complete, bot left
- **bot_rejected**: Bot was not admitted to meeting
- **bot_removed**: Bot was removed by participant

## Error Handling

The service handles various error scenarios:
- Invalid meeting URLs
- Bot rejection
- Network timeouts
- Download failures

All errors are logged and appropriate HTTP status codes are returned.

## Development

### Project Structure

```
requirement_gathering/
├── main.py           # FastAPI application
├── pyproject.toml    # Dependencies
├── .env             # Environment variables
└── downloads/       # Downloaded recordings (created automatically)
```

### Adding New Features

The service is designed to be extensible:
- Add new webhook handlers in the `meeting_webhook` endpoint
- Add processing logic for transcripts
- Integrate with other services (database, message queue, etc.)

## Support

For issues with MeetingBaaS API, refer to:
- [MeetingBaaS Documentation](https://meetingbaas.com/docs)
- [API Reference](https://api.meetingbaas.com)
