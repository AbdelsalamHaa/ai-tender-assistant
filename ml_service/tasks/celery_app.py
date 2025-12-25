"""
Celery application configuration.
"""

from celery import Celery

from ml_service.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ml_service",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["ml_service.tasks.ingestion_task"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Task routing (optional, for future scaling)
    task_routes={
        "ml_service.tasks.ingestion_task.*": {"queue": "ingestion"},
    },
    
    # Default queue
    task_default_queue="ingestion",
)


# Optional: Configure task retry behavior
celery_app.conf.task_annotations = {
    "ml_service.tasks.ingestion_task.process_pdf_ingestion": {
        "rate_limit": "10/m",  # Max 10 tasks per minute
        "max_retries": 3,
        "default_retry_delay": 60,  # 60 seconds between retries
    }
}

