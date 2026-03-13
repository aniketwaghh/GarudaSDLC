"""
Database migration script to add S3 storage columns to meet_history table.

This script adds the following columns:
- mp4_s3_key: S3 key for video file
- audio_s3_key: S3 key for audio file
- transcript_s3_key: S3 key for transcript file

The local path columns are kept for backward compatibility.
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "garuda.db"

def migrate():
    """Add S3 key columns to meet_history table"""
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Please create the database first by running the services.")
        sys.exit(1)
    
    print(f"📦 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='meet_history'
        """)
        
        if not cursor.fetchone():
            print("❌ Table 'meet_history' does not exist")
            sys.exit(1)
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(meet_history)")
        columns = [row[1] for row in cursor.fetchall()]
        
        columns_to_add = []
        if 'mp4_s3_key' not in columns:
            columns_to_add.append(('mp4_s3_key', 'VARCHAR(500)'))
        if 'audio_s3_key' not in columns:
            columns_to_add.append(('audio_s3_key', 'VARCHAR(500)'))
        if 'transcript_s3_key' not in columns:
            columns_to_add.append(('transcript_s3_key', 'VARCHAR(500)'))
        
        if not columns_to_add:
            print("✅ All S3 columns already exist. Nothing to migrate.")
            return
        
        print(f"🔧 Adding {len(columns_to_add)} columns...")
        
        for column_name, column_type in columns_to_add:
            sql = f"ALTER TABLE meet_history ADD COLUMN {column_name} {column_type}"
            print(f"   Adding column: {column_name}")
            cursor.execute(sql)
        
        conn.commit()
        print(f"✅ Migration completed successfully!")
        print(f"   Added columns: {', '.join([c[0] for c in columns_to_add])}")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  S3 Storage Migration Script")
    print("=" * 60)
    migrate()
    print("=" * 60)
