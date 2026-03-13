#!/usr/bin/env python3
"""
Migration script to upload all existing local downloads to S3 and update database.

This script:
1. Finds all files in the downloads/ directory
2. Uploads them to S3 with proper organization (downloads/{bot_id}/filename)
3. Updates meet_history records with S3 keys
4. Deletes local files after successful upload
5. Removes local path columns from database

Run with: uv run migrate_downloads_to_s3.py
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.s3_storage import get_s3_manager
from core.database import DATABASE_URL, engine
from core.models import MeetHistory

# Load environment variables
load_dotenv()


async def migrate_files_to_s3():
    """Upload all local downloads to S3 and update database"""
    downloads_dir = Path("downloads")
    
    if not downloads_dir.exists():
        print("✓ No downloads directory found - nothing to migrate")
        return
    
    # Get S3 manager
    s3_manager = get_s3_manager()
    
    # Get database session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Find all bot directories
        bot_dirs = [d for d in downloads_dir.iterdir() if d.is_dir()]
        
        if not bot_dirs:
            print("✓ No files to migrate")
            return
        
        print(f"📦 Found {len(bot_dirs)} bot directories to process")
        
        migrated_count = 0
        error_count = 0
        
        for bot_dir in bot_dirs:
            bot_id = bot_dir.name
            print(f"\n🔄 Processing bot: {bot_id}")
            
            # Find meeting record
            meeting = db.query(MeetHistory).filter(
                MeetHistory.bot_id == bot_id
            ).first()
            
            if not meeting:
                print(f"  ⚠️  No database record found for bot {bot_id}")
                continue
            
            # Find all files for this bot
            files = list(bot_dir.glob("*"))
            print(f"  Found {len(files)} files")
            
            for file_path in files:
                try:
                    # Determine file type and generate S3 key
                    filename = file_path.name
                    
                    # Upload to S3
                    s3_key = await s3_manager.upload_file(
                        local_path=file_path,
                        bot_id=bot_id,
                        filename=filename
                    )
                    
                    # Update database based on file type
                    if file_path.suffix == '.mp4':
                        meeting.mp4_s3_key = s3_key
                        print(f"  ✓ Uploaded video: {s3_key}")
                    elif file_path.suffix in ['.mp3', '.flac', '.wav']:
                        meeting.audio_s3_key = s3_key
                        print(f"  ✓ Uploaded audio: {s3_key}")
                    elif file_path.suffix == '.json':
                        meeting.transcript_s3_key = s3_key
                        print(f"  ✓ Uploaded transcript: {s3_key}")
                    else:
                        print(f"  ✓ Uploaded {file_path.suffix}: {s3_key}")
                    
                    migrated_count += 1
                    
                    # Delete local file after successful upload
                    file_path.unlink()
                    
                except Exception as e:
                    print(f"  ✗ Failed to migrate {filename}: {str(e)}")
                    error_count += 1
            
            # Commit changes for this meeting
            db.commit()
            
            # Remove empty bot directory
            try:
                if not any(bot_dir.iterdir()):
                    bot_dir.rmdir()
                    print(f"  ✓ Removed empty directory")
            except Exception as e:
                print(f"  ⚠️  Could not remove directory: {str(e)}")
        
        print(f"\n✅ Migration complete!")
        print(f"   Migrated: {migrated_count} files")
        if error_count > 0:
            print(f"   Errors: {error_count} files")
        
        # Remove empty downloads directory
        try:
            if downloads_dir.exists() and not any(downloads_dir.iterdir()):
                downloads_dir.rmdir()
                print(f"   Removed empty downloads directory")
        except Exception as e:
            print(f"   ⚠️  Could not remove downloads directory: {str(e)}")
            
    finally:
        db.close()


async def drop_local_path_columns():
    """Remove deprecated local path columns from database"""
    print("\n🔧 Removing local path columns from database...")
    
    try:
        with engine.connect() as conn:
            # SQLite doesn't support DROP COLUMN directly
            # We need to create a new table and copy data
            
            # Check if columns exist first
            result = conn.execute(text("PRAGMA table_info(meet_history)"))
            columns = [row[1] for row in result]
            
            local_path_columns = ['mp4_local_path', 'audio_local_path', 'transcript_local_path']
            has_local_columns = any(col in columns for col in local_path_columns)
            
            if not has_local_columns:
                print("✓ Local path columns already removed")
                return
            
            print("  Creating new table without local path columns...")
            
            # Create new table with updated schema
            conn.execute(text("""
                CREATE TABLE meet_history_new (
                    id VARCHAR(36) PRIMARY KEY,
                    project_id VARCHAR(36) NOT NULL,
                    meeting_url VARCHAR(500) NOT NULL,
                    bot_id VARCHAR(255) NOT NULL,
                    bot_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    event_uuid VARCHAR(255),
                    mp4_url VARCHAR(1000),
                    audio_url VARCHAR(1000),
                    mp4_s3_key VARCHAR(500),
                    audio_s3_key VARCHAR(500),
                    transcript_s3_key VARCHAR(500),
                    speakers JSON,
                    duration_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """))
            
            print("  Copying data to new table...")
            
            # Copy data from old table to new table
            conn.execute(text("""
                INSERT INTO meet_history_new (
                    id, project_id, meeting_url, bot_id, bot_name,
                    status, event_uuid, mp4_url, audio_url,
                    mp4_s3_key, audio_s3_key, transcript_s3_key,
                    speakers, duration_seconds, created_at, updated_at
                )
                SELECT 
                    id, project_id, meeting_url, bot_id, bot_name,
                    status, event_uuid, mp4_url, audio_url,
                    mp4_s3_key, audio_s3_key, transcript_s3_key,
                    speakers, duration_seconds, created_at, updated_at
                FROM meet_history
            """))
            
            print("  Replacing old table...")
            
            # Drop old table and rename new one
            conn.execute(text("DROP TABLE meet_history"))
            conn.execute(text("ALTER TABLE meet_history_new RENAME TO meet_history"))
            
            # Recreate indexes
            conn.execute(text("CREATE INDEX idx_meet_history_project_id ON meet_history(project_id)"))
            conn.execute(text("CREATE INDEX idx_meet_history_bot_id ON meet_history(bot_id)"))
            conn.execute(text("CREATE INDEX idx_meet_history_status ON meet_history(status)"))
            
            conn.commit()
            
            print("✓ Successfully removed local path columns")
            
    except Exception as e:
        print(f"✗ Error removing local path columns: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


async def main():
    """Main migration workflow"""
    print("=" * 60)
    print("  MIGRATION: Local Storage → S3")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Upload all files from downloads/ to S3")
    print("  2. Update database records with S3 keys")
    print("  3. Delete local files after successful upload")
    print("  4. Remove local path columns from database")
    print()
    
    response = input("Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        return
    
    print()
    
    # Step 1: Migrate files
    await migrate_files_to_s3()
    
    # Step 2: Drop local path columns
    await drop_local_path_columns()
    
    print()
    print("=" * 60)
    print("  ✅ MIGRATION COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Restart the requirement_gathering service")
    print("  2. Test creating a new meeting")
    print("  3. Verify files are uploaded to S3")
    print()


if __name__ == "__main__":
    asyncio.run(main())
