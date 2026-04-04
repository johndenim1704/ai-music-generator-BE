"""
Celery Tasks for Audio Mastering
Offloads heavy audio processing to background workers
"""
import os
import tempfile
import logging
from celery import Task
from celery_app import celery_app
from utils.mastering_service import MasteringService
from utils.s3_manager import S3Manager
from config.db import SessionLocal
from models.mastered_music import MasteredMusic

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="tasks.mastering_tasks.master_audio_async",
    max_retries=3,
    default_retry_delay=60
)
def master_audio_async(
    self,
    audio_url: str,
    genre: str,
    quality_mode: str,
    user_id: int,
    mastered_music_id: int,
    original_track_id: int = None
):
    """
    Asynchronously master an audio file
    
    Args:
        audio_url: S3 URL of the audio file to master
        genre: Genre preset to use
        quality_mode: "high" or "standard"
        user_id: User ID
        mastered_music_id: Database record ID
        original_track_id: Optional original track ID for remastering
    """
    s3_manager = S3Manager()
    mastering_service = MasteringService()
    
    temp_dir = None
    input_path = None
    output_path = None
    
    try:
        # Update status to processing
        mastered_record = self.db.query(MasteredMusic).filter(
            MasteredMusic.id == mastered_music_id
        ).first()
        
        if not mastered_record:
            raise ValueError(f"MasteredMusic record {mastered_music_id} not found")
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "input.wav")
        output_path = os.path.join(temp_dir, "mastered.wav")
        
        # Download from S3
        logger.info(f"[CELERY] Downloading audio from S3: {audio_url}")
        s3_key = s3_manager.get_key_from_url(audio_url)
        s3_manager.download_file(s3_key, input_path)
        
        # Progress callback
        def log_progress(msg: str):
            logger.info(f"[CELERY] {msg}")
            # Could update database with progress here
        
        # Master the audio
        logger.info(f"[CELERY] Starting mastering: genre={genre}, quality={quality_mode}")
        metadata = mastering_service.master_audio(
            input_path=input_path,
            output_path=output_path,
            genre=genre,
            quality_mode=quality_mode,
            log_callback=log_progress
        )
        
        # Upload mastered file to S3
        logger.info(f"[CELERY] Uploading mastered audio to S3")
        mastered_filename = f"mastered_{mastered_music_id}.wav"
        s3_key = f"mastered/{user_id}/{mastered_filename}"
        mastered_url = s3_manager.upload_file(output_path, s3_key)
        
        # Update database
        mastered_record.mastered_audio_url = mastered_url
        mastered_record.processing_metadata = metadata
        self.db.commit()
        
        logger.info(f"[CELERY] Mastering complete: {mastered_url}")
        
        return {
            "status": "success",
            "mastered_url": mastered_url,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"[CELERY] Mastering failed: {str(e)}", exc_info=True)
        
        # Update database with error
        try:
            mastered_record = self.db.query(MasteredMusic).filter(
                MasteredMusic.id == mastered_music_id
            ).first()
            if mastered_record:
                mastered_record.error_message = str(e)
                self.db.commit()
        except Exception as db_error:
            logger.error(f"[CELERY] Failed to update error in DB: {db_error}")
        
        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        raise
        
    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"[CELERY] Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.error(f"[CELERY] Failed to cleanup temp dir: {e}")


@celery_app.task(name="tasks.mastering_tasks.get_mastering_status")
def get_mastering_status(task_id: str):
    """
    Get the status of a mastering task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        dict with status, result, etc.
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None
    }
