"""
Repository for ingestion job database operations.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ml_service.db.models import IngestionJob, JobStatus


class JobRepository:
    """Repository for IngestionJob CRUD operations."""
    
    # Async methods for FastAPI
    
    @staticmethod
    async def create_async(
        session: AsyncSession,
        filename: str,
        file_path: str,
    ) -> IngestionJob:
        """Create a new ingestion job asynchronously."""
        job = IngestionJob(
            filename=filename,
            file_path=file_path,
            status=JobStatus.PENDING.value,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job
    
    @staticmethod
    async def get_by_id_async(
        session: AsyncSession,
        job_id: UUID,
    ) -> Optional[IngestionJob]:
        """Get a job by ID asynchronously."""
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.id == job_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_status_async(
        session: AsyncSession,
        job_id: UUID,
        status: JobStatus,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        total_pages: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> Optional[IngestionJob]:
        """Update job status asynchronously."""
        update_data = {"status": status.value if isinstance(status, JobStatus) else status}
        if current_step is not None:
            update_data["current_step"] = current_step
        if error_message is not None:
            update_data["error_message"] = error_message
        if total_pages is not None:
            update_data["total_pages"] = total_pages
        if total_chunks is not None:
            update_data["total_chunks"] = total_chunks
        
        await session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id)
            .values(**update_data)
        )
        await session.commit()
        return await JobRepository.get_by_id_async(session, job_id)
    
    @staticmethod
    async def list_jobs_async(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IngestionJob]:
        """List jobs with pagination asynchronously."""
        result = await session.execute(
            select(IngestionJob)
            .order_by(IngestionJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    # Sync methods for Celery workers
    
    @staticmethod
    def create_sync(
        session: Session,
        filename: str,
        file_path: str,
    ) -> IngestionJob:
        """Create a new ingestion job synchronously."""
        job = IngestionJob(
            filename=filename,
            file_path=file_path,
            status=JobStatus.PENDING.value,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    
    @staticmethod
    def get_by_id_sync(
        session: Session,
        job_id: UUID,
    ) -> Optional[IngestionJob]:
        """Get a job by ID synchronously."""
        return session.query(IngestionJob).filter(
            IngestionJob.id == job_id
        ).first()
    
    @staticmethod
    def update_status_sync(
        session: Session,
        job_id: UUID,
        status: JobStatus,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        total_pages: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> Optional[IngestionJob]:
        """Update job status synchronously."""
        job = JobRepository.get_by_id_sync(session, job_id)
        if job:
            job.status = status.value if isinstance(status, JobStatus) else status
            if current_step is not None:
                job.current_step = current_step
            if error_message is not None:
                job.error_message = error_message
            if total_pages is not None:
                job.total_pages = total_pages
            if total_chunks is not None:
                job.total_chunks = total_chunks
            session.commit()
            session.refresh(job)
        return job

