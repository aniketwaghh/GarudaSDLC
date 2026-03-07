from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class Workspace(Base):
    """Workspace model"""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name={self.name})>"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    code_config = Column(JSON, nullable=True, default={})
    scrum_config = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    workspace = relationship("Workspace", back_populates="projects")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, workspace_id={self.workspace_id})>"
