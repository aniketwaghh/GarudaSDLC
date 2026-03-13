"""
Cleanup script for GarudaSDLC development environment.

This script will:
1. Delete all local downloads
2. Clear meet_history database table
3. Empty S3 vector bucket (garuda-sdlc)
4. Empty S3 media bucket (garuda-sdlc-media)

⚠️  WARNING: This will DELETE all data! Use only in development.
"""

import os
import shutil
import sqlite3
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "garuda.db"
DOWNLOADS_DIR = Path(__file__).parent / "downloads"
VECTOR_BUCKET = os.getenv("AWS_S3_VECTOR_BUCKET_NAME", "garuda-sdlc")
MEDIA_BUCKET = os.getenv("AWS_S3_MEDIA_BUCKET_NAME", "garuda-sdlc-media")
REGION = os.getenv("AWS_REGION", "us-west-2")


def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")


def cleanup_local_downloads():
    """Remove all files from local downloads directory"""
    print(f"{YELLOW}🗑️  Cleaning local downloads...{NC}")
    
    if not DOWNLOADS_DIR.exists():
        print(f"{GREEN}✓ Downloads directory doesn't exist (already clean){NC}")
        return
    
    try:
        # Count files before deletion
        file_count = sum(1 for _ in DOWNLOADS_DIR.rglob('*') if _.is_file())
        
        if file_count == 0:
            print(f"{GREEN}✓ Downloads directory is empty{NC}")
            return
        
        # Delete all contents
        for item in DOWNLOADS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                print(f"  Deleted directory: {item.name}")
            else:
                item.unlink()
                print(f"  Deleted file: {item.name}")
        
        print(f"{GREEN}✓ Deleted {file_count} files from downloads{NC}")
    
    except Exception as e:
        print(f"{RED}✗ Failed to clean downloads: {str(e)}{NC}")


def cleanup_database():
    """Clear meet_history and meeting_schedules tables"""
    print(f"\n{YELLOW}🗑️  Cleaning database...{NC}")
    
    if not DB_PATH.exists():
        print(f"{YELLOW}⚠ Database not found at: {DB_PATH}{NC}")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Clear meet_history
        cursor.execute("DELETE FROM meet_history")
        meet_count = cursor.rowcount
        print(f"  Deleted {meet_count} records from meet_history")
        
        # Clear meeting_schedules
        cursor.execute("DELETE FROM meeting_schedules")
        schedule_count = cursor.rowcount
        print(f"  Deleted {schedule_count} records from meeting_schedules")
        
        conn.commit()
        conn.close()
        
        print(f"{GREEN}✓ Database cleaned successfully{NC}")
    
    except Exception as e:
        print(f"{RED}✗ Failed to clean database: {str(e)}{NC}")


def empty_s3_bucket(bucket_name):
    """Delete all objects from an S3 bucket"""
    print(f"\n{YELLOW}🗑️  Emptying S3 bucket: {bucket_name}...{NC}")
    
    try:
        s3 = boto3.client(
            's3',
            region_name=REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        delete_count = 0
        for page in pages:
            if 'Contents' not in page:
                continue
            
            # Prepare objects for deletion
            objects = [{'Key': obj['Key']} for obj in page['Contents']]
            
            # Delete in batches of 1000 (S3 limit)
            if objects:
                response = s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )
                deleted = len(response.get('Deleted', []))
                delete_count += deleted
                print(f"  Deleted {deleted} objects...")
        
        if delete_count == 0:
            print(f"{GREEN}✓ Bucket is already empty{NC}")
        else:
            print(f"{GREEN}✓ Deleted {delete_count} objects from {bucket_name}{NC}")
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"{YELLOW}⚠ Bucket doesn't exist: {bucket_name}{NC}")
        else:
            print(f"{RED}✗ Failed to empty bucket: {str(e)}{NC}")
    except Exception as e:
        print(f"{RED}✗ Failed to empty bucket: {str(e)}{NC}")


def main():
    print_header("GarudaSDLC Development Cleanup")
    
    print(f"{RED}⚠️  WARNING: This will DELETE all data!{NC}")
    print(f"{RED}   - Local downloads folder{NC}")
    print(f"{RED}   - All meeting history records{NC}")
    print(f"{RED}   - All files in S3 buckets{NC}")
    print()
    
    # Confirmation
    response = input(f"{YELLOW}Are you sure you want to continue? (yes/no): {NC}")
    if response.lower() != 'yes':
        print(f"\n{GREEN}Cleanup cancelled.{NC}")
        return
    
    print()
    
    # 1. Clean local downloads
    cleanup_local_downloads()
    
    # 2. Clean database
    cleanup_database()
    
    # 3. Empty S3 vector bucket
    empty_s3_bucket(VECTOR_BUCKET)
    
    # 4. Empty S3 media bucket
    empty_s3_bucket(MEDIA_BUCKET)
    
    # Summary
    print_header("Cleanup Complete!")
    print(f"{GREEN}✅ All data has been cleaned{NC}")
    print(f"\n{BLUE}Next steps:{NC}")
    print(f"  1. Start fresh meetings")
    print(f"  2. System is ready for new recordings")
    print()


if __name__ == "__main__":
    main()
