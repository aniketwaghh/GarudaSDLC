"""
Simple test to visualize chunking output from a TSV file.
Usage: python test_chunking_output.py <path_to_tsv_file>
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.vector_store import TranscriptChunker


def test_tsv_chunking(tsv_path: str):
    """
    Test chunking on a specific TSV file and print results.
    
    Args:
        tsv_path: Path to TSV transcript file
    """
    tsv_file = Path(tsv_path)
    
    if not tsv_file.exists():
        print(f"❌ Error: File not found: {tsv_path}")
        return
    
    print("\n" + "=" * 80)
    print(f"📄 Processing: {tsv_file.name}")
    print("=" * 80)
    
    # Create chunker
    chunker = TranscriptChunker(target_chunk_size=500, max_chunk_size=1000)
    
    # Read segments
    print("\n📖 Reading segments...")
    segments = chunker.read_tsv(tsv_file)
    print(f"   ✓ Found {len(segments)} segments")
    
    # Show first few segments
    print("\n📝 First 3 segments:")
    for i, seg in enumerate(segments[:3]):
        print(f"\n   Segment {i+1}:")
        print(f"     Time: {seg['start']}ms - {seg['end']}ms")
        print(f"     Text: {seg['text'][:80]}..." if len(seg['text']) > 80 else f"     Text: {seg['text']}")
    
    # Create chunks
    print("\n\n✂️  Creating chunks...")
    chunks = chunker.create_chunks(segments)
    print(f"   ✓ Created {len(chunks)} chunks")
    
    # Show all chunks with details
    print("\n" + "=" * 80)
    print("📦 CHUNKS (Documents that will be stored in vector DB)")
    print("=" * 80)
    
    for idx, chunk in enumerate(chunks):
        start_sec = chunk['start'] / 1000
        end_sec = chunk['end'] / 1000
        duration_sec = chunk['duration'] / 1000
        
        print(f"\n┌─ Chunk #{idx + 1} " + "─" * 65)
        print(f"│ 🕒 Time Range: {start_sec:.2f}s - {end_sec:.2f}s (duration: {duration_sec:.2f}s)")
        print(f"│ 📏 Length: {len(chunk['text'])} characters")
        print(f"│ 📍 Timestamps: {chunk['start']}ms → {chunk['end']}ms")
        print(f"│")
        print(f"│ 📝 Text:")
        
        # Print text with proper wrapping
        text = chunk['text']
        max_width = 76
        words = text.split()
        line = "│    "
        
        for word in words:
            if len(line) + len(word) + 1 <= max_width:
                line += word + " "
            else:
                print(line.rstrip())
                line = "│    " + word + " "
        
        if line.strip() != "│":
            print(line.rstrip())
        
        print(f"└─" + "─" * 78)
    
    # Summary
    total_chars = sum(len(chunk['text']) for chunk in chunks)
    avg_chars = total_chars / len(chunks) if chunks else 0
    total_duration = segments[-1]['end'] - segments[0]['start'] if segments else 0
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"• Input segments: {len(segments)}")
    print(f"• Output chunks: {len(chunks)}")
    print(f"• Total characters: {total_chars:,}")
    print(f"• Average chunk size: {avg_chars:.0f} characters")
    print(f"• Total duration: {total_duration / 1000:.2f} seconds")
    print(f"• Chunks per minute: {len(chunks) / (total_duration / 60000):.1f}")
    print("=" * 80)
    print("\n✅ Done!\n")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n❌ Usage: python test_chunking_output.py <path_to_tsv_file>")
        print("\nExample:")
        print("  python test_chunking_output.py downloads/bot-id/transcript.tsv")
        
        # Try to find a TSV file automatically
        downloads_dir = Path(__file__).parent.parent / "downloads"
        if downloads_dir.exists():
            tsv_files = list(downloads_dir.rglob("*.tsv"))
            if tsv_files:
                print(f"\n💡 Found {len(tsv_files)} TSV file(s):")
                for f in tsv_files[:5]:
                    print(f"   • {f.relative_to(downloads_dir.parent)}")
                
                if tsv_files:
                    print(f"\n🔄 Using first file: {tsv_files[0].name}")
                    test_tsv_chunking(str(tsv_files[0]))
                    return
        
        sys.exit(1)
    
    tsv_path = sys.argv[1]
    test_tsv_chunking(tsv_path)


if __name__ == "__main__":
    main()
