"""
Repository for document and extracted data database operations.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ml_service.db.models import Document, ExtractedData


class DocumentRepository:
    """Repository for Document and ExtractedData CRUD operations."""
    
    # Async methods for FastAPI
    
    @staticmethod
    async def create_document_async(
        session: AsyncSession,
        job_id: UUID,
        content: str,
        page_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a document record asynchronously."""
        doc = Document(
            job_id=job_id,
            content=content,
            page_count=page_count,
            metadata_=metadata,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc
    
    @staticmethod
    async def get_document_by_job_id_async(
        session: AsyncSession,
        job_id: UUID,
    ) -> Optional[Document]:
        """Get document by job ID asynchronously."""
        result = await session.execute(
            select(Document).where(Document.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    # Alias for compatibility
    @staticmethod
    async def get_by_job_id_async(
        session: AsyncSession,
        job_id: UUID,
    ) -> Optional[Document]:
        """Get document by job ID asynchronously (alias)."""
        return await DocumentRepository.get_document_by_job_id_async(session, job_id)
    
    @staticmethod
    async def create_extracted_data_async(
        session: AsyncSession,
        job_id: UUID,
        title: Optional[str] = None,
        author: Optional[str] = None,
        summary: Optional[str] = None,
        document_type: Optional[str] = None,
        key_topics: Optional[List[str]] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        language: str = "en",
        # Tender-specific fields
        tender_reference: Optional[str] = None,
        submission_deadline: Optional[str] = None,
        estimated_value: Optional[str] = None,
        requirements: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractedData:
        """Create extracted data record asynchronously."""
        extracted = ExtractedData(
            job_id=job_id,
            title=title,
            author=author,
            summary=summary,
            document_type=document_type,
            key_topics=key_topics,
            entities=entities,
            language=language,
            tender_reference=tender_reference,
            submission_deadline=submission_deadline,
            estimated_value=estimated_value,
            requirements=requirements,
        )
        session.add(extracted)
        await session.commit()
        await session.refresh(extracted)
        return extracted
    
    @staticmethod
    async def get_extracted_data_by_job_id_async(
        session: AsyncSession,
        job_id: UUID,
    ) -> Optional[ExtractedData]:
        """Get extracted data by job ID asynchronously."""
        result = await session.execute(
            select(ExtractedData).where(ExtractedData.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    # Sync methods for Celery workers
    
    @staticmethod
    def create_document_sync(
        session: Session,
        job_id: UUID,
        content: str,
        page_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a document record synchronously."""
        doc = Document(
            job_id=job_id,
            content=content,
            page_count=page_count,
            metadata_=metadata,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc
    
    @staticmethod
    def get_document_by_job_id_sync(
        session: Session,
        job_id: UUID,
    ) -> Optional[Document]:
        """Get document by job ID synchronously."""
        return session.query(Document).filter(
            Document.job_id == job_id
        ).first()
    
    @staticmethod
    def create_extracted_data_sync(
        session: Session,
        job_id: UUID,
        title: Optional[str] = None,
        author: Optional[str] = None,
        summary: Optional[str] = None,
        document_type: Optional[str] = None,
        key_topics: Optional[List[str]] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        language: str = "en",
        # Tender-specific fields
        tender_reference: Optional[str] = None,
        submission_deadline: Optional[str] = None,
        estimated_value: Optional[str] = None,
        requirements: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractedData:
        """Create extracted data record synchronously."""
        extracted = ExtractedData(
            job_id=job_id,
            title=title,
            author=author,
            summary=summary,
            document_type=document_type,
            key_topics=key_topics,
            entities=entities,
            language=language,
            tender_reference=tender_reference,
            submission_deadline=submission_deadline,
            estimated_value=estimated_value,
            requirements=requirements,
        )
        session.add(extracted)
        session.commit()
        session.refresh(extracted)
        return extracted
    
    @staticmethod
    def get_extracted_data_by_job_id_sync(
        session: Session,
        job_id: UUID,
    ) -> Optional[ExtractedData]:
        """Get extracted data by job ID synchronously."""
        return session.query(ExtractedData).filter(
            ExtractedData.job_id == job_id
        ).first()


class ExtractedDataRepository:
    """Dedicated repository for ExtractedData operations."""
    
    @staticmethod
    async def get_by_job_id_async(
        session: AsyncSession,
        job_id: UUID,
    ) -> Optional[ExtractedData]:
        """Get extracted data by job ID asynchronously."""
        result = await session.execute(
            select(ExtractedData).where(ExtractedData.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def get_by_job_id_sync(
        session: Session,
        job_id: UUID,
    ) -> Optional[ExtractedData]:
        """Get extracted data by job ID synchronously."""
        return session.query(ExtractedData).filter(
            ExtractedData.job_id == job_id
        ).first()
