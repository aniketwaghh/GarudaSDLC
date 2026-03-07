from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4
from core.database import get_db
from core.models import Workspace
from schemas import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceListResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(schema: WorkspaceCreate, db: Session = Depends(get_db)):
    """Create a new workspace"""
    workspace = Workspace(
        id=str(uuid4()),
        name=schema.name,
        description=schema.description
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=WorkspaceListResponse)
def list_workspaces(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all workspaces with pagination"""
    total = db.query(func.count(Workspace.id)).scalar()
    workspaces = db.query(Workspace).offset(skip).limit(limit).all()
    return {"items": workspaces, "total": total}


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str, db: Session = Depends(get_db)):
    """Get a workspace by ID"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(workspace_id: str, schema: WorkspaceUpdate, db: Session = Depends(get_db)):
    """Update a workspace"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    if schema.name is not None:
        workspace.name = schema.name
    if schema.description is not None:
        workspace.description = schema.description
    
    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)):
    """Delete a workspace"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    db.delete(workspace)
    db.commit()
