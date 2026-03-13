"""
Migration script to add total_chunks column to meet_history table.

This migration adds the total_chunks field to track the number of
vector chunks created from meeting transcripts, matching the pattern
used for custom requirements.

Usage:
    python scripts/migrate_add_total_chunks_to_meetings.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import engine

def run_migration():
    """Add total_chunks column to meet_history table"""
    print("🔄 Running migration: Add total_chunks to meet_history")
    
    with engine.connect() as conn:
        try:
            # For SQLite, check if column exists by trying to query it
            try:
                conn.execute(text("SELECT total_chunks FROM meet_history LIMIT 1"))
                print("✓ Column 'total_chunks' already exists in meet_history table")
                return
            except Exception:
                # Column doesn't exist, proceed with adding it
                pass
            
            # Add the column (SQLite syntax)
            conn.execute(text("""
                ALTER TABLE meet_history 
                ADD COLUMN total_chunks INTEGER DEFAULT 0
            """))
            conn.commit()
            
            print("✓ Successfully added 'total_chunks' column to meet_history table")
            print("  Default value: 0")
            print("  Note: Existing meetings will have total_chunks=0 until they are reprocessed")
            
        except Exception as e:
            print(f"✗ Migration failed: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    try:
        run_migration()
        print("\n✅ Migration completed successfully")
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)
