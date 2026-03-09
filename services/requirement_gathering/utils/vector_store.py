"""
Vector store utilities for storing and retrieving meeting transcripts.
Uses AWS S3 Vectors with Azure OpenAI embeddings.
"""

import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_openai import AzureOpenAIEmbeddings
from langchain_aws.vectorstores.s3_vectors import AmazonS3Vectors
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


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
        # Non-filterable metadata keys are for display-only fields (formatted timestamps)
        # All other metadata fields (type, project_id, meeting_id, etc.) will be filterable
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
            non_filterable_metadata_keys=['start_time_formatted', 'end_time_formatted'],
        )
        
        self.chunker = TranscriptChunker()
    
    async def process_and_store_transcript(
        self,
        tsv_path: Path,
        bot_id: str,
        meeting_id: str,
        project_id: str,
    ) -> int:
        """
        Process transcript TSV file, create chunks, and store in vector database.
        
        Args:
            tsv_path: Path to TSV transcript file
            bot_id: Bot ID from MeetingBaaS
            meeting_id: Meeting record ID from database
            project_id: Project ID
            
        Returns:
            Number of chunks stored
        """
        # Read and chunk transcript
        segments = self.chunker.read_tsv(tsv_path)
        chunks = self.chunker.create_chunks(segments)
        
        if not chunks:
            return 0
        
        # Convert chunks to LangChain documents with metadata
        documents = []
        for idx, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk['text'],
                metadata={
                    'type': 'meeting-transcripts',
                    'bot_id': bot_id,
                    'meeting_id': meeting_id,
                    'project_id': project_id,
                    'chunk_index': idx,
                    'start_time_ms': chunk['start'],
                    'end_time_ms': chunk['end'],
                    'duration_ms': chunk['duration'],
                    'start_time_formatted': self._format_timestamp(chunk['start']),
                    'end_time_formatted': self._format_timestamp(chunk['end']),
                }
            )
            documents.append(doc)
        
        # Store in S3 Vectors
        # Generate IDs for documents (format: {meeting_id}_{chunk_index})
        ids = [f"{meeting_id}_{idx}" for idx in range(len(documents))]
        self.vector_store.add_documents(documents, ids=ids)
        
        return len(documents)
    
    def retrieve_requirements(
        self,
        query: str,
        project_id: str,
        k: int = 5,
        meeting_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant transcript chunks based on query.
        
        Args:
            query: Search query
            project_id: Project ID to filter results
            k: Number of results to return (default: 5)
            meeting_id: Optional meeting ID to filter specific meeting
            
        Returns:
            List of relevant chunks with metadata and scores
        """
        # Build metadata filter using AWS S3 Vectors filter syntax
        # See: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-metadata-filtering.html
        
        # Try simple filter first - just project_id
        filter_dict = {'project_id': {'$eq': project_id}}
        
        if meeting_id:
            # Add meeting_id filter
            filter_dict = {
                '$and': [
                    {'project_id': {'$eq': project_id}},
                    {'meeting_id': {'$eq': meeting_id}}
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
        
        print(f"✅ Retrieved {len(results)} filtered results from AWS S3 Vectors")
        
        # Format results
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                'text': doc.page_content,
                'score': score,
                'metadata': doc.metadata,
                'type': doc.metadata.get('type'),
                'bot_id': doc.metadata.get('bot_id'),
                'meeting_id': doc.metadata.get('meeting_id'),
                'project_id': doc.metadata.get('project_id'),
                'start_time': doc.metadata.get('start_time_formatted'),
                'end_time': doc.metadata.get('end_time_formatted'),
                'duration_ms': doc.metadata.get('duration_ms'),
            })
        
        return formatted_results
    
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
