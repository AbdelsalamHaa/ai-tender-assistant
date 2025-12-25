"""
Job status and data retrieval endpoints.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ml_service.db.session import get_db
from ml_service.db.repositories.job_repository import JobRepository
from ml_service.db.repositories.document_repository import DocumentRepository
from ml_service.schemas.job import JobResponse, JobProgress, JobStatusResponse
from ml_service.schemas.document import DocumentResponse
from ml_service.schemas.extraction import ExtractedDataResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Get full details of an ingestion job including progress information.",
)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about an ingestion job.
    
    **Status values:**
    - `PENDING`: Job is queued and waiting for processing
    - `PROCESSING`: Job is currently being processed
    - `COMPLETED`: Job finished successfully
    - `FAILED`: Job failed (see error_message for details)
    """
    job = await JobRepository.get_by_id_async(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    # Build progress info
    steps_completed = []
    if job.current_step:
        step_order = ["parsing", "extracting", "chunking", "embedding", "completed"]
        current_idx = step_order.index(job.current_step) if job.current_step in step_order else -1
        steps_completed = step_order[:current_idx + 1] if current_idx >= 0 else []
    
    progress = JobProgress(
        current_step=job.current_step,
        steps_completed=steps_completed,
        total_chunks=job.total_chunks,
        total_pages=job.total_pages,
    )
    
    return JobResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress=progress,
        error_message=job.error_message,
    )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get simplified status for polling. Use this for frequent status checks.",
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get simplified job status for polling.
    
    This endpoint is optimized for frequent status checks during processing.
    """
    job = await JobRepository.get_by_id_async(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        current_step=job.current_step,
        error_message=job.error_message,
    )


@router.get(
    "/{job_id}/document",
    response_model=DocumentResponse,
    summary="Get parsed document",
    description="Get the raw parsed content of the document.",
)
async def get_job_document(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the raw parsed document content.
    
    Only available after job reaches COMPLETED status.
    """
    # Verify job exists and is completed
    job = await JobRepository.get_by_id_async(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status}",
        )
    
    # Get document
    document = await DocumentRepository.get_document_by_job_id_async(db, job_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found for job {job_id}",
        )
    
    return DocumentResponse(
        id=document.id,
        job_id=document.job_id,
        content=document.content,
        page_count=document.page_count,
        metadata=document.metadata_,
        created_at=document.created_at,
    )


@router.get(
    "/{job_id}/extracted",
    response_model=ExtractedDataResponse,
    summary="Get extracted data",
    description="Get structured data extracted from the document.",
)
async def get_job_extracted_data(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get structured data extracted from the document.
    
    Includes title, author, summary, key topics, and named entities.
    Only available after job reaches COMPLETED status.
    """
    # Verify job exists and is completed
    job = await JobRepository.get_by_id_async(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status}",
        )
    
    # Get extracted data
    extracted = await DocumentRepository.get_extracted_data_by_job_id_async(db, job_id)
    
    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extracted data not found for job {job_id}",
        )
    
    return ExtractedDataResponse(
        id=extracted.id,
        job_id=extracted.job_id,
        title=extracted.title,
        author=extracted.author,
        summary=extracted.summary,
        document_type=extracted.document_type,
        key_topics=extracted.key_topics,
        entities=extracted.entities,
        language=extracted.language,
        created_at=extracted.created_at,
    )


@router.get(
    "",
    response_model=List[JobResponse],
    summary="List jobs",
    description="List recent ingestion jobs with pagination.",
)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Number of jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    db: AsyncSession = Depends(get_db),
):
    """
    List recent ingestion jobs.
    
    Results are ordered by creation date (newest first).
    """
    jobs = await JobRepository.list_jobs_async(db, limit=limit, offset=offset)
    
    result = []
    for job in jobs:
        steps_completed = []
        if job.current_step:
            step_order = ["parsing", "extracting", "chunking", "embedding", "completed"]
            current_idx = step_order.index(job.current_step) if job.current_step in step_order else -1
            steps_completed = step_order[:current_idx + 1] if current_idx >= 0 else []
        
        progress = JobProgress(
            current_step=job.current_step,
            steps_completed=steps_completed,
            total_chunks=job.total_chunks,
            total_pages=job.total_pages,
        )
        
        result.append(JobResponse(
            job_id=job.id,
            status=job.status,
            filename=job.filename,
            created_at=job.created_at,
            updated_at=job.updated_at,
            progress=progress,
            error_message=job.error_message,
        ))
    
    return result

