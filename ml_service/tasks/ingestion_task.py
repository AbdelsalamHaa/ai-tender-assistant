"""
Celery task for PDF ingestion pipeline.
"""

import logging
from uuid import UUID

from celery import Task

from ml_service.tasks.celery_app import celery_app
from ml_service.db.session import SessionLocal
from ml_service.db.models import JobStatus
from ml_service.db.repositories.job_repository import JobRepository
from ml_service.db.repositories.document_repository import DocumentRepository
from ml_service.core.ingestion.pipeline import PDFIngestionPipeline

logger = logging.getLogger(__name__)


class IngestionTask(Task):
    """Base task class with error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=IngestionTask,
    name="ml_service.tasks.ingestion_task.process_pdf_ingestion",
)
def process_pdf_ingestion(self, job_id: str) -> dict:
    """
    Process a PDF ingestion job.
    
    This task:
    1. Parses the PDF document
    2. Extracts structured data using LLM
    3. Chunks the document
    4. Generates embeddings
    5. Stores everything in PostgreSQL
    
    Args:
        job_id: UUID of the ingestion job
        
    Returns:
        dict: Result summary with status and metadata
    """
    job_uuid = UUID(job_id)
    session = SessionLocal()
    
    try:
        # Get job from database
        job = JobRepository.get_by_id_sync(session, job_uuid)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        logger.info(f"Starting PDF ingestion for job {job_id}: {job.filename}")
        
        # Update status to PROCESSING
        JobRepository.update_status_sync(
            session,
            job_uuid,
            status=JobStatus.PROCESSING,
            current_step="initializing",
        )
        
        # Initialize the ingestion pipeline
        pipeline = PDFIngestionPipeline(session, job_uuid)
        
        # Step 1: Parse PDF
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.PROCESSING,
            current_step="parsing",
        )
        parsed_content, page_count, doc_metadata, pages_with_content = pipeline.parse_pdf(job.file_path)
        
        # Store raw document content
        DocumentRepository.create_document_sync(
            session,
            job_id=job_uuid,
            content=parsed_content,
            page_count=page_count,
            metadata=doc_metadata,
        )
        
        logger.info(f"Job {job_id}: Parsed {page_count} pages")
        
        # Step 2: Extract structured data (with page tracking for requirements)
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.PROCESSING,
            current_step="extracting",
        )
        extracted_data = pipeline.extract_structured_data(parsed_content, pages_with_content)
        
        # Store extracted data with tender-specific fields
        requirements = extracted_data.get("requirements", [])
        DocumentRepository.create_extracted_data_sync(
            session,
            job_id=job_uuid,
            title=extracted_data.get("title"),
            author=extracted_data.get("author"),
            summary=extracted_data.get("summary"),
            document_type=extracted_data.get("document_type"),
            key_topics=extracted_data.get("key_topics"),
            entities=extracted_data.get("entities"),
            language=extracted_data.get("language", "en"),
            # Tender-specific fields
            tender_reference=extracted_data.get("tender_reference"),
            submission_deadline=extracted_data.get("submission_deadline"),
            estimated_value=extracted_data.get("estimated_value"),
            requirements=requirements,
        )
        
        logger.info(
            f"Job {job_id}: Extracted structured data - {extracted_data.get('title')}, "
            f"{len(requirements)} requirements"
        )
        
        # Step 3: Chunk document
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.PROCESSING,
            current_step="chunking",
        )
        nodes = pipeline.chunk_document(parsed_content, job_uuid, doc_metadata)
        
        logger.info(f"Job {job_id}: Created {len(nodes)} chunks")
        
        # Step 4: Generate embeddings and store in vector DB
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.PROCESSING,
            current_step="embedding",
        )
        chunk_count = pipeline.embed_and_store(nodes)
        
        logger.info(f"Job {job_id}: Stored {chunk_count} chunks with embeddings")
        
        # Update job as completed
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.COMPLETED,
            current_step="completed",
            total_pages=page_count,
            total_chunks=chunk_count,
        )
        
        logger.info(f"Job {job_id}: Ingestion completed successfully")
        
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "filename": job.filename,
            "total_pages": page_count,
            "total_chunks": chunk_count,
            "title": extracted_data.get("title"),
        }
        
    except Exception as e:
        logger.error(f"Job {job_id}: Ingestion failed - {str(e)}", exc_info=True)
        
        # Update job as failed
        JobRepository.update_status_sync(
            session, job_uuid,
            status=JobStatus.FAILED,
            current_step="failed",
            error_message=str(e),
        )
        
        # Re-raise for Celery retry logic
        raise
        
    finally:
        session.close()

