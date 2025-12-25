"""
Pydantic schemas for structured data extraction.
These schemas are used both for LLM extraction and API responses.
"""

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentEntity(BaseModel):
    """An entity extracted from the document."""
    name: str = Field(description="Name of the entity (person, org, location)")
    entity_type: str = Field(
        description="Type: PERSON, ORGANIZATION, LOCATION, DATE, OTHER"
    )


class TenderRequirement(BaseModel):
    """
    A single requirement extracted from a tender document.
    """
    requirement_id: str = Field(
        description="Unique identifier for the requirement (e.g., REQ-001, REQ-002)"
    )
    category: str = Field(
        description="Category of requirement: EQUIPMENT_SPECIFICATION, TIMELINE, COMPLIANCE, TECHNICAL, FINANCIAL, LEGAL, DOCUMENTATION, QUALITY, SAFETY, ENVIRONMENTAL, DELIVERY, WARRANTY, OTHER"
    )
    requirement_text: str = Field(
        description="The specific requirement text extracted from the document"
    )
    classification: str = Field(
        description="Whether the requirement is MANDATORY or OPTIONAL"
    )
    compliance_status: str = Field(
        default="UNKNOWN",
        description="Compliance status: YES, NO, PARTIAL, or UNKNOWN"
    )
    page_number: Optional[int] = Field(
        default=None,
        description="The page number where this requirement was found (1-indexed)"
    )
    source_section: Optional[str] = Field(
        default=None,
        description="The section or heading where this requirement was found"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes or context about the requirement"
    )


class ExtractedDocument(BaseModel):
    """
    Structured data extracted from a tender/PDF document.
    This schema is used by LlamaIndex for LLM-based extraction.
    """
    
    title: str = Field(
        description="The title of the document, usually found at the top or first page"
    )
    author: Optional[str] = Field(
        default=None,
        description="The author(s) or issuing organization of the document"
    )
    summary: str = Field(
        description="A brief 2-3 sentence summary of the tender/document's main content and scope"
    )
    document_type: str = Field(
        description="The type of document: TENDER, RFP, RFQ, CONTRACT, SPECIFICATION, TECHNICAL_DOCUMENT, OTHER"
    )
    key_topics: List[str] = Field(
        default=[],
        description="List of 3-7 main topics or themes covered in the document"
    )
    entities: List[DocumentEntity] = Field(
        default=[],
        description="Key entities (organizations, locations, dates) mentioned in the document"
    )
    language: str = Field(
        default="en",
        description="Primary language of the document (ISO 639-1 code)"
    )
    # Tender-specific fields
    tender_reference: Optional[str] = Field(
        default=None,
        description="Tender reference number or ID if present"
    )
    submission_deadline: Optional[str] = Field(
        default=None,
        description="Submission deadline date/time if mentioned"
    )
    estimated_value: Optional[str] = Field(
        default=None,
        description="Estimated contract value if mentioned"
    )
    requirements: List[TenderRequirement] = Field(
        default=[],
        description="List of all requirements extracted from the tender document"
    )


class TenderRequirementResponse(BaseModel):
    """API response for a single requirement."""
    requirement_id: str
    category: str
    requirement_text: str
    classification: str
    compliance_status: str
    page_number: Optional[int] = None
    source_section: Optional[str] = None
    notes: Optional[str] = None


class ExtractedDataResponse(BaseModel):
    """API response for extracted document data."""
    id: UUID = Field(description="Extraction record unique identifier")
    job_id: UUID = Field(description="Associated job identifier")
    title: Optional[str] = Field(default=None, description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    summary: Optional[str] = Field(default=None, description="Document summary")
    document_type: Optional[str] = Field(default=None, description="Document type")
    key_topics: Optional[List[str]] = Field(default=None, description="Key topics")
    entities: Optional[List[DocumentEntity]] = Field(
        default=None,
        description="Extracted entities"
    )
    language: str = Field(default="en", description="Document language")
    # Tender-specific fields
    tender_reference: Optional[str] = Field(default=None, description="Tender reference number")
    submission_deadline: Optional[str] = Field(default=None, description="Submission deadline")
    estimated_value: Optional[str] = Field(default=None, description="Estimated contract value")
    requirements: Optional[List[TenderRequirementResponse]] = Field(
        default=None,
        description="Extracted requirements"
    )
    requirements_count: int = Field(default=0, description="Total number of requirements")
    mandatory_count: int = Field(default=0, description="Number of mandatory requirements")
    optional_count: int = Field(default=0, description="Number of optional requirements")
    created_at: datetime = Field(description="Extraction timestamp")

    class Config:
        from_attributes = True


class RequirementsSummary(BaseModel):
    """Summary statistics for requirements."""
    total: int = Field(description="Total number of requirements")
    mandatory: int = Field(description="Number of mandatory requirements")
    optional: int = Field(description="Number of optional requirements")
    by_category: dict = Field(description="Count by category")
    by_compliance: dict = Field(description="Count by compliance status")
