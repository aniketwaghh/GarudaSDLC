"""
RAG Chat endpoint with LangChain agent for querying requirements.
"""

import os
import requests
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain.agents import create_agent
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


class ChatRequest(BaseModel):
    """Request model for RAG chat"""
    message: str = Field(..., description="User's question or query")
    project_id: str = Field(..., description="Project ID to search within")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="Previous chat messages")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID filter")
    k: int = Field(5, ge=1, le=10, description="Number of context chunks to retrieve")


class RetrievedChunk(BaseModel):
    """Retrieved context chunk"""
    text: str
    score: float
    bot_id: str
    meeting_id: str
    start_time: str
    end_time: str


class ChatResponse(BaseModel):
    """Response model for RAG chat"""
    message: str = Field(..., description="AI assistant's response")
    retrieved_chunks: List[RetrievedChunk] = Field(..., description="Retrieved context used")
    project_id: str = Field(..., description="Project ID")
    total_chunks: int = Field(..., description="Number of chunks retrieved")


def create_retrieve_tool(project_id: str, meeting_id: Optional[str] = None, k: int = 5):
    """Create a tool that retrieves requirements from the vector store"""
    
    @tool
    def retrieve_requirements(query: str) -> str:
        """
        Retrieve relevant meeting transcript chunks and requirements based on a search query.
        Use this tool to search for information from past meetings, discussions, and requirements.
        
        Args:
            query: The search query to find relevant information
            
        Returns:
            Retrieved transcript chunks with context and timestamps
        """
        try:
            # Call the requirement_gathering service retrieve endpoint
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
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return "No relevant information found in the meeting transcripts."
            
            # Format results for the LLM (avoid template variable interpretation)
            formatted_results = []
            for i, chunk in enumerate(results, 1):
                formatted_results.append(
                    f"[Chunk {i}]\n"
                    f"Meeting: {chunk['meeting_id']}\n"
                    f"Time: {chunk['start_time']} - {chunk['end_time']}\n"
                    f"Score: {chunk['score']:.4f}\n"
                    f"Content: {chunk['text']}\n"
                )
            
            return "\n---\n".join(formatted_results)
            
        except requests.exceptions.RequestException as e:
            return f"Error retrieving requirements: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
    
    return retrieve_requirements


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG-powered chat endpoint that answers questions using meeting transcripts and requirements.
    
    This endpoint uses a LangChain agent with Azure OpenAI to:
    1. Understand your question
    2. Retrieve relevant information from meeting transcripts
    3. Provide a detailed answer with citations
    
    **Example questions:**
    - "What authentication methods were discussed?"
    - "What are the main features for the dashboard?"
    - "What database should we use and why?"
    - "What performance requirements were mentioned?"
    """
    try:
        print(f"\n🤖 Processing chat request:")
        print(f"   Project: {request.project_id}")
        print(f"   Question: {request.message}")
        
        # Initialize chat model
        model = init_chat_model(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            model_provider="azure_openai",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            temperature=0.7,
            max_tokens=2000,
        )
        
        # Create retrieve tool
        tools = [create_retrieve_tool(request.project_id, request.meeting_id, request.k)]
        
        # Create agent with system prompt
        agent = create_agent(
            model,
            tools=tools,
            system_prompt="""You are a helpful AI assistant that answers questions about project requirements and meeting discussions.

You have access to a tool that can search through meeting transcripts and requirements documentation.

When answering questions:
1. Use the retrieve_requirements tool to search for relevant information
2. Provide clear, concise answers based on the retrieved information
3. Always cite your sources by mentioning the meeting ID and timestamp when referencing specific information
4. If the retrieved information doesn't contain the answer, say so clearly
5. Be honest about uncertainty - don't make up information
6. Structure your answer with clear sections if covering multiple topics

Format citations like: *[Meeting: <meeting_id>, Time: <start_time>-<end_time>]*
"""
        )
        
        # Format chat history
        chat_history = []
        for msg in request.chat_history:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                chat_history.append(AIMessage(content=msg.content))
        
        # Invoke agent
        result = agent.invoke({
            "messages": chat_history + [HumanMessage(content=request.message)]
        })
        
        # Extract the answer from the result
        messages = result.get("messages", [])
        answer = messages[-1].content if messages else "I couldn't generate a response."
        
        # Retrieve the chunks that were used (by calling retrieve one more time)
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
        retrieve_data = retrieve_response.json()
        
        # Format retrieved chunks
        retrieved_chunks = [
            RetrievedChunk(
                text=chunk["text"],
                score=chunk["score"],
                bot_id=chunk["bot_id"],
                meeting_id=chunk["meeting_id"],
                start_time=chunk["start_time"],
                end_time=chunk["end_time"]
            )
            for chunk in retrieve_data.get("results", [])
        ]
        
        print(f"✅ Response generated with {len(retrieved_chunks)} chunks")
        
        return ChatResponse(
            message=answer,
            retrieved_chunks=retrieved_chunks,
            project_id=request.project_id,
            total_chunks=len(retrieved_chunks)
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to requirement service: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )
