#!/usr/bin/env python3
"""
Delete the AWS S3 Vectors index to allow recreation with new configuration.
Run this script to fix the metadata size limit issue.
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VECTOR_BUCKET = os.getenv("AWS_S3_VECTOR_BUCKET_NAME", "garuda-sdlc")
INDEX_NAME = "requirements-gadhering-4"  # Note: keeping original typo
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def delete_index():
    """Delete all files in the vector index"""
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    print(f"🗑️  Deleting vector index: {INDEX_NAME} from bucket: {VECTOR_BUCKET}")
    
    try:
        # List all objects with the index prefix
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=VECTOR_BUCKET, Prefix=f'{INDEX_NAME}/')
        
        deleted_count = 0
        for page in pages:
            if 'Contents' not in page:
                print("ℹ️  Index is empty or doesn't exist")
                break
                
            # Delete objects in batches
            objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
            
            if objects_to_delete:
                response = s3.delete_objects(
                    Bucket=VECTOR_BUCKET,
                    Delete={'Objects': objects_to_delete}
                )
                deleted_count += len(response.get('Deleted', []))
                
                for obj in response.get('Deleted', []):
                    print(f"  ✓ Deleted: {obj['Key']}")
                
                for error in response.get('Errors', []):
                    print(f"  ✗ Error deleting {error['Key']}: {error['Message']}")
        
        print(f"\n✅ Successfully deleted {deleted_count} objects")
        print(f"ℹ️  The index will be recreated automatically on next upload with new configuration:")
        print(f"   - Filterable fields: source, project_id, requirement_id, file_type, chunk_index")
        print(f"   - Non-filterable: filename, total_chunks, char_count")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("AWS S3 Vectors Index Deletion Script")
    print("=" * 60)
    print()
    
    confirm = input(f"Are you sure you want to delete index '{INDEX_NAME}'? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Aborted")
        exit(1)
    
    print()
    if delete_index():
        print()
        print("🎉 Done! Now restart your services and try uploading again.")
        print()
        print("Next steps:")
        print("  1. cd services/requirement_gathering && uv run main.py")
        print("  2. Upload aniket_Resume.pdf again")
        print("  3. It should succeed with the new metadata configuration")
    else:
        print("❌ Deletion failed")
        exit(1)
