"""
PDF ingestion endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ml_service.db.session import get_db
from ml_service.db.repositories.job_repository import JobRepository
from ml_service.schemas.job import JobCreate
from ml_service.core.storage import (
    save_uploaded_file,
    validate_file_extension,
    validate_file_size,
)
from ml_service.tasks.ingestion_task import process_pdf_ingestion

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=JobCreate,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload PDF for ingestion",
    description="Upload a PDF file to start the ingestion pipeline. Returns immediately with a job ID for status tracking.",
)
async def ingest_pdf(
    file: Annotated[UploadFile, File(description="PDF file to ingest")],
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF file and start the ingestion pipeline.
    
    The ingestion process runs asynchronously in the background.
    Use the returned job_id to poll for status updates.
    
    **Processing steps:**
    1. Parse PDF content
    2. Extract structured data (title, author, summary, etc.)
    3. Chunk document into smaller pieces
    4. Generate embeddings
    5. Store in vector database
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed.",
        )
    
    # Validate file size
    if not validate_file_size(file.file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50MB.",
        )
    
    try:
        # Save file to disk
        file_path = save_uploaded_file(file.file, file.filename)
        logger.info(f"Saved uploaded file: {file_path}")
        
        # Create job record
        job = await JobRepository.create_async(
            session=db,
            filename=file.filename,
            file_path=file_path,
        )
        logger.info(f"Created ingestion job: {job.id}")
        
        # Queue Celery task
        process_pdf_ingestion.delay(str(job.id))
        logger.info(f"Queued ingestion task for job: {job.id}")
        
        return JobCreate(
            job_id=job.id,
            status=job.status,
            message="Ingestion job created successfully. Processing will begin shortly.",
            created_at=job.created_at,
        )
        
    except Exception as e:
        logger.error(f"Failed to create ingestion job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start ingestion: {str(e)}",
        )

