import os
import tempfile
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status,Form, Request
from utils.limiter import limiter
from utils.video_service import VideoService
from utils.s3_manager import S3Manager
import requests

from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

router = APIRouter(tags=["video"], prefix="/video")
video_service = VideoService()
s3_manager = S3Manager()

try:
    s3_manager.ensure_video_lifecycle_policy()
except Exception as e:
    logger.warning(f"Could not set S3 lifecycle policy: {e}")



@router.post("/generate", status_code=status.HTTP_200_OK)
# @limiter.limit("2/minute")
async def generate_video(
    # request: Request,

    image: UploadFile | None = File(
        None, description="Image file (JPG, PNG, etc.)"
    ),
    
    image_url: str | None = Form(
        None, description="URL of the image (JPG, PNG, etc.)"
    ),
    
    audio: UploadFile = File(..., description="Audio file (WAV, MP3)")
):
    """
    Generate an MP4 video from an image (file OR URL) and an audio file.

    - image: uploaded image file (optional)
    - image_url: URL of an image (optional)
    - audio: uploaded audio file (required)

    At least one of image or image_url must be provided.
    """

    if image is None and not image_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either an image file or image_url"
        )

    if image is not None and image_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either image file OR image_url, not both"
        )

    if (
        not audio.content_type.startswith("audio/")
        and not audio.filename.lower().endswith((".mp3", ".wav"))
    ):
        raise HTTPException(status_code=400, detail="Invalid audio file type")

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()

        audio_ext = os.path.splitext(audio.filename)[1] or ".wav"
        temp_audio_path = os.path.join(
            temp_dir, f"input_audio_{uuid.uuid4()}{audio_ext}"
        )
        with open(temp_audio_path, "wb") as f:
            f.write(await audio.read())

        if image is not None:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Invalid image file type")

            image_ext = os.path.splitext(image.filename)[1] or ".jpg"
            temp_image_path = os.path.join(
                temp_dir, f"input_image_{uuid.uuid4()}{image_ext}"
            )
            with open(temp_image_path, "wb") as f:
                f.write(await image.read())

        else:
            try:
                resp = await run_in_threadpool(requests.get, image_url, stream=True, timeout=10)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch image_url: {e}"
                )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch image_url, status={resp.status_code}",
                )

            content_type = resp.headers.get("Content-Type", "")
            
            url_ext = os.path.splitext(image_url.split("?")[0])[1].lower()
            
            is_image_type = content_type.startswith("image/")
            is_binary_type = content_type in ["application/octet-stream", "binary/octet-stream"]
            has_image_ext = url_ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
            
            if not is_image_type:
                if not (is_binary_type and has_image_ext):
                    
                    if not has_image_ext:
                         raise HTTPException(
                            status_code=400,
                            detail=f"URL does not point to an image (Content-Type={content_type})",
                        )

            if not url_ext:
                if "png" in content_type:
                    url_ext = ".png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    url_ext = ".jpg"
                else:
                    url_ext = ".jpg"

            temp_image_path = os.path.join(
                temp_dir, f"input_image_{uuid.uuid4()}{url_ext}"
            )
            with open(temp_image_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        temp_output_path = os.path.join(
            temp_dir, f"output_video_{uuid.uuid4()}.mp4"
        )

        await run_in_threadpool(
            video_service.generate_video,
            temp_image_path,
            temp_audio_path,
            temp_output_path,
        )

        s3_filename = f"generated_video_{uuid.uuid4()}.mp4"
        s3_key = f"videos/{s3_filename}"

        file_url = await run_in_threadpool(s3_manager.upload_file, temp_output_path, s3_key)
        if not file_url:
            raise HTTPException(
                status_code=500, detail="Failed to upload video to storage"
            )

        presigned_url = s3_manager.generate_presigned_url_for_download(
            s3_key, expiration=3600
        )

        return {
            "message": "Video generated successfully",
            "video_url": presigned_url,
            "s3_key": s3_key,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in video generation endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temp dir: {cleanup_error}")
