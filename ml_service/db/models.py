"""
SQLAlchemy ORM models for the ML service.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class JobStatus(str, PyEnum):
    """Enumeration of possible job statuses."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionJob(Base):
    """
    Tracks the status of PDF ingestion jobs.
    """
    __tablename__ = "ingestion_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Using String instead of native PostgreSQL enum for portability
    status: Mapped[str] = mapped_column(
        String(20),
        default=JobStatus.PENDING.value,
        nullable=False,
    )
    current_step: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    extracted_data: Mapped[Optional["ExtractedData"]] = relationship(
        "ExtractedData",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<IngestionJob(id={self.id}, filename={self.filename}, status={self.status})>"


class Document(Base):
    """
    Stores raw parsed document content.
    """
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    job: Mapped["IngestionJob"] = relationship(
        "IngestionJob",
        back_populates="document",
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, job_id={self.job_id})>"


class ExtractedData(Base):
    """
    Stores structured data extracted from documents using LLM.
    Includes tender-specific fields for requirement extraction.
    """
    __tablename__ = "extracted_data"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    key_topics: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    entities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    
    # Tender-specific fields
    tender_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submission_deadline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    estimated_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requirements: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    job: Mapped["IngestionJob"] = relationship(
        "IngestionJob",
        back_populates="extracted_data",
    )
    
    @property
    def requirements_count(self) -> int:
        """Total number of requirements."""
        return len(self.requirements) if self.requirements else 0
    
    @property
    def mandatory_count(self) -> int:
        """Number of mandatory requirements."""
        if not self.requirements:
            return 0
        return sum(1 for r in self.requirements if r.get("classification") == "MANDATORY")
    
    @property
    def optional_count(self) -> int:
        """Number of optional requirements."""
        if not self.requirements:
            return 0
        return sum(1 for r in self.requirements if r.get("classification") == "OPTIONAL")
    
    def __repr__(self) -> str:
        return f"<ExtractedData(id={self.id}, title={self.title}, requirements={self.requirements_count})>"

