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
    
    # S3 storage keys
    mp4_s3_key = Column(String(500), nullable=True)
    audio_s3_key = Column(String(500), nullable=True)
    transcript_s3_key = Column(String(500), nullable=True)
    
    # Processing metadata
    total_chunks = Column(Integer, default=0)  # Number of vector chunks created from transcript
    
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

class CustomRequirement(Base):
    """Custom requirements uploaded by users (docs, PDFs, txt files)"""
    __tablename__ = "custom_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # txt, pdf, docx
    file_size = Column(Integer, nullable=False)  # bytes
    file_s3_key = Column(String(500), nullable=False)  # S3 storage key
    
    # Processing metadata
    total_chunks = Column(Integer, default=0)  # Number of vector chunks created
    status = Column(String(50), default="processing", index=True)  # processing, completed, failed
    
    # Timestamps
    uploaded_by = Column(String(255), nullable=True)  # User email/ID from Cognito
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CustomRequirement(id={self.id}, filename={self.filename}, status={self.status})>"

class ChunkContent(Base):
    """
    Chunk content storage - stores actual text content separately from vector metadata.
    This keeps vector metadata minimal to avoid AWS S3 Vectors' 2048 byte filterable metadata limit.
    
    Used for both:
    - Meeting transcript chunks
    - Custom requirement document chunks
    """
    __tablename__ = "chunk_contents"

    chunk_id = Column(String(36), primary_key=True)  # UUID stored in vector metadata
    content = Column(Text, nullable=False)  # Actual text content
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ChunkContent(chunk_id={self.chunk_id}, content_length={len(self.content)})>"
