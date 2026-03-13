"""
Vector store utilities for storing and retrieving meeting transcripts.
Uses AWS S3 Vectors with Azure OpenAI embeddings.
"""

import csv
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_openai import AzureOpenAIEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.models import ChunkContent


class TranscriptChunker:
    """
    Intelligent chunker for transcript data.
    Combines small transcript segments into larger chunks while preserving timestamps.
    """
    
    def __init__(self, target_chunk_size: int = 500, max_chunk_size: int = 1000):
        """
        Args:
            target_chunk_size: Target size for chunks in characters (default: 500)
            max_chunk_size: Maximum chunk size in characters (default: 1000)
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def read_tsv(self, tsv_path: Path) -> List[Dict[str, Any]]:
        """
        Read TSV transcript file and return segments.
        
        Args:
            tsv_path: Path to TSV file
            
        Returns:
            List of segments with start, end, and text
        """
        segments = []
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                segments.append({
                    'start': int(row['start']),  # in milliseconds
                    'end': int(row['end']),      # in milliseconds
                    'text': row['text'].strip()
                })
        return segments
    
    def create_chunks(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine small segments into larger chunks while preserving timestamps.
        Uses RecursiveCharacterTextSplitter for proper sentence/paragraph boundaries.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            List of chunks with aggregated text and timestamp metadata
        """
        if not segments:
            return []
        
        # Combine all segments into full text
        full_text = ' '.join(seg['text'] for seg in segments)
        
        # Use LangChain's text splitter for smart chunking at sentence boundaries
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.target_chunk_size,
            chunk_overlap=50,  # Small overlap for context continuity
        )
        
        # Split text into chunks
        text_chunks = text_splitter.split_text(full_text)
        
        # Build position map: character position -> segment info
        char_to_segment = []
        current_pos = 0
        for segment in segments:
            segment_text = segment['text']
            for _ in range(len(segment_text)):
                char_to_segment.append(segment)
            current_pos += len(segment_text)
            # Add space position (maps to current segment)
            if segment != segments[-1]:  # Don't add space after last segment
                char_to_segment.append(segment)
                current_pos += 1
        
        # Map each chunk to timestamps
        chunks = []
        search_start = 0
        
        for chunk_text in text_chunks:
            # Find chunk position in full text
            chunk_start_pos = full_text.find(chunk_text, search_start)
            if chunk_start_pos == -1:
                continue
            
            chunk_end_pos = chunk_start_pos + len(chunk_text) - 1
            
            # Get timestamps from first and last character positions
            if chunk_start_pos < len(char_to_segment) and chunk_end_pos < len(char_to_segment):
                start_segment = char_to_segment[chunk_start_pos]
                end_segment = char_to_segment[chunk_end_pos]
                
                chunks.append({
                    'text': chunk_text,
                    'start': start_segment['start'],
                    'end': end_segment['end'],
                    'duration': end_segment['end'] - start_segment['start']
                })
            
            search_start = chunk_start_pos + 1
        
        return chunks


class MeetingVectorStore:
    """
    Manages vector storage for meeting transcripts in AWS S3 Vectors.
    """
    
    def __init__(
        self,
        vector_bucket_name: str,
        index_name: str,
        azure_openai_endpoint: str,
        azure_openai_api_key: str,
        azure_openai_deployment: str,
        azure_openai_api_version: str = "2024-02-01",
        aws_region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize the vector store with Azure OpenAI embeddings.
        
        Args:
            vector_bucket_name: Name of S3 vector bucket
            index_name: Name of vector index
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_api_key: Azure OpenAI API key
            azure_openai_deployment: Azure OpenAI embedding deployment name
            azure_openai_api_version: API version (default: "2024-02-01")
            aws_region: AWS region (default: "us-east-1")
            aws_access_key_id: AWS access key ID (optional)
            aws_secret_access_key: AWS secret access key (optional)
        """
        # Initialize Azure OpenAI embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            azure_deployment=azure_openai_deployment,
            api_version=azure_openai_api_version,
        )
        
        # Initialize S3 Vectors store
        # Non-filterable metadata keys are for display-only fields
        # These fields don't count toward the 2048 byte filterable metadata limit
        # Filterable fields (ONLY what we query by): source, project_id, meeting_id
        # Everything else is non-filterable for maximum safety
        # NOTE: This configuration is set during index creation and cannot be changed later
        self.vector_store = AmazonS3Vectors(
            vector_bucket_name=vector_bucket_name,
            index_name=index_name,
            embedding=self.embeddings,
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            distance_metric="cosine",
            create_index_if_not_exist=True,
            page_content_metadata_key=None,  # Don't store content in metadata to avoid 2048 byte limit
            non_filterable_metadata_keys=[
                # Chunk reference (stored in DB)
                'chunk_id',
                # Meeting metadata (display only)
                'start_time_formatted', 
                'end_time_formatted',
                'bot_id',
                'duration_ms',
                # Custom requirement metadata (display only)
                'requirement_id',
                'file_type',
                'chunk_index',
                'filename',
                'total_chunks'
            ],
        )
        
        self.chunker = TranscriptChunker()
    
    async def process_and_store_transcript(
        self,
        tsv_path: Path,
        bot_id: str,
        meeting_id: str,
        project_id: str,
        db: Session,
    ) -> int:
        """
        Process transcript TSV file, create chunks, and store in vector database.
        
        Args:
            tsv_path: Path to TSV transcript file
            bot_id: Bot ID from MeetingBaaS
            meeting_id: Meeting record ID from database
            project_id: Project ID
            db: Database session for storing chunk content
            
        Returns:
            Number of chunks stored
        """
        # Read and chunk transcript
        segments = self.chunker.read_tsv(tsv_path)
        chunks = self.chunker.create_chunks(segments)
        
        if not chunks:
            return 0
        
        # Store chunks in database and prepare documents for vectors
        documents = []
        for idx, chunk in enumerate(chunks):
            # Generate unique chunk ID
            chunk_id = str(uuid.uuid4())
            
            # Store actual content in database
            chunk_content = ChunkContent(
                chunk_id=chunk_id,
                content=chunk['text']
            )
            db.add(chunk_content)
            
            # Create vector document WITH actual text content for embeddings
            # Even though content is in DB, we need text here for Azure OpenAI embeddings
            doc = Document(
                page_content=chunk['text'],  # Include actual text for proper embeddings
                metadata={
                    'chunk_id': chunk_id,  # Reference to DB content
                    'source': 'meeting-transcripts',  # Consistent naming with chat.py
                    'project_id': project_id,
                    'meeting_id': meeting_id,
                    'bot_id': bot_id,
                    'chunk_index': idx,
                    'start_time_ms': chunk['start'],
                    'end_time_ms': chunk['end'],
                    'duration_ms': chunk['duration'],
                    'start_time_formatted': self._format_timestamp(chunk['start']),
                    'end_time_formatted': self._format_timestamp(chunk['end']),
                }
            )
            documents.append(doc)
        
        # Commit chunk content to database
        db.commit()
        
        # Store in S3 Vectors
        # Generate IDs for documents (format: {meeting_id}_{chunk_index})
        ids = [f"{meeting_id}_{idx}" for idx in range(len(documents))]
        self.vector_store.add_documents(documents, ids=ids)
        
        return len(documents)
    
    async def add_text(
        self,
        text: str,
        metadata: Dict[str, Any],
        db: Session,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a single text chunk to vector store.
        
        Args:
            text: Text content to add
            metadata: Metadata for the chunk
            db: Database session for storing chunk content
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        # Generate unique chunk ID
        chunk_id = str(uuid.uuid4())
        
        # Store actual content in database
        chunk_content = ChunkContent(
            chunk_id=chunk_id,
            content=text
        )
        db.add(chunk_content)
        db.commit()
        
        # Add chunk_id to metadata
        metadata_with_chunk = {**metadata, 'chunk_id': chunk_id}
        
        # Create document WITH actual text content for embeddings
        # Even though content is in DB, we need text here for Azure OpenAI embeddings
        doc = Document(
            page_content=text,  # Include actual text for proper embeddings
            metadata=metadata_with_chunk
        )
        
        # Generate ID if not provided
        if not doc_id:
            doc_id = f"{metadata.get('requirement_id', uuid.uuid4())}_{metadata.get('chunk_index', 0)}"
        
        # Add to vector store
        self.vector_store.add_documents([doc], ids=[doc_id])
        
        return doc_id
    
    def retrieve_requirements(
        self,
        query: str,
        project_id: str,
        db: Session,
        k: int = 5,
        source_type: Optional[str] = None,  # 'meeting' or 'custom_requirement'
        meeting_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks based on query.
        
        Args:
            query: Search query
            project_id: Project ID to filter results
            k: Number of results to return (default: 5)
            source_type: Filter by source type ('meeting-transcripts' or 'custom_requirement')
            meeting_id: Optional meeting ID to filter specific meeting
            
        Returns:
            List of relevant chunks with metadata and scores
        """
        # Build metadata filter - always filter by project
        filter_dict = {'project_id': {'$eq': project_id}}
        
        # Add additional filters if provided
        filters = []
        if source_type:
            filters.append({'source': {'$eq': source_type}})
        if meeting_id:
            filters.append({'meeting_id': {'$eq': meeting_id}})
        
        if filters:
            filter_dict = {
                '$and': [
                    {'project_id': {'$eq': project_id}},
                    *filters
                ]
            }
        
        print(f"🔍 Vector search query: {query}")
        print(f"🔍 Filter: {filter_dict}")
        print(f"🔍 k: {k}")
        
        # Perform similarity search with AWS S3 Vectors filtering
        results = self.vector_store.similarity_search_with_score(
            query,
            k=k,
            filter=filter_dict
        )
        
        print(f"✅ Retrieved {results} filtered results from AWS S3 Vectors")
        
        # Fetch actual content from database for all chunks
        chunk_ids = [doc.metadata.get('chunk_id') for doc, _ in results if doc.metadata.get('chunk_id')]
        print(f"🔍 Looking up chunk_ids in database: {chunk_ids}")
        
        chunk_contents = {}
        if chunk_ids:
            chunks_from_db = db.query(ChunkContent).filter(ChunkContent.chunk_id.in_(chunk_ids)).all()
            chunk_contents = {chunk.chunk_id: chunk.content for chunk in chunks_from_db}
            print(f"✅ Found {len(chunk_contents)} chunks in database")
            if len(chunk_contents) < len(chunk_ids):
                missing_ids = set(chunk_ids) - set(chunk_contents.keys())
                print(f"⚠️  Missing chunks in database: {missing_ids}")
        
        # Format results based on source type
        formatted_results = []
        for doc, score in results:
            metadata = doc.metadata
            source = metadata.get('source', metadata.get('type'))  # Support both field names
            
            # Get actual text content from database or page_content
            chunk_id = metadata.get('chunk_id')
            text_content = chunk_contents.get(chunk_id) if chunk_id else None
            
            # If not found in DB, try page_content from vector (for newer vectors with text)
            if not text_content and doc.page_content:
                text_content = doc.page_content
                print(f"ℹ️  Using page_content for chunk {chunk_id}")
            
            # If still no content, log warning
            if not text_content:
                print(f"⚠️  No text content found for chunk {chunk_id} (source: {source})")
                text_content = "[Content not available]"
            
            result = {
                'text': text_content,
                'score': score,
                'metadata': metadata,
                'source': source,
                'project_id': metadata.get('project_id'),
            }
            
            # Add source-specific fields
            if source == 'meeting-transcripts' or source == 'meeting':
                result.update({
                    'bot_id': metadata.get('bot_id'),
                    'meeting_id': metadata.get('meeting_id'),
                    'start_time': metadata.get('start_time_formatted'),
                    'end_time': metadata.get('end_time_formatted'),
                    'duration_ms': metadata.get('duration_ms'),
                })
            elif source == 'custom_requirement':
                result.update({
                    'requirement_id': metadata.get('requirement_id'),
                    'filename': metadata.get('filename'),
                    'file_type': metadata.get('file_type'),
                    'file_s3_key': metadata.get('file_s3_key'),
                    'chunk_index': metadata.get('chunk_index'),
                    'total_chunks': metadata.get('total_chunks'),
                })
            
            formatted_results.append(result)
            print("formated res: ", formatted_results)
        
        return formatted_results
    
    def delete_vectors_by_requirement(
        self,
        requirement_id: str,
        db: Session
    ) -> int:
        """
        Delete all vectors for a specific custom requirement.
        
        Args:
            requirement_id: Custom requirement ID
            db: Database session
            
        Returns:
            Number of vectors deleted
        """
        try:
            print(f"🗑️  Deleting vectors for requirement: {requirement_id}")
            
            # Query for chunks with this requirement_id
            # AWS S3 Vectors doesn't support delete by metadata, so we need to track IDs
            # For custom requirements, IDs are: {requirement_id}_{chunk_index}
            from core.models import CustomRequirement
            
            requirement = db.query(CustomRequirement).filter(
                CustomRequirement.id == requirement_id
            ).first()
            
            if not requirement:
                print(f"⚠️  Requirement not found: {requirement_id}")
                return 0
            
            total_chunks = requirement.total_chunks or 0
            deleted_count = 0
            
            # Delete vectors by their IDs
            for idx in range(total_chunks):
                doc_id = f"{requirement_id}_{idx}"
                try:
                    self.vector_store.delete([doc_id])
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to delete vector {doc_id}: {str(e)}")
            
            # Delete chunk content from database
            chunk_ids = []
            # We need to query ChunkContent to find chunks with this requirement_id in metadata
            # Since we don't have a direct link, we'll need to query via vector store results
            
            print(f"✓ Deleted {deleted_count} vectors for requirement")
            return deleted_count
            
        except Exception as e:
            print(f"✗ Failed to delete vectors: {str(e)}")
            return 0
    
    def delete_vectors_by_meeting(
        self,
        meeting_id: str,
        db: Session
    ) -> int:
        """
        Delete all vectors for a specific meeting.
        
        Args:
            meeting_id: Meeting ID
            db: Database session
            
        Returns:
            Number of vectors deleted
        """
        try:
            print(f"🗑️  Deleting vectors for meeting: {meeting_id}")
            
            # Query for chunks with this meeting_id
            from core.models import MeetHistory
            
            meeting = db.query(MeetHistory).filter(
                MeetHistory.id == meeting_id
            ).first()
            
            if not meeting:
                print(f"⚠️  Meeting not found: {meeting_id}")
                return 0
            
            total_chunks = meeting.total_chunks or 0
            deleted_count = 0
            
            # Delete vectors by their IDs (format: {meeting_id}_{chunk_index})
            for idx in range(total_chunks):
                doc_id = f"{meeting_id}_{idx}"
                try:
                    self.vector_store.delete([doc_id])
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to delete vector {doc_id}: {str(e)}")
            
            print(f"✓ Deleted {deleted_count} vectors for meeting")
            return deleted_count
            
        except Exception as e:
            print(f"✗ Failed to delete vectors: {str(e)}")
            return 0
    
    def delete_chunk_contents(
        self,
        chunk_ids: List[str],
        db: Session
    ) -> int:
        """
        Delete chunk contents from database.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            db: Database session
            
        Returns:
            Number of chunks deleted
        """
        try:
            from core.models import ChunkContent
            
            deleted = db.query(ChunkContent).filter(
                ChunkContent.chunk_id.in_(chunk_ids)
            ).delete(synchronize_session=False)
            
            db.commit()
            print(f"✓ Deleted {deleted} chunk contents from database")
            return deleted
            
        except Exception as e:
            print(f"✗ Failed to delete chunk contents: {str(e)}")
            db.rollback()
            return 0

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        """
        Format milliseconds to HH:MM:SS.mmm format.
        
        Args:
            ms: Milliseconds
            
        Returns:
            Formatted timestamp string
        """
        seconds = ms // 1000
        milliseconds = ms % 1000
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def get_vector_store() -> MeetingVectorStore:
    """
    Factory function to create vector store instance from environment variables.
    
    Returns:
        Configured MeetingVectorStore instance
    """
    return MeetingVectorStore(
        vector_bucket_name=os.getenv("AWS_S3_VECTOR_BUCKET_NAME"),
        index_name=os.getenv("AWS_S3_VECTOR_INDEX_NAME", "meeting-transcripts"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
