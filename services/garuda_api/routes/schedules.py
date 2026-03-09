"""
Meeting schedules proxy endpoints.
Proxies requests to the requirement gathering service.
"""

import os
import requests
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/schedules", tags=["schedules"])

# Requirement gathering service URL
REQUIREMENT_SERVICE_URL = os.getenv(
    "REQUIREMENT_SERVICE_URL", 
    "http://localhost:8001"
)


class CreateScheduleRequest(BaseModel):
    """Request to create a meeting schedule"""
    project_id: str
    meeting_url: str
    bot_name: str = "Garuda Bot"
    cron_expression: str
    description: Optional[str] = None


class UpdateScheduleRequest(BaseModel):
    """Request to update a schedule"""
    cron_expression: Optional[str] = None
    meeting_url: Optional[str] = None
    bot_name: Optional[str] = None
    status: Optional[str] = None


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


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(request: CreateScheduleRequest):
    """Create a new meeting schedule."""
    try:
        response = requests.post(
            f"{REQUIREMENT_SERVICE_URL}/api/schedules/",
            json=request.dict(),
            timeout=30.0
        )
        
        if response.status_code != 201:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create schedule: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.get("/", response_model=List[ScheduleResponse])
def list_schedules(
    project_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status")
):
    """List all meeting schedules, optionally filtered by project_id and status."""
    try:
        params = {}
        if project_id:
            params["project_id"] = project_id
        if status_filter:
            params["status"] = status_filter
        
        response = requests.get(
            f"{REQUIREMENT_SERVICE_URL}/api/schedules/",
            params=params,
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list schedules: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str):
    """Get a specific schedule by ID."""
    try:
        response = requests.get(
            f"{REQUIREMENT_SERVICE_URL}/api/schedules/{schedule_id}",
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get schedule: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: str, request: UpdateScheduleRequest):
    """Update an existing schedule."""
    try:
        response = requests.put(
            f"{REQUIREMENT_SERVICE_URL}/api/schedules/{schedule_id}",
            json=request.dict(exclude_none=True),
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to update schedule: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str):
    """Delete a schedule."""
    try:
        response = requests.delete(
            f"{REQUIREMENT_SERVICE_URL}/api/schedules/{schedule_id}",
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to delete schedule: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )
