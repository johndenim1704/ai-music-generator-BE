"""
Celery Application Configuration
Handles async tasks for audio mastering, AI generation, and heavy processing
"""
from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Create Celery app
celery_app = Celery(
    "aimusic",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.mastering_tasks",
        "tasks.ai_tasks",
        "tasks.cleanup_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 min soft limit
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time (for heavy tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-old-temp-files": {
            "task": "tasks.cleanup_tasks.cleanup_temp_files",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        },
        "cleanup-old-processing-logs": {
            "task": "tasks.cleanup_tasks.cleanup_processing_logs",
            "schedule": crontab(minute=0, hour=3),  # Daily at 3 AM
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
