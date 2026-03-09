"""
Requirements retrieval endpoints using vector store.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from utils.vector_store import get_vector_store


router = APIRouter(prefix="/requirements", tags=["requirements"])


class RetrieveRequirementsRequest(BaseModel):
    """Request model for retrieving requirements"""
    query: str = Field(..., description="Search query for requirements")
    project_id: str = Field(..., description="Project ID to filter results")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID to filter specific meeting")
    k: int = Field(5, ge=1, le=20, description="Number of results to return (1-20)")


class RequirementChunk(BaseModel):
    """Model for a single requirement chunk with metadata"""
    text: str = Field(..., description="Transcript text chunk")
    score: float = Field(..., description="Similarity score (lower is better for cosine distance)")
    type: str = Field(..., description="Type of document (e.g., 'meeting-transcripts')")
    bot_id: str = Field(..., description="Bot ID from MeetingBaaS")
    meeting_id: str = Field(..., description="Meeting record ID")
    project_id: str = Field(..., description="Project ID")
    start_time: str = Field(..., description="Start timestamp (HH:MM:SS.mmm)")
    end_time: str = Field(..., description="End timestamp (HH:MM:SS.mmm)")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")


class RetrieveRequirementsResponse(BaseModel):
    """Response model for requirements retrieval"""
    query: str = Field(..., description="Original search query")
    project_id: str = Field(..., description="Project ID")
    meeting_id: Optional[str] = Field(None, description="Meeting ID if filtered")
    total_results: int = Field(..., description="Number of results returned")
    results: List[RequirementChunk] = Field(..., description="Retrieved requirement chunks")


@router.post("/retrieve", response_model=RetrieveRequirementsResponse)
async def retrieve_requirements(request: RetrieveRequirementsRequest):
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
