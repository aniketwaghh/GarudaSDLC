#!/usr/bin/env python3
"""
Create custom_requirements table migration.
Run with: uv run scripts/migrate_add_custom_requirements.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import engine
from core.models import Base, CustomRequirement


def main():
    """Create custom_requirements table"""
    print("=" * 60)
    print("  Creating custom_requirements table")
    print("=" * 60)
    print()
    
    try:
        # Create only the custom_requirements table
        CustomRequirement.__table__.create(engine, checkfirst=True)
        
        print("✅ custom_requirements table created successfully!")
        print()
        print("Table schema:")
        print("  - id (PRIMARY KEY)")
        print("  - project_id (FOREIGN KEY → projects.id)")
        print("  - filename, file_type, file_size")
        print("  - file_s3_key (S3 storage location)")
        print("  - total_chunks (number of vector chunks)")
        print("  - status (processing/completed/failed)")
        print("  - uploaded_by (user ID from Cognito)")
        print("  - created_at, updated_at")
        print()
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
