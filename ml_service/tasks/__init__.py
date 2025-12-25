"""
Celery tasks module.
"""

from ml_service.tasks.celery_app import celery_app
from ml_service.tasks.ingestion_task import process_pdf_ingestion

__all__ = ["celery_app", "process_pdf_ingestion"]

