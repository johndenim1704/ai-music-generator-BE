"""
Celery Tasks for AI Generation
Handles title generation, album cover generation, etc.
"""
import os
import tempfile
import logging
from celery_app import celery_app
from utils.track_title_service import TrackTitleService
from utils.s3_manager import S3Manager

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.ai_tasks.generate_track_title_async",
    max_retries=2,
    default_retry_delay=30
)
def generate_track_title_async(audio_url: str, genre: str, num_titles: int = 1):
    """
    Asynchronously generate track titles using AI
    
    Args:
        audio_url: S3 URL of the audio file
        genre: Music genre
        num_titles: Number of titles to generate
        
    Returns:
        dict with generated titles
    """
    s3_manager = S3Manager()
    title_service = TrackTitleService()
    
    temp_path = None
    
    try:
        # Download from S3
        logger.info(f"[CELERY] Downloading audio for title generation: {audio_url}")
        s3_key = s3_manager.get_key_from_url(audio_url)
        
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        s3_manager.download_file(s3_key, temp_path)
        
        # Generate titles
        logger.info(f"[CELERY] Generating titles: genre={genre}")
        titles = title_service.generate_titles(temp_path, genre=genre, num_titles=num_titles)
        
        logger.info(f"[CELERY] Title generation complete")
        
        return {
            "status": "success",
            "titles": titles
        }
        
    except Exception as e:
        logger.error(f"[CELERY] Title generation failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"[CELERY] Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.error(f"[CELERY] Failed to cleanup temp file: {e}")


@celery_app.task(
    name="tasks.ai_tasks.generate_album_cover_async",
    max_retries=2,
    default_retry_delay=30
)
def generate_album_cover_async(
    track_name: str,
    genre: str,
    mood: str,
    style: str,
    user_id: int
):
    """
    Asynchronously generate album cover using Stable Diffusion
    
    Args:
        track_name: Name of the track
        genre: Music genre
        mood: Mood/vibe
        style: Art style
        user_id: User ID for S3 path
        
    Returns:
        dict with S3 URL of generated cover
    """
    try:
        from utils.album_cover_service import AlbumCoverService
        
        logger.info(f"[CELERY] Generating album cover: {track_name}")
        
        cover_service = AlbumCoverService()
        s3_manager = S3Manager()
        
        # Generate cover
        temp_path = cover_service.generate_cover(
            track_name=track_name,
            genre=genre,
            mood=mood,
            style=style
        )
        
        # Upload to S3
        import uuid
        cover_filename = f"cover_{uuid.uuid4().hex[:8]}.png"
        s3_key = f"album-covers/{user_id}/{cover_filename}"
        cover_url = s3_manager.upload_file(temp_path, s3_key)
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        logger.info(f"[CELERY] Album cover generated: {cover_url}")
        
        return {
            "status": "success",
            "cover_url": cover_url
        }
        
    except Exception as e:
        logger.error(f"[CELERY] Album cover generation failed: {str(e)}", exc_info=True)
        raise
