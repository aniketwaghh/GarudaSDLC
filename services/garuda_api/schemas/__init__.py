from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# ============= Workspace Schemas =============

class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceResponse(BaseModel):
    """Schema for workspace response"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Project Schemas =============

class ProjectCreate(BaseModel):
    """Schema for creating a project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    code_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    scrum_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    code_config: Optional[Dict[str, Any]] = None
    scrum_config: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    code_config: Dict[str, Any]
    scrum_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithWorkspace(ProjectResponse):
    """Project response with workspace details"""
    workspace: WorkspaceResponse


# ============= List Responses =============

class WorkspaceListResponse(BaseModel):
    """Schema for workspace list response"""
    items: list[WorkspaceResponse]
    total: int


class ProjectListResponse(BaseModel):
    """Schema for project list response"""
    items: list[ProjectResponse]
    total: int
