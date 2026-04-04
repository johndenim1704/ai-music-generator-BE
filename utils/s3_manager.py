from dotenv import load_dotenv
load_dotenv()
import boto3
from config.s3_config import S3Config
import os
from botocore.exceptions import NoCredentialsError
from datetime import timedelta
from urllib.parse import urlparse
import io
from fastapi.responses import StreamingResponse
from fastapi import UploadFile
from typing import Optional
import urllib.parse


# Load environment variables
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")

class S3Manager:
    def __init__(self):
        self.s3_client = S3Config().get_client()
        self.bucket_name = BUCKET_NAME
        self.region = AWS_REGION

    def upload_file(self, file_path: str, s3_key: str):
        """Uploads a file to the specified S3 bucket"""
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            file_url = self.get_file_url(s3_key)
            return file_url
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except NoCredentialsError:
            print("Credentials not available.")
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None

    def delete_file(self, s3_key: str):
        """Deletes a file from the S3 bucket"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return None

    def delete_folder(self, folder_path: str):
        """Deletes a folder (all objects under a prefix) from the S3 bucket"""
        try:

            # Ensure the folder path ends with a slash
            if not folder_path.endswith('/'):
                folder_path += '/'

            # List all objects under the folder
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=folder_path)

            # Check if objects exist
            if 'Contents' in response:
                # Prepare the list of keys to delete
                delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]

                # Delete all found objects
                result = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_keys}
                )

               
            else:
                print("No objects found under the specified prefix.")

        except Exception as e:
            print(f"Error deleting folder: {e}")
            return None


    def download_file(self, key: str, destination_path: str):
        self.s3_client.download_file(self.bucket_name, key, destination_path)

    def generate_s3_key(self, artist: str, track_title: str, file_type: str, filename: str) -> str:
        artist_slug = artist.lower().replace(" ", "-")
        track_title_slug = track_title.lower().replace(" ", "-")
        file_type = file_type.lower()
        filename = filename.lower().replace(" ", "-")
        s3_key = f"music/{artist_slug}/{track_title_slug}/{file_type}/{filename}"
        print(f"Generated S3 key: {s3_key}")
        return s3_key



    def get_file_url(self, s3_key: str) -> str:
        """Generates the S3 URL for a file using its key"""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

    def generate_presigned_url_for_upload(self, s3_key: str, expiration=3600):
        """Generate a pre-signed URL for uploading a file to S3"""
        try:
            # Generate the URL to allow uploading to S3
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating pre-signed URL for upload: {e}")
            return None

    def generate_presigned_url_for_download(self, s3_key: str, expiration=3600):
        """Generate a pre-signed URL for downloading a file from S3"""
        try:
            # Generate the URL to allow downloading from S3
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key , 'ResponseContentDisposition': 'attachment'},
                ExpiresIn=expiration
            )
            
            return url
        except Exception as e:
            print(f"Error generating pre-signed URL for download: {e}")
            return None

    def stream_file_from_s3(self, s3_key: str, bucket_name: str):
        """Stream entire file from S3 ensuring bytes are yielded."""
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key)

            def content_generator():
                with response['Body'] as stream:
                    while True:
                        chunk = stream.read(8192)
                        if not chunk:
                            break
                        if isinstance(chunk, str):
                            chunk = chunk.encode('utf-8')
                        yield chunk
            return content_generator()
        except self.s3_client.exceptions.NoSuchKey:
            print(f"File not found: {s3_key}")
            raise FileNotFoundError(f"File not found: {s3_key}")
        except Exception as e:
            print(f"Error streaming entire file: {e}")
            raise e


    
    def upload_track_package(self, artist: str, track_title: str, assets: dict):
        """
        Uploads all components (audio, image, metadata, zip) of a track
        :param artist: Artist name
        :param track_title: Track title
        :param assets: Dictionary with file_type as key and (local_path, filename) as value
        """
        urls = {}
        for file_type, (file_path, filename) in assets.items():
            s3_key = self.generate_s3_key(artist, track_title, file_type, filename)
            url = self.upload_file(file_path, s3_key)
            urls[file_type] = url
        return urls
    

    # Method to move the s3 object from one location to another and delete the old one
    def move_s3_object(self, old_key, new_key):
        """Move an S3 object by copying to new location and deleting the old one"""
        # Copy the object
        self.s3_client.copy_object(
            Bucket=self.bucket_name,
            CopySource={'Bucket': self.bucket_name, 'Key': old_key},
            Key=new_key
        )
        # Delete the original
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=old_key)
        
        # Return the new URL
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{new_key}"
    

    def get_file_name_from_url(self, url: str) -> str:
        """Extract the file name from a given S3 URL"""
        parsed_url = urlparse(url)
        return os.path.basename(parsed_url.path)
        
    async def upload_file_from_uploadfile(self, upload_file, s3_key: str):
        try:
            self.s3_client.upload_fileobj(upload_file.file, self.bucket_name, s3_key)
            file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            return file_url
        except NoCredentialsError:
            print("Credentials not available.")
            return None
        except Exception as e:
            print(f"Error uploading file from uploadfile: {e}")
            return None

    async def handle_music_file_upload(self, file: UploadFile, artist: str, track_name: str, file_type: str, unique: bool = False):
        """Handle file upload to S3 and return the URL"""
        if not file:
            return None

        try:
            original_filename = file.filename
            name, ext = os.path.splitext(original_filename)
            if unique:
                import uuid
                suffix = uuid.uuid4().hex[:8]
                filename = f"{name}-{suffix}{ext}"
            else:
                filename = original_filename

            # Generate S3 key
            s3_key = self.generate_s3_key(
                artist=artist,
                track_title=track_name,
                file_type=file_type,
                filename=filename
            )
            content_type = file.content_type or ''
            if not content_type or content_type == 'application/octet-stream':
                ext_lower = ext.lower()
                if ext_lower in ['.mp3']:
                    content_type = 'audio/mpeg'
                elif ext_lower in ['.wav']:
                    content_type = 'audio/wav'
                elif ext_lower in ['.jpg', '.jpeg']:
                    content_type = 'image/jpeg'
                elif ext_lower in ['.png']:
                    content_type = 'image/png'
                elif ext_lower in ['.webp']:
                    content_type = 'image/webp'

            return await self.upload_file_from_uploadfile(
                upload_file=file,
                s3_key=s3_key,
                extra_args={"ContentType": content_type} if content_type else None
            )
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None


    def get_file_size(self, s3_key: str, bucket_name: str) -> int:
        """Get file size from S3"""
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            print(f"File size: {response['ContentLength']} bytes")
            return response['ContentLength']
        except Exception as e:
            print(f"Error getting file size: {e}")
            raise

    def stream_file_range_from_s3(self, s3_key: str, bucket_name: str, start: int, end: int,file_size: int):
        """Stream a specific range of bytes from S3"""
        try:
            range_header = f"bytes={start}-{end}"
            response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key, Range=range_header)
            content_length = response['ContentLength']

            def content_generator():
                with response['Body'] as stream:
                    while True:
                        chunk = stream.read(8192)
                        if not chunk:
                            break
                        if isinstance(chunk, str):
                            chunk = chunk.encode('utf-8')
                        yield chunk

            return StreamingResponse(
                content_generator(),
                status_code=206,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Content-Length': str(end - start + 1),
                    'Accept-Ranges': 'bytes',
                    'Content-Type': 'audio/mpeg'
                },
                media_type="audio/mpeg"
            )
        except Exception as e:
            print(f"Error streaming file from S3: {e}")
            raise

    async def upload_playlist_cover(
        self, 
        file: UploadFile, 
        user_id: int,
        playlist_id: int
    ) -> str:
        """Upload playlist cover image to S3 with validation"""
        ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]
        MAX_SIZE = 5 * 1024 * 1024  # 5MB

        # Validate content type
        if file.content_type not in ALLOWED_TYPES:
            raise ValueError(
                f"Invalid file type. Allowed: {', '.join(ALLOWED_TYPES)}"
            )

        # Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_SIZE:
            raise ValueError(f"File too large. Max size: {MAX_SIZE//1024//1024}MB")

        # Generate S3 key
        ext = file.filename.split('.')[-1].lower()
        s3_key = f"users/{user_id}/playlists/{playlist_id}/cover.{ext}"

        # Upload to S3
        try:
            await self.upload_file_from_uploadfile(file, s3_key)
            return self.get_file_url(s3_key)
        except Exception as e:
            raise RuntimeError(f"S3 upload failed: {str(e)}")
        
    
    def get_key_from_url(self, url: str) -> str:
        """Extract S3 key from URL"""
        parsed = urlparse(url)
        # Remove leading slash from path
        return parsed.path.lstrip('/')
    
    async def upload_file_from_uploadfile(
        self, 
        upload_file: UploadFile, 
        s3_key: str,
        extra_args: Optional[dict] = None
    ):
        try:
            # Ensure we're at the start of the file
            await upload_file.seek(0)
            
            # Set default extra args
            if extra_args is None:
                extra_args = {}
                
            # Upload with additional parameters
            self.s3_client.upload_fileobj(
                upload_file.file, 
                self.bucket_name, 
                s3_key,
                ExtraArgs=extra_args
            )
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    
    # Zip file 
    def generate_presigned_zip_download(self, s3_key: str, download_filename: str, expiration: int = 86400) -> str:
        """
        Generate a presigned URL for a ZIP with a forced download filename.
        """
        # RFC5987 filename* for broader charset support (fallback filename also set)
        disposition = f'attachment; filename="{download_filename}"; filename*=UTF-8\'\'{urllib.parse.quote(download_filename)}'
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentDisposition': disposition,
                    'ResponseContentType': 'application/zip',
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned ZIP download URL: {e}")
            return None

    def build_license_zip_key(self, license_id: int, music_name: str, license_type_value: str) -> str:
        """
        Create a safe, predictable S3 key for license ZIPs.
        """
        safe_title = music_name.strip().lower().replace(" ", "-")
        safe_type = license_type_value.strip().lower()
        filename = f"{safe_title}.zip"
        return f"licenses/{license_id}/{safe_title}/{safe_type}/{filename}"

    # get bucket name from url
    @staticmethod
    def get_s3_bucket_from_url(url: str) -> str:
        """Extract the S3 bucket name from a given URL"""
        parsed_url = urlparse(url)
        return parsed_url.netloc.split('.')[0]

    def generate_license_pdf_key(self, user_id: int, license_id: str, music_name: str, license_type: str) -> str:
        """Generate S3 key for license PDF"""
        safe_music_name = music_name.replace(' ', '-').lower()
        safe_license_type = license_type.replace(' ', '-').lower()
        filename = f"{safe_music_name}-{safe_license_type}-{license_id}.pdf"
        return f"licenses/{user_id}/{license_id}/{filename}"

    def upload_license_pdf(self, pdf_bytes: bytes, s3_key: str, filename: str) -> str:
        """Upload license PDF to S3"""
        try:
            import io
            pdf_file = io.BytesIO(pdf_bytes)
            
            self.s3_client.upload_fileobj(
                pdf_file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ContentDisposition': f'attachment; filename="{filename}"'
                }
            )
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        except Exception as e:
            print(f"Error uploading license PDF: {e}")
            raise
    def ensure_video_lifecycle_policy(self, prefix: str = "videos/", days: int = 1):
        """
        Ensures a lifecycle policy exists to delete objects in the specified prefix after 'days'.
        """
        rule_id = "DeleteVideoAfterOneDay"
        try:
            # Try to get existing configuration
            try:
                lifecycle = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.bucket_name)
                rules = lifecycle.get('Rules', [])
            except self.s3_client.exceptions.ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'NoSuchLifecycleConfiguration':
                    rules = []
                else:
                    raise e

            # Check if rule already exists
            for rule in rules:
                if rule.get('ID') == rule_id:
                    print(f"Lifecycle rule '{rule_id}' already exists.")
                    return

            # Add new rule
            new_rule = {
                'ID': rule_id,
                'Status': 'Enabled',
                'Filter': {'Prefix': prefix},
                'Expiration': {'Days': days}
            }
            rules.append(new_rule)

            # Update configuration
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration={'Rules': rules}
            )
            print(f"Successfully added lifecycle rule '{rule_id}' for prefix '{prefix}'")

        except Exception as e:
            print(f"Error setting lifecycle policy: {e}")
