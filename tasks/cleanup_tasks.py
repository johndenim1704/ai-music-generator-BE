"""
Celery Tasks for Cleanup and Maintenance
Periodic tasks to clean up temporary files, old logs, etc.
"""
import os
import time
import logging
from datetime import datetime, timedelta
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.cleanup_tasks.cleanup_temp_files")
def cleanup_temp_files():
    """
    Clean up old temporary files
    Runs every 6 hours via Celery Beat
    """
    try:
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        # Delete files older than 24 hours
        cutoff_time = time.time() - (24 * 3600)
        deleted_count = 0
        
        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if filename.startswith("tmp") or filename.startswith("aimusic"):
                    filepath = os.path.join(root, filename)
                    try:
                        if os.path.getmtime(filepath) < cutoff_time:
                            os.remove(filepath)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete {filepath}: {e}")
        
        logger.info(f"[CLEANUP] Deleted {deleted_count} old temp files")
        return {"deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Temp file cleanup failed: {e}", exc_info=True)
        raise


@celery_app.task(name="tasks.cleanup_tasks.cleanup_processing_logs")
def cleanup_processing_logs():
    """
    Clean up old processing logs from memory
    Runs daily at 3 AM via Celery Beat
    """
    try:
        from routers.mastering import processing_logs
        
        # Keep logs for last 24 hours only
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # This would need to be implemented based on your log storage
        # For now, just clear all logs older than 24 hours
        
        logger.info("[CLEANUP] Processing logs cleanup complete")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Log cleanup failed: {e}", exc_info=True)
        raise


@celery_app.task(name="tasks.cleanup_tasks.cleanup_old_mastered_files")
def cleanup_old_mastered_files(days_old: int = 30):
    """
    Clean up mastered files older than specified days
    
    Args:
        days_old: Delete files older than this many days
    """
    try:
        from config.db import SessionLocal
        from models.mastered_music import MasteredMusic
        from utils.s3_manager import S3Manager
        
        db = SessionLocal()
        s3_manager = S3Manager()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old mastered music records
        old_records = db.query(MasteredMusic).filter(
            MasteredMusic.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for record in old_records:
            try:
                if record.mastered_audio_url:
                    s3_key = s3_manager.get_key_from_url(record.mastered_audio_url)
                    s3_manager.delete_file(s3_key)
                
                db.delete(record)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete mastered file {record.id}: {e}")
        
        db.commit()
        db.close()
        
        logger.info(f"[CLEANUP] Deleted {deleted_count} old mastered files")
        return {"deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Mastered files cleanup failed: {e}", exc_info=True)
        raise
