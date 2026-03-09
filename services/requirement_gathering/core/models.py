from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Text
from sqlalchemy.sql import func
from core.database import Base


class Project(Base):
    """Project model - minimal definition for foreign key reference"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    code_config = Column(JSON, nullable=True, default={})
    scrum_config = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetHistory(Base):
    """Meeting history - tracks all meeting recordings"""
    __tablename__ = "meet_history"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    meeting_url = Column(String(500), nullable=False)
    bot_id = Column(String(255), nullable=False, index=True)  # MeetingBaaS bot ID
    bot_name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending", index=True)  # pending, recording, completed, failed
    event_uuid = Column(String(255), nullable=True)
    
    # Recording URLs (expire after 2 hours)
    mp4_url = Column(String(1000), nullable=True)
    audio_url = Column(String(1000), nullable=True)
    
    # Local file paths
    mp4_local_path = Column(String(500), nullable=True)
    audio_local_path = Column(String(500), nullable=True)
    transcript_local_path = Column(String(500), nullable=True)
    
    # Meeting metadata
    speakers = Column(JSON, nullable=True, default=[])
    duration_seconds = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MeetHistory(id={self.id}, bot_id={self.bot_id}, status={self.status})>"


class MeetingSchedule(Base):
    """Meeting schedules - tracks scheduled meeting bot joins"""
    __tablename__ = "meeting_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    
    # EventBridge scheduler details
    schedule_name = Column(String(255), nullable=False, unique=True, index=True)  # EventBridge schedule name
    schedule_arn = Column(String(500), nullable=True)  # EventBridge ARN
    cron_expression = Column(String(255), nullable=False)  # Cron expression
    
    # Meeting details
    meeting_url = Column(String(500), nullable=False)
    bot_name = Column(String(255), nullable=False)
    
    # EventBridge target input (stored as JSON)
    target_input = Column(JSON, nullable=False)  # Full payload sent to webhook
    
    # Status
    status = Column(String(50), default="enabled", index=True)  # enabled, disabled, deleted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MeetingSchedule(id={self.id}, schedule_name={self.schedule_name}, status={self.status})>"
