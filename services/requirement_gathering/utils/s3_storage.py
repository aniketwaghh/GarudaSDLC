"""
S3 Storage utility for managing meeting recordings and files.
Provides upload, download, and presigned URL generation for private S3 bucket.
"""

import os
import boto3
from botocore.config import Config
from pathlib import Path
from typing import Optional, Dict
from botocore.exceptions import ClientError


class S3StorageManager:
    """Manage S3 storage operations for meeting recordings"""
    
    def __init__(self):
        """Initialize S3 client with configuration from environment"""
        # Use dedicated media bucket for videos/audio/transcripts
        self.bucket_name = os.getenv("AWS_S3_MEDIA_BUCKET_NAME", "garuda-sdlc-media")
        self.region = os.getenv("AWS_REGION", "us-west-2")
        
        # Configure S3 client to use regional endpoint and signature v4
        s3_config = Config(
            region_name=self.region,
            signature_version='s3v4',
            s3={
                'addressing_style': 'virtual'
            }
        )
        
        # Initialize S3 client with regional endpoint
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            config=s3_config,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        print(f"✓ S3 Storage Manager initialized for bucket: {self.bucket_name} (region: {self.region})")
    
    def _get_s3_key(self, bot_id: str, filename: str) -> str:
        """
        Generate S3 key with proper prefix structure.
        
        Structure: downloads/{bot_id}/{filename}
        
        Args:
            bot_id: Meeting/bot ID
            filename: Name of the file
            
        Returns:
            S3 key path
        """
        return f"downloads/{bot_id}/{filename}"
    
    async def upload_file(
        self, 
        local_path: Path, 
        bot_id: str, 
        filename: Optional[str] = None
    ) -> str:
        """
        Upload a file to S3.
        
        Args:
            local_path: Path to local file
            bot_id: Meeting/bot ID for organizing files
            filename: Optional custom filename (defaults to local filename)
            
        Returns:
            S3 key of uploaded file
            
        Raises:
            Exception if upload fails
        """
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        
        if filename is None:
            filename = local_path.name
        
        s3_key = self._get_s3_key(bot_id, filename)
        
        try:
            # Determine content type based on extension
            content_type = self._get_content_type(filename)
            
            extra_args = {
                'ContentType': content_type
            }
            
            # Upload file
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            print(f"✓ Uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            print(f"✗ Failed to upload to S3: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")
    
    async def download_and_upload(
        self, 
        url: str, 
        bot_id: str, 
        filename: str,
        temp_dir: Optional[Path] = None
    ) -> str:
        """
        Download a file from URL and upload directly to S3.
        
        Args:
            url: URL to download from
            bot_id: Meeting/bot ID
            filename: Filename for the uploaded file
            temp_dir: Optional temporary directory for download
            
        Returns:
            S3 key of uploaded file
        """
        import requests
        import tempfile
        
        s3_key = self._get_s3_key(bot_id, filename)
        
        try:
            # Download file
            print(f"⬇ Downloading: {url}")
            response = requests.get(url, timeout=300.0, stream=True)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                temp_path = Path(temp_file.name)
            
            # Upload to S3
            content_type = self._get_content_type(filename)
            extra_args = {'ContentType': content_type}
            
            self.s3_client.upload_file(
                str(temp_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Clean up temp file
            temp_path.unlink()
            
            print(f"✓ Downloaded and uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except Exception as e:
            print(f"✗ Failed to download and upload: {str(e)}")
            raise Exception(f"Download and upload failed: {str(e)}")
    
    def get_presigned_url(
        self, 
        s3_key: str, 
        expiration: int = 3600,
        inline: bool = True
    ) -> str:
        """
        Generate a presigned URL for accessing a private S3 object.
        
        Args:
            s3_key: S3 key of the object
            expiration: URL expiration time in seconds (default: 1 hour)
            inline: If True, sets Content-Disposition to inline for browser viewing
            
        Returns:
            Presigned URL
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': s3_key
            }
            
            # Set Content-Disposition to inline for viewing in browser
            if inline:
                # Extract filename from s3_key
                filename = s3_key.split('/')[-1]
                params['ResponseContentDisposition'] = f'inline; filename="{filename}"'
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            print(f"✓ Generated presigned URL for: {s3_key} (expires in {expiration}s, inline={inline})")
            return url
            
        except ClientError as e:
            print(f"✗ Failed to generate presigned URL: {str(e)}")
            raise Exception(f"Presigned URL generation failed: {str(e)}")
    
    def list_files(self, bot_id: str) -> list[Dict[str, any]]:
        """
        List all files for a specific bot/meeting.
        
        Args:
            bot_id: Meeting/bot ID
            
        Returns:
            List of file information dictionaries
        """
        prefix = f"downloads/{bot_id}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'filename': obj['Key'].split('/')[-1]
                    })
            
            return files
            
        except ClientError as e:
            print(f"✗ Failed to list files: {str(e)}")
            return []
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 key to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: S3 key to delete
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            print(f"✓ Deleted from S3: {s3_key}")
            return True
            
        except ClientError as e:
            print(f"✗ Failed to delete from S3: {str(e)}")
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """
        Determine content type based on file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            MIME type string
        """
        extension = filename.lower().split('.')[-1]
        
        content_types = {
            'mp4': 'video/mp4',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'json': 'application/json',
            'txt': 'text/plain',
            'srt': 'text/plain',
            'vtt': 'text/vtt',
            'tsv': 'text/tab-separated-values',
        }
        
        return content_types.get(extension, 'application/octet-stream')


# Singleton instance
_s3_manager: Optional[S3StorageManager] = None


def get_s3_manager() -> S3StorageManager:
    """
    Get singleton instance of S3 Storage Manager.
    
    Returns:
        S3StorageManager instance
    """
    global _s3_manager
    
    if _s3_manager is None:
        _s3_manager = S3StorageManager()
    
    return _s3_manager
