"""
RAG Chat endpoint with LangChain agent for querying requirements.
"""

import os
import requests
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.messages import HumanMessage, AIMessage


router = APIRouter(prefix="/chat", tags=["chat"])

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
REQUIREMENT_SERVICE_URL = os.getenv("REQUIREMENT_SERVICE_URL", "http://localhost:8001")


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class Reference(BaseModel):
    """Reference to source material"""
    source_type: str = Field(..., description="Type: 'meeting', 'document', or 'langchain_doc'")
    title: str = Field(..., description="Title or identifier")
    excerpt: str = Field(..., description="Relevant excerpt from the source")
    metadata: dict = Field(default_factory=dict, description="Additional metadata (meeting_id, timestamp, filename, url, etc.)")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")


class StructuredChatResponse(BaseModel):
    """Structured response with answer and references"""
    answer: str = Field(..., description="Clear, detailed nicely formatted markdown full-length answer to the user's question")
    references: List[Reference] = Field(default_factory=list, description="Array of source references used")
    confidence: str = Field("high", description="Confidence level: 'high', 'medium', 'low'")
    followup_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")


class ChatRequest(BaseModel):
    """Request model for RAG chat"""
    message: str = Field(..., description="User's question or query")
    project_id: str = Field(..., description="Project ID to search within")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="Previous chat messages")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID filter")
    k: int = Field(5, ge=1, le=10, description="Number of context chunks to retrieve")


class ChatResponse(BaseModel):
    """Response model for RAG chat"""
    answer: str = Field(..., description="AI assistant's response")
    references: List[Reference] = Field(..., description="Source references used")
    confidence: str = Field(..., description="Confidence level")
    followup_questions: List[str] = Field(..., description="Suggested follow-up questions")
    project_id: str = Field(..., description="Project ID")


def create_retrieve_tool(project_id: str, meeting_id: Optional[str] = None, k: int = 5):
    """Create a tool that retrieves requirements from the vector store"""
    
    @tool
    def retrieve_requirements(query: str) -> str:
        """
        Search meeting transcripts and requirement documents for relevant information.
        Returns formatted results with source attribution and chunk IDs.
        
        Args:
            query: Search query to find relevant information
            
        Returns:
            Formatted results with chunk IDs, excerpts, timestamps, and sources
        """
        try:
            response = requests.post(
                f"{REQUIREMENT_SERVICE_URL}/api/requirements/retrieve",
                json={
                    "query": query,
                    "project_id": project_id,
                    "meeting_id": meeting_id,
                    "k": k
                },
                timeout=30
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            
            if not results:
                return "No relevant information found."
            
            # Format results with CHUNK_IDs for LLM to reference
            formatted_output = []
            for idx, result in enumerate(results, start=1):
                chunk_text = f"[CHUNK_{idx}]\n"
                chunk_text += f"Source: {result.get('source', 'unknown')}\n"
                
                # Add source-specific metadata
                if result.get('source') == 'meeting-transcripts':
                    chunk_text += f"Meeting: {result.get('meeting_id', 'N/A')}\n"
                    chunk_text += f"Time: {result.get('start_time', '')} - {result.get('end_time', '')}\n"
                elif result.get('source') == 'custom_requirement':
                    chunk_text += f"File: {result.get('filename', 'N/A')}\n"
                    chunk_text += f"Type: {result.get('file_type', 'N/A')}\n"
                
                # Add truncated text content (limit to 500 chars)
                text_content = result.get('text', '')
                if len(text_content) > 500:
                    text_content = text_content[:500] + "..."
                chunk_text += f"Content: {text_content}\n"
                chunk_text += f"Relevance Score: {result.get('score', 0):.3f}\n"
                
                formatted_output.append(chunk_text)
            
            return "\n\n".join(formatted_output)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    return retrieve_requirements


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG-powered chat with structured responses and references.
    
    Returns answers with:
    - Clear, concise response
    - Array of references (meetings, documents, docs)
    - Confidence level
    - Follow-up question suggestions
    """
    try:
        # First, retrieve the actual data for metadata
        retrieve_response = requests.post(
            f"{REQUIREMENT_SERVICE_URL}/api/requirements/retrieve",
            json={
                "query": request.message,
                "project_id": request.project_id,
                "meeting_id": request.meeting_id,
                "k": request.k
            },
            timeout=30
        )
        retrieve_response.raise_for_status()
        retrieved_data = retrieve_response.json().get("results", [])
        
        # Initialize model
        model = init_chat_model(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            model_provider="azure_openai",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            temperature=0.7,
            max_tokens=2000,
        )
        
        # Create tools
        tools = [
            create_retrieve_tool(request.project_id, request.meeting_id, request.k),
        ]
        
        # Create agent with structured output
        agent = create_agent(
            model,
            tools=tools,
            response_format=ToolStrategy(StructuredChatResponse),
            system_prompt="""You are a helpful AI assistant for project requirements.

**Your task:**
1. ALWAYS use retrieve_requirements tool to search the knowledge base before answering
2. Use the retrieved information to answer the user's question accurately
3. If no relevant information is found, say you couldn't find an answer in the available requirements

**Important - Citing Sources:**
- When you retrieve results, they will have [CHUNK_1], [CHUNK_2] etc. markers
- In your references array, you MUST include the CHUNK_ID in the title field
- Format: "CHUNK_X: [brief description]" where X is the chunk number
- Example title: "CHUNK_1: Authentication discussion" or "CHUNK_2: Database requirements document"
- This is CRITICAL for video playback and document linking to work properly

**Guidelines:**
- Take retrieved information with a grain of salt - there might be noise, spelling mistakes, or incomplete info
- If information seems unclear or incomplete, try searching with different terms
- Provide clear, detailed responses using markdown formatting
- Be confident when you have good sources, indicate uncertainty when sources are ambiguous
"""
        )
        
        # Format chat history
        messages = [
            HumanMessage(content=msg.content) if msg.role == "user" else AIMessage(content=msg.content)
            for msg in request.chat_history
        ]
        messages.append(HumanMessage(content=request.message))
        
        # Invoke agent
        result = agent.invoke({"messages": messages})
        structured_response: StructuredChatResponse = result.get("structured_response")
        
        # Enrich references with full metadata from retrieved data
        enriched_references = []
        for ref in structured_response.references:
            # Extract CHUNK_ID from title (e.g., "CHUNK_1: ..." -> 1)
            import re
            chunk_match = re.search(r'CHUNK_(\d+)', ref.title)
            
            if chunk_match:
                chunk_idx = int(chunk_match.group(1)) - 1  # Convert to 0-based index
                if 0 <= chunk_idx < len(retrieved_data):
                    matched_data = retrieved_data[chunk_idx]
                    
                    # Populate metadata based on source type
                    if matched_data.get('source') == 'meeting-transcripts':
                        ref.source_type = 'meeting'
                        ref.metadata = {
                            'bot_id': matched_data.get('bot_id'),
                            'meeting_id': matched_data.get('meeting_id'),
                            'start_time': matched_data.get('start_time'),
                            'end_time': matched_data.get('end_time'),
                        }
                    elif matched_data.get('source') == 'custom_requirement':
                        ref.source_type = 'document'
                        ref.metadata = {
                            'requirement_id': matched_data.get('requirement_id'),
                            'filename': matched_data.get('filename'),
                            'file_type': matched_data.get('file_type'),
                        }
            
            enriched_references.append(ref)
        
        return ChatResponse(
            answer=structured_response.answer,
            references=enriched_references,
            confidence=structured_response.confidence,
            followup_questions=structured_response.followup_questions,
            project_id=request.project_id
        )
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )
