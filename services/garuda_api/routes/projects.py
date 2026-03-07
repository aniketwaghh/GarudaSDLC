from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4
from core.database import get_db
from core.models import Project, Workspace
from schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse, ProjectWithWorkspace

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(workspace_id: str, schema: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project in a workspace"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    project = Project(
        id=str(uuid4()),
        workspace_id=workspace_id,
        name=schema.name,
        description=schema.description,
        code_config=schema.code_config or {},
        scrum_config=schema.scrum_config or {}
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=ProjectListResponse)
def list_projects(workspace_id: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all projects in a workspace"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    total = db.query(func.count(Project.id)).filter(Project.workspace_id == workspace_id).scalar()
    projects = db.query(Project).filter(Project.workspace_id == workspace_id).offset(skip).limit(limit).all()
    return {"items": projects, "total": total}


@router.get("/{project_id}", response_model=ProjectWithWorkspace)
def get_project(workspace_id: str, project_id: str, db: Session = Depends(get_db)):
    """Get a project by ID"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == workspace_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(workspace_id: str, project_id: str, schema: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == workspace_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if schema.name is not None:
        project.name = schema.name
    if schema.description is not None:
        project.description = schema.description
    if schema.code_config is not None:
        project.code_config = schema.code_config
    if schema.scrum_config is not None:
        project.scrum_config = schema.scrum_config
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(workspace_id: str, project_id: str, db: Session = Depends(get_db)):
    """Delete a project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == workspace_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    db.delete(project)
    db.commit()
