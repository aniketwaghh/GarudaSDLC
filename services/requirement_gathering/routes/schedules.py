"""
Meeting schedule endpoints - CRUD operations for scheduled meetings.
"""

import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from core.database import get_db
from core import models
from utils.eventbridge import get_scheduler


router = APIRouter(prefix="/schedules", tags=["schedules"])

# Get callback URL for EventBridge to call
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8001/api/webhooks/callback")
# Extract base URL and construct join endpoint
BASE_URL = CALLBACK_URL.rsplit("/api/webhooks/callback", 1)[0]
JOIN_ENDPOINT = f"{BASE_URL}/api/meetings/join"


class CreateScheduleRequest(BaseModel):
    """Request to create a meeting schedule"""
    project_id: str = Field(..., description="Project ID")
    meeting_url: str = Field(..., description="Meeting URL")
    bot_name: str = Field(default="Garuda Bot", description="Bot display name")
    cron_expression: str = Field(..., description="Cron expression (e.g., 'cron(0 10 * * ? *)' for 10 AM daily)")
    description: Optional[str] = Field(None, description="Optional description")


class ScheduleResponse(BaseModel):
    """Response for schedule operations"""
    id: str
    project_id: str
    schedule_name: str
    schedule_arn: Optional[str]
    cron_expression: str
    meeting_url: str
    bot_name: str
    status: str
    created_at: str
    updated_at: str


class UpdateScheduleRequest(BaseModel):
    """Request to update a schedule"""
    cron_expression: Optional[str] = Field(None, description="New cron expression")
    meeting_url: Optional[str] = Field(None, description="New meeting URL")
    bot_name: Optional[str] = Field(None, description="New bot name")
    status: Optional[str] = Field(None, description="Status: 'enabled' or 'disabled'")


@router.post("/", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    request: CreateScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new meeting schedule using AWS EventBridge.
    
    The schedule will trigger at the specified cron time and automatically
    call the join meeting endpoint with the provided details.
    
    **Cron expression examples:**
    - `cron(0 10 * * ? *)` - Every day at 10:00 AM UTC
    - `cron(0 14 ? * MON-FRI *)` - Every weekday at 2:00 PM UTC
    - `cron(0/30 * * * ? *)` - Every 30 minutes
    """
    try:
        # Generate unique schedule name
        schedule_id = str(uuid.uuid4())
        schedule_name = f"g-mtg-{schedule_id}"
        
        # Prepare payload for join meeting endpoint
        target_payload = {
            "meeting_url": request.meeting_url,
            "bot_name": request.bot_name,
            "project_id": request.project_id
        }
        
        # Create EventBridge schedule
        scheduler = get_scheduler()
        result = scheduler.create_schedule(
            name=schedule_name,
            cron_expression=request.cron_expression,
            webhook_url=JOIN_ENDPOINT,
            payload=target_payload,
            description=request.description or f"Scheduled meeting for project {request.project_id}"
        )
        
        # Store in database
        schedule = models.MeetingSchedule(
            id=schedule_id,
            project_id=request.project_id,
            schedule_name=schedule_name,
            schedule_arn=result.get("schedule_arn"),
            cron_expression=request.cron_expression,
            meeting_url=request.meeting_url,
            bot_name=request.bot_name,
            target_input=target_payload,
            status="enabled"
        )
        
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        
        return ScheduleResponse(
            id=schedule.id,
            project_id=schedule.project_id,
            schedule_name=schedule.schedule_name,
            schedule_arn=schedule.schedule_arn,
            cron_expression=schedule.cron_expression,
            meeting_url=schedule.meeting_url,
            bot_name=schedule.bot_name,
            status=schedule.status,
            created_at=schedule.created_at.isoformat(),
            updated_at=schedule.updated_at.isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/", response_model=List[ScheduleResponse])
def list_schedules(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all meeting schedules.
    
    Optionally filter by project_id and/or status.
    """
    query = db.query(models.MeetingSchedule)
    
    if project_id:
        query = query.filter(models.MeetingSchedule.project_id == project_id)
    
    if status:
        query = query.filter(models.MeetingSchedule.status == status)
    
    schedules = query.order_by(models.MeetingSchedule.created_at.desc()).all()
    
    return [
        ScheduleResponse(
            id=s.id,
            project_id=s.project_id,
            schedule_name=s.schedule_name,
            schedule_arn=s.schedule_arn,
            cron_expression=s.cron_expression,
            meeting_url=s.meeting_url,
            bot_name=s.bot_name,
            status=s.status,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in schedules
    ]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Get a specific schedule by ID."""
    schedule = db.query(models.MeetingSchedule).filter(
        models.MeetingSchedule.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        schedule_name=schedule.schedule_name,
        schedule_arn=schedule.schedule_arn,
        cron_expression=schedule.cron_expression,
        meeting_url=schedule.meeting_url,
        bot_name=schedule.bot_name,
        status=schedule.status,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat()
    )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: str,
    request: UpdateScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Update an existing schedule.
    
    Can update cron expression, meeting details, or enable/disable the schedule.
    """
    schedule = db.query(models.MeetingSchedule).filter(
        models.MeetingSchedule.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        scheduler = get_scheduler()
        
        # Prepare update payload
        new_payload = schedule.target_input.copy() if schedule.target_input else {}
        
        if request.meeting_url:
            new_payload["meeting_url"] = request.meeting_url
            schedule.meeting_url = request.meeting_url
        
        if request.bot_name:
            new_payload["bot_name"] = request.bot_name
            schedule.bot_name = request.bot_name
        
        # Update EventBridge schedule
        eb_state = None
        if request.status:
            eb_state = "ENABLED" if request.status == "enabled" else "DISABLED"
            schedule.status = request.status
        
        scheduler.update_schedule(
            name=schedule.schedule_name,
            cron_expression=request.cron_expression,
            webhook_url=JOIN_ENDPOINT,
            payload=new_payload,
            state=eb_state
        )
        
        # Update database record
        if request.cron_expression:
            schedule.cron_expression = request.cron_expression
        
        schedule.target_input = new_payload
        
        db.commit()
        db.refresh(schedule)
        
        return ScheduleResponse(
            id=schedule.id,
            project_id=schedule.project_id,
            schedule_name=schedule.schedule_name,
            schedule_arn=schedule.schedule_arn,
            cron_expression=schedule.cron_expression,
            meeting_url=schedule.meeting_url,
            bot_name=schedule.bot_name,
            status=schedule.status,
            created_at=schedule.created_at.isoformat(),
            updated_at=schedule.updated_at.isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """
    Delete a schedule.
    
    This will remove the EventBridge schedule and mark the database record as deleted.
    """
    schedule = db.query(models.MeetingSchedule).filter(
        models.MeetingSchedule.id == schedule_id
    ).first()
    
    if not schedule:
       raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        # Delete from EventBridge
        scheduler = get_scheduler()
        scheduler.delete_schedule(schedule.schedule_name)
        
        # Soft delete in database
        schedule.status = "deleted"
        db.commit()
        
        return {"message": "Schedule deleted successfully", "id": schedule_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")
