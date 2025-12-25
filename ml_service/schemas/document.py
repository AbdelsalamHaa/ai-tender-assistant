"""
Pydantic schemas for document endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response containing parsed document content."""
    id: UUID = Field(description="Document unique identifier")
    job_id: UUID = Field(description="Associated job identifier")
    content: str = Field(description="Raw parsed text content")
    page_count: Optional[int] = Field(
        default=None,
        description="Number of pages in the document",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Document metadata",
    )
    created_at: datetime = Field(description="Document creation timestamp")

    class Config:
        from_attributes = True

