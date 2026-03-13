"""
Requirements retrieval endpoints using vector store.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from utils.vector_store import get_vector_store
from core.database import get_db
from core.models import MeetHistory, CustomRequirement, ChunkContent


router = APIRouter(prefix="/requirements", tags=["requirements"])


class RetrieveRequirementsRequest(BaseModel):
    """Request model for retrieving requirements"""
    query: str = Field(..., description="Search query for requirements")
    project_id: str = Field(..., description="Project ID to filter results")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID to filter specific meeting")
    k: int = Field(5, ge=1, le=20, description="Number of results to return (1-20)")


class RequirementChunk(BaseModel):
    """Model for a single requirement chunk with metadata"""
    text: str = Field(..., description="Content text chunk")
    score: float = Field(..., description="Similarity score (lower is better for cosine distance)")
    source: str = Field(..., description="Source type (e.g., 'meeting-transcripts' or 'custom_requirement')")
    project_id: str = Field(..., description="Project ID")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    
    # Meeting transcript fields (optional)
    bot_id: Optional[str] = Field(None, description="Bot ID from MeetingBaaS")
    meeting_id: Optional[str] = Field(None, description="Meeting record ID")
    start_time: Optional[str] = Field(None, description="Start timestamp (HH:MM:SS.mmm)")
    end_time: Optional[str] = Field(None, description="End timestamp (HH:MM:SS.mmm)")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    
    # Custom requirement fields (optional)
    requirement_id: Optional[str] = Field(None, description="Custom requirement ID")
    filename: Optional[str] = Field(None, description="Original filename")
    file_type: Optional[str] = Field(None, description="File type (pdf, docx, txt)")
    chunk_index: Optional[int] = Field(None, description="Chunk index in document")
    total_chunks: Optional[int] = Field(None, description="Total chunks in document")


class RetrieveRequirementsResponse(BaseModel):
    """Response model for requirements retrieval"""
    query: str = Field(..., description="Original search query")
    project_id: str = Field(..., description="Project ID")
    meeting_id: Optional[str] = Field(None, description="Meeting ID if filtered")
    total_results: int = Field(..., description="Number of results returned")
    results: List[RequirementChunk] = Field(..., description="Retrieved requirement chunks")


@router.post("/retrieve", response_model=RetrieveRequirementsResponse)
async def retrieve_requirements(request: RetrieveRequirementsRequest, db: Session = Depends(get_db)):
    """
    Retrieve relevant transcript chunks based on a search query.
    
    This endpoint uses Azure OpenAI embeddings and AWS S3 Vectors to find
    the most relevant meeting transcript segments related to your query.
    
    **Example queries:**
    - "What are the authentication requirements?"
    - "How should the dashboard be designed?"
    - "What database technology was discussed?"
    - "What are the performance requirements?"
    
    **Filters:**
    - `project_id`: Required - filters results to specific project
    - `meeting_id`: Optional - filters to specific meeting within project
    
    **Returns:**
    - Transcript chunks with timestamps
    - Similarity scores (lower is better)
    - Meeting and bot metadata
    """
    try:
        # Get vector store instance
        vector_store = get_vector_store()
        
        # Retrieve relevant chunks with filtering
        results = vector_store.retrieve_requirements(
            query=request.query,
            project_id=request.project_id,
            db=db,
            k=request.k,
            meeting_id=request.meeting_id,  # Optional filter
        )
        
        # Convert to response model
        requirement_chunks = [
            RequirementChunk(**result) for result in results
        ]
        
        return RetrieveRequirementsResponse(
            query=request.query,
            project_id=request.project_id,
            meeting_id=request.meeting_id,
            total_results=len(requirement_chunks),
            results=requirement_chunks,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve requirements: {str(e)}"
        )


class RequirementListItem(BaseModel):
    """Unified requirement list item (meeting or custom)"""
    id: str
    type: str = Field(..., description="'meet' or 'custom'")
    title: str
    status: str
    total_chunks: int
    created_at: str
    # Meeting-specific fields
    bot_id: Optional[str] = None
    meeting_url: Optional[str] = None
    bot_name: Optional[str] = None
    # Custom requirement-specific fields
    filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None


@router.get("/list/{project_id}", response_model=List[RequirementListItem])
async def list_all_requirements(project_id: str, db: Session = Depends(get_db)):
    """
    List all requirements for a project - combines both meeting transcripts and custom uploaded documents.
    
    Returns a unified list with type='meet' for meetings and type='custom' for uploaded documents.
    """
    try:
        all_requirements = []
        
        # Get all meetings for this project
        meetings = db.query(MeetHistory).filter(
            MeetHistory.project_id == project_id
        ).order_by(MeetHistory.created_at.desc()).all()
        
        for meeting in meetings:
            all_requirements.append(RequirementListItem(
                id=str(meeting.id),
                type="meet",
                title=f"{meeting.bot_name} - {meeting.meeting_url[:50]}..." if len(meeting.meeting_url) > 50 else f"{meeting.bot_name} - Meeting",
                status=meeting.status,
                total_chunks=meeting.total_chunks or 0,
                created_at=meeting.created_at.isoformat(),
                bot_id=meeting.bot_id,
                meeting_url=meeting.meeting_url,
                bot_name=meeting.bot_name
            ))
        
        # Get all custom requirements for this project
        custom_reqs = db.query(CustomRequirement).filter(
            CustomRequirement.project_id == project_id
        ).order_by(CustomRequirement.created_at.desc()).all()
        
        for req in custom_reqs:
            all_requirements.append(RequirementListItem(
                id=str(req.id),
                type="custom",
                title=req.filename,
                status=req.status,
                total_chunks=req.total_chunks or 0,
                created_at=req.created_at.isoformat(),
                filename=req.filename,
                file_type=req.file_type,
                file_size=req.file_size
            ))
        
        # Sort all by created_at descending
        all_requirements.sort(key=lambda x: x.created_at, reverse=True)
        
        return all_requirements
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list requirements: {str(e)}"
        )


@router.get("/debug/chunk-contents", response_model=Dict[str, Any])
async def debug_chunk_contents(db: Session = Depends(get_db)):
    """
    Debug endpoint to check ChunkContent records in database.
    Helps diagnose missing text content issues.
    """
    try:
        # Count total chunk contents
        total_chunks = db.query(ChunkContent).count()
        
        # Get sample chunk contents
        sample_chunks = db.query(ChunkContent).limit(5).all()
        
        samples = [
            {
                "chunk_id": chunk.chunk_id,
                "content_length": len(chunk.content),
                "content_preview": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                "created_at": chunk.created_at.isoformat()
            }
            for chunk in sample_chunks
        ]
        
        return {
            "total_chunk_contents": total_chunks,
            "sample_chunks": samples,
            "status": "ok" if total_chunks > 0 else "warning - no chunks found"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check chunk contents: {str(e)}"
        )
