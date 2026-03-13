"""
Custom requirements upload routes - proxy to requirement gathering service
"""
import os
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List
from pydantic import BaseModel


router = APIRouter(prefix="/custom-requirements", tags=["custom-requirements"])

# Requirement gathering service URL
REQUIREMENT_SERVICE_URL = os.getenv(
    "REQUIREMENT_SERVICE_URL", 
    "http://localhost:8001"
)


class RequirementUploadResponse(BaseModel):
    """Response for file upload"""
    requirement_id: str
    filename: str
    file_type: str
    file_size: int
    s3_key: str
    total_chunks: int
    status: str


class RequirementListResponse(BaseModel):
    """Response for listing requirements"""
    id: str
    filename: str
    file_type: str
    file_size: int
    total_chunks: int
    status: str
    created_at: str


@router.post("/upload", response_model=List[RequirementUploadResponse])
async def upload_requirements(
    project_id: str = Form(...),
    user_email: str = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    Upload custom requirement documents (PDF, DOCX, TXT).
    Proxies to requirement gathering service.
    """
    try:
        # Prepare files for forwarding
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append(
                ('files', (file.filename, content, file.content_type))
            )
            # Reset file pointer for potential reuse
            await file.seek(0)
        
        # Forward to requirement gathering service
        response = requests.post(
            f"{REQUIREMENT_SERVICE_URL}/api/custom-requirements/upload",
            data={
                'project_id': project_id,
                'user_email': user_email
            },
            files=files_data,
            timeout=300.0  # 5 minutes for large file processing
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Upload failed: {response.text}"
            )
        
        return response.json()
        
    except requests.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upload processing timeout - files may be too large"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/list/{project_id}", response_model=List[RequirementListResponse])
async def list_requirements(project_id: str):
    """List all custom requirements for a project"""
    try:
        response = requests.get(
            f"{REQUIREMENT_SERVICE_URL}/api/custom-requirements/list/{project_id}",
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list requirements: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.delete("/{requirement_id}")
async def delete_requirement(requirement_id: str):
    """Delete a custom requirement"""
    try:
        response = requests.delete(
            f"{REQUIREMENT_SERVICE_URL}/api/custom-requirements/{requirement_id}",
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to delete requirement: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )


@router.get("/view/{requirement_id}")
async def get_requirement_view_url(requirement_id: str):
    """Get presigned URL to view a custom requirement document"""
    try:
        response = requests.get(
            f"{REQUIREMENT_SERVICE_URL}/api/custom-requirements/view/{requirement_id}",
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get view URL: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with requirement service: {str(e)}"
        )
