"""
Pydantic schemas for ingestion job endpoints.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class JobProgress(BaseModel):
    """Progress information for an ingestion job."""
    current_step: Optional[str] = Field(
        default=None,
        description="Current processing step",
    )
    steps_completed: List[str] = Field(
        default=[],
        description="List of completed processing steps",
    )
    total_chunks: Optional[int] = Field(
        default=None,
        description="Total number of chunks created",
    )
    total_pages: Optional[int] = Field(
        default=None,
        description="Total number of pages in the document",
    )


class JobCreate(BaseModel):
    """Response after creating a new ingestion job."""
    job_id: UUID = Field(description="Unique identifier for the job")
    status: str = Field(description="Current job status")
    message: str = Field(description="Human-readable message")
    created_at: datetime = Field(description="Job creation timestamp")


class JobResponse(BaseModel):
    """Full job response with all details."""
    job_id: UUID = Field(description="Unique identifier for the job")
    status: str = Field(description="Current job status")
    filename: str = Field(description="Original filename")
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    progress: JobProgress = Field(description="Processing progress details")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if job failed",
    )

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    """Simplified status response for polling."""
    job_id: UUID = Field(description="Unique identifier for the job")
    status: str = Field(description="Current job status")
    current_step: Optional[str] = Field(
        default=None,
        description="Current processing step",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if job failed",
    )

    class Config:
        from_attributes = True

