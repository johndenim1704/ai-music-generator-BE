# import os
# import tempfile
# import uuid
# import logging
# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.orm import Session

# from utils.thumbnail_service import ThumbnailService
# from utils.s3_manager import S3Manager
# from utils.deps import get_db, get_current_user
# from models.user import Users
# from schemas.thumbnail import ThumbnailRequest, ThumbnailResponse

# router = APIRouter(tags=["thumbnail"], prefix="/thumbnail")
# logger = logging.getLogger(__name__)

# thumbnail_service = ThumbnailService()
# s3_manager = S3Manager()

# @router.post("/generate", response_model=ThumbnailResponse, status_code=status.HTTP_200_OK)
# async def generate_thumbnail(
#     request: ThumbnailRequest,
#     # current_user: Users = Depends(get_current_user) # Uncomment when auth is ready
# ):
#     """
#     Generate an AI thumbnail for a music track.
    
#     Uses OpenAI's DALL-E 3 (gpt-image-1) to generate photorealistic album artwork
#     based on the track's name, genre, and mood.
#     """
#     print("=" * 80)
#     print(f"🎨 THUMBNAIL GENERATION REQUEST")
#     print(f"🎵 Track: {request.track_name}")
#     print(f"🎸 Genre: {request.genre}")
#     print(f"💭 Mood: {request.mood}")
#     print(f"📐 Size: {request.size}")
#     print("=" * 80)

#     temp_path = None
    
#     try:
#         # Create temp file
#         fd, temp_path = tempfile.mkstemp(suffix=".png")
#         os.close(fd)
        
#         # Generate thumbnail
#         print("🤖 Calling OpenAI to generate image...")
#         result = thumbnail_service.generate_thumbnail(
#             track_name=request.track_name,
#             genre=request.genre,
#             mood=request.mood,
#             # size_preset=request.size,
#             output_path=temp_path
#         )
        
#         print("✅ Image generated successfully")
        
#         # Upload to S3
#         print("☁️ Uploading to S3...")
#         s3_filename = f"thumbnail_{uuid.uuid4().hex[:8]}.png"
#         # s3_key = f"thumbnails/{current_user.id}/{s3_filename}"
#         s3_key = f"thumbnails/{s3_filename}"
        
#         uploaded_url = s3_manager.upload_file(temp_path, s3_key)
#         if not uploaded_url:
#              raise Exception("Failed to upload thumbnail to S3")
             
#         print(f"✅ Uploaded to S3: {s3_key}")
        
#         # Generate presigned URL
#         presigned_url = s3_manager.generate_presigned_url_for_download(s3_key, expiration=3600)
#         print(f"🔗 Presigned URL generated")
        
#         return ThumbnailResponse(
#             image_url=presigned_url,
#             track_name=request.track_name,
#             genre=request.genre,
#             mood=request.mood,
#             # size=request.size,
#             width=result["width"],
#             height=result["height"],
#             prompt=result.get("prompt")
#         )

#     except Exception as e:
#         logger.error(f"Thumbnail generation failed: {e}")
#         print(f"❌ Error: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to generate thumbnail: {str(e)}"
#         )
#     finally:
#         # Cleanup
#         if temp_path and os.path.exists(temp_path):
#             try:
#                 os.remove(temp_path)
#                 print(f"🧹 Cleaned up temp file: {temp_path}")
#             except Exception as e:
#                 print(f"⚠️ Failed to cleanup temp file: {e}")
import os
import tempfile
import uuid
import logging
from fastapi import APIRouter, HTTPException, status, Request
from utils.limiter import limiter
from schemas.thumbnail import ThumbnailRequest, ThumbnailResponse
from utils.thumbnail_service import ThumbnailService
from utils.s3_manager import S3Manager

router = APIRouter(tags=["thumbnail"], prefix="/thumbnail")
logger = logging.getLogger(__name__)

thumbnail_service = ThumbnailService()
s3_manager = S3Manager()

@router.post("/generate", response_model=ThumbnailResponse, status_code=status.HTTP_200_OK)
# @limiter.limit("5/minute")
async def generate_thumbnail(req: Request, request: ThumbnailRequest):
    print("=" * 80)
    print("🎨 THUMBNAIL GENERATION REQUEST")
    print(f"🎵 Track: {request.track_name}")
    print(f"🎸 Genre: {request.genre}")
    print(f"💭 Mood: {request.mood}")
    print("=" * 80)

    temp_path = None

    try:
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        print("🤖 Generating AI artwork...")
        result = thumbnail_service.generate_thumbnail(
            track_name=request.track_name,
            genre=request.genre,
            mood=request.mood,
            output_path=temp_path
        )
        print("✅ Generated successfully")

        print("☁️ Uploading to S3...")
        s3_filename = f"thumbnail_{uuid.uuid4().hex[:8]}.png"
        s3_key = f"thumbnails/{s3_filename}"
        uploaded_url = s3_manager.upload_file(temp_path, s3_key)
        if not uploaded_url:
            raise Exception("S3 upload failed")
        print("📤 S3 upload complete")

        presigned_url = s3_manager.generate_presigned_url_for_download(s3_key, expiration=3600)
        print("🔗 Presigned URL ready")

        return ThumbnailResponse(
            image_url=presigned_url,
            track_name=request.track_name,
            genre=request.genre,
            mood=request.mood,
            font_style=request.font_style,  # Pass to frontend for client-side overlay
            width=result["width"],
            height=result["height"],
            prompt=result.get("prompt")
        )

    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        raise HTTPException(status_code=500, detail=f"Thumbnail generation failed: {str(e)}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"🧹 Temp file cleaned: {temp_path}")
            except:
                print("⚠ Failed to delete temp file")
