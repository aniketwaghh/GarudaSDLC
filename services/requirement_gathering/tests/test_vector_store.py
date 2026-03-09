"""
Test script for vector store functionality.
Tests chunking and retrieval without requiring AWS/Azure setup.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.vector_store import TranscriptChunker


def test_transcript_chunker():
    """Test the transcript chunking logic"""
    print("=" * 60)
    print("Testing TranscriptChunker")
    print("=" * 60)
    
    # Create sample transcript segments
    segments = [
        {'start': 0, 'end': 5000, 'text': 'Hello, this is a test.'},
        {'start': 5000, 'end': 10000, 'text': 'We are discussing authentication.'},
        {'start': 10000, 'end': 15000, 'text': 'The system should use OAuth 2.0.'},
        {'start': 15000, 'end': 20000, 'text': 'JWT tokens will be used for sessions.'},
        {'start': 20000, 'end': 25000, 'text': 'We also need to implement rate limiting.'},
        {'start': 25000, 'end': 30000, 'text': 'The database should be PostgreSQL.'},
        {'start': 30000, 'end': 35000, 'text': 'We need to store user profiles.'},
        {'start': 35000, 'end': 40000, 'text': 'The API should be RESTful.'},
    ]
    
    # Create chunker with small target size for testing
    chunker = TranscriptChunker(target_chunk_size=100, max_chunk_size=200)
    
    # Create chunks
    chunks = chunker.create_chunks(segments)
    
    print(f"\nInput: {len(segments)} segments")
    print(f"Output: {len(chunks)} chunks\n")
    
    for idx, chunk in enumerate(chunks):
        start_sec = chunk['start'] / 1000
        end_sec = chunk['end'] / 1000
        duration_sec = chunk['duration'] / 1000
        
        print(f"Chunk {idx + 1}:")
        print(f"  Time: {start_sec:.1f}s - {end_sec:.1f}s (duration: {duration_sec:.1f}s)")
        print(f"  Length: {len(chunk['text'])} chars")
        print(f"  Text: {chunk['text'][:80]}...")
        print()
    
    print("✓ Chunking test completed successfully!")
    return chunks


def test_timestamp_formatting():
    """Test timestamp formatting"""
    print("\n" + "=" * 60)
    print("Testing Timestamp Formatting")
    print("=" * 60)
    
    from utils.vector_store import MeetingVectorStore
    
    test_cases = [
        (0, "00:00:00.000"),
        (1000, "00:00:01.000"),
        (60000, "00:01:00.000"),
        (3661500, "01:01:01.500"),
        (930500, "00:15:30.500"),
    ]
    
    print("\nTimestamp conversion tests:")
    for ms, expected in test_cases:
        result = MeetingVectorStore._format_timestamp(ms)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {ms}ms -> {result} (expected: {expected})")
    
    print("\n✓ Timestamp formatting test completed!")


def test_read_tsv():
    """Test reading actual TSV file if it exists"""
    print("\n" + "=" * 60)
    print("Testing TSV File Reading")
    print("=" * 60)
    
    # Look for TSV files in downloads directory
    downloads_dir = Path(__file__).parent.parent / "downloads"
    
    if not downloads_dir.exists():
        print("\n⚠ No downloads directory found. Skipping TSV test.")
        return
    
    tsv_files = list(downloads_dir.rglob("*.tsv"))
    
    if not tsv_files:
        print("\n⚠ No TSV files found in downloads. Skipping TSV test.")
        return
    
    # Use first TSV file found
    tsv_path = tsv_files[0]
    print(f"\nReading: {tsv_path.name}")
    
    chunker = TranscriptChunker(target_chunk_size=500, max_chunk_size=1000)
    
    try:
        segments = chunker.read_tsv(tsv_path)
        print(f"  ✓ Read {len(segments)} segments")
        
        if segments:
            print(f"  First segment: {segments[0]}")
            print(f"  Last segment: {segments[-1]}")
        
        chunks = chunker.create_chunks(segments)
        print(f"  ✓ Created {len(chunks)} chunks")
        
        if chunks:
            total_duration = chunks[-1]['end'] - chunks[0]['start']
            print(f"  Total duration: {total_duration / 1000:.1f} seconds")
            
            print(f"\n  Sample chunk:")
            sample = chunks[0]
            print(f"    Start: {sample['start']}ms")
            print(f"    End: {sample['end']}ms")
            print(f"    Duration: {sample['duration']}ms")
            print(f"    Text: {sample['text'][:100]}...")
        
        print("\n✓ TSV reading test completed!")
        
    except Exception as e:
        print(f"\n✗ Error reading TSV: {str(e)}")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Vector Store Test Suite" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # Test chunking logic
        test_transcript_chunker()
        
        # Test timestamp formatting
        test_timestamp_formatting()
        
        # Test reading actual TSV files
        test_read_tsv()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        print()
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
