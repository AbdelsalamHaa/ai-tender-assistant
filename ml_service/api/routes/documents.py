"""
Document listing and retrieval endpoints.
"""

import csv
import io
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ml_service.db.session import get_db
from ml_service.db.models import IngestionJob, Document, ExtractedData
from ml_service.schemas.extraction import DocumentEntity, TenderRequirementResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class RequirementSummary(BaseModel):
    """Summary statistics for requirements."""
    total: int = Field(description="Total number of requirements")
    mandatory: int = Field(description="Number of mandatory requirements")
    optional: int = Field(description="Number of optional requirements")


class DocumentSummary(BaseModel):
    """Summary view of a document for listing."""
    job_id: UUID = Field(description="Job identifier")
    filename: str = Field(description="Original filename")
    status: str = Field(description="Ingestion status")
    title: Optional[str] = Field(default=None, description="Extracted title")
    author: Optional[str] = Field(default=None, description="Extracted author")
    document_type: Optional[str] = Field(default=None, description="Document type")
    page_count: Optional[int] = Field(default=None, description="Number of pages")
    chunk_count: Optional[int] = Field(default=None, description="Number of chunks")
    created_at: str = Field(description="Upload timestamp")
    # Tender-specific
    tender_reference: Optional[str] = Field(default=None, description="Tender reference number")
    requirements_summary: Optional[RequirementSummary] = Field(default=None, description="Requirements summary")

    class Config:
        from_attributes = True


class DocumentDetail(BaseModel):
    """Detailed view of a document with all extracted information."""
    job_id: UUID = Field(description="Job identifier")
    filename: str = Field(description="Original filename")
    status: str = Field(description="Ingestion status")
    created_at: str = Field(description="Upload timestamp")
    
    # Document info
    page_count: Optional[int] = Field(default=None, description="Number of pages")
    chunk_count: Optional[int] = Field(default=None, description="Number of chunks")
    content_preview: Optional[str] = Field(default=None, description="First 500 chars of content")
    
    # Extracted data
    title: Optional[str] = Field(default=None, description="Extracted title")
    author: Optional[str] = Field(default=None, description="Extracted author")
    summary: Optional[str] = Field(default=None, description="Document summary")
    document_type: Optional[str] = Field(default=None, description="Document type")
    key_topics: Optional[List[str]] = Field(default=None, description="Key topics")
    entities: Optional[List[DocumentEntity]] = Field(default=None, description="Extracted entities")
    language: Optional[str] = Field(default=None, description="Document language")
    
    # Tender-specific fields
    tender_reference: Optional[str] = Field(default=None, description="Tender reference number")
    submission_deadline: Optional[str] = Field(default=None, description="Submission deadline")
    estimated_value: Optional[str] = Field(default=None, description="Estimated contract value")
    requirements_summary: Optional[RequirementSummary] = Field(default=None, description="Requirements summary")
    requirements: Optional[List[TenderRequirementResponse]] = Field(default=None, description="All extracted requirements")

    class Config:
        from_attributes = True


class RequirementListResponse(BaseModel):
    """Response for requirements listing."""
    job_id: UUID = Field(description="Job identifier")
    filename: str = Field(description="Original filename")
    title: Optional[str] = Field(default=None, description="Document title")
    requirements_summary: RequirementSummary = Field(description="Requirements summary")
    requirements: List[TenderRequirementResponse] = Field(description="All extracted requirements")
    
    # Filter counts by category
    by_category: dict = Field(description="Count by category")


class DocumentListResponse(BaseModel):
    """Response for document listing."""
    documents: List[DocumentSummary]
    total: int
    limit: int
    offset: int


def _get_requirements_summary(requirements: Optional[List[dict]]) -> Optional[RequirementSummary]:
    """Calculate requirements summary from list."""
    if not requirements:
        return None
    
    total = len(requirements)
    mandatory = sum(1 for r in requirements if r.get("classification") == "MANDATORY")
    optional = total - mandatory
    
    return RequirementSummary(total=total, mandatory=mandatory, optional=optional)


def _count_by_category(requirements: List[dict]) -> dict:
    """Count requirements by category."""
    counts = {}
    for req in requirements:
        category = req.get("category", "OTHER")
        counts[category] = counts.get(category, 0) + 1
    return counts


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="List all ingested documents with their basic information and extracted metadata.",
)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100, description="Number of documents to return"),
    offset: int = Query(default=0, ge=0, description="Number of documents to skip"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status: PENDING, PROCESSING, COMPLETED, FAILED",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List all ingested documents with extracted metadata.
    
    Returns documents sorted by creation date (newest first).
    Use status filter to show only completed documents.
    """
    # Build query with eager loading
    query = (
        select(IngestionJob)
        .options(
            selectinload(IngestionJob.extracted_data),
            selectinload(IngestionJob.document),
        )
        .order_by(IngestionJob.created_at.desc())
    )
    
    # Apply status filter
    if status_filter:
        query = query.where(IngestionJob.status == status_filter.upper())
    
    # Get total count (without pagination)
    count_query = select(IngestionJob)
    if status_filter:
        count_query = count_query.where(IngestionJob.status == status_filter.upper())
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    # Build response
    documents = []
    for job in jobs:
        extracted = job.extracted_data
        doc = job.document
        
        req_summary = None
        if extracted and extracted.requirements:
            req_summary = _get_requirements_summary(extracted.requirements)
        
        documents.append(DocumentSummary(
            job_id=job.id,
            filename=job.filename,
            status=job.status,
            title=extracted.title if extracted else None,
            author=extracted.author if extracted else None,
            document_type=extracted.document_type if extracted else None,
            page_count=job.total_pages,
            chunk_count=job.total_chunks,
            created_at=job.created_at.isoformat(),
            tender_reference=extracted.tender_reference if extracted else None,
            requirements_summary=req_summary,
        ))
    
    return DocumentListResponse(
        documents=documents,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    response_model=DocumentDetail,
    summary="Get document details",
    description="Get full details of a document including all extracted information and requirements.",
)
async def get_document_detail(
    job_id: UUID,
    include_requirements: bool = Query(default=True, description="Include all requirements in response"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a document.
    
    Includes extracted metadata, summary, key topics, entities, and requirements.
    """
    # Query with eager loading
    query = (
        select(IngestionJob)
        .options(
            selectinload(IngestionJob.extracted_data),
            selectinload(IngestionJob.document),
        )
        .where(IngestionJob.id == job_id)
    )
    
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with job_id {job_id} not found",
        )
    
    extracted = job.extracted_data
    doc = job.document
    
    # Get content preview
    content_preview = None
    if doc and doc.content:
        content_preview = doc.content[:500] + ("..." if len(doc.content) > 500 else "")
    
    # Build requirements response
    req_summary = None
    requirements = None
    if extracted and extracted.requirements:
        req_summary = _get_requirements_summary(extracted.requirements)
        if include_requirements:
            requirements = [
                TenderRequirementResponse(
                    requirement_id=r.get("requirement_id", ""),
                    category=r.get("category", "OTHER"),
                    requirement_text=r.get("requirement_text", ""),
                    classification=r.get("classification", "MANDATORY"),
                    compliance_status=r.get("compliance_status", "UNKNOWN"),
                    page_number=r.get("page_number"),
                    source_section=r.get("source_section"),
                    notes=r.get("notes"),
                )
                for r in extracted.requirements
            ]
    
    return DocumentDetail(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        created_at=job.created_at.isoformat(),
        page_count=job.total_pages,
        chunk_count=job.total_chunks,
        content_preview=content_preview,
        title=extracted.title if extracted else None,
        author=extracted.author if extracted else None,
        summary=extracted.summary if extracted else None,
        document_type=extracted.document_type if extracted else None,
        key_topics=extracted.key_topics if extracted else None,
        entities=extracted.entities if extracted else None,
        language=extracted.language if extracted else None,
        tender_reference=extracted.tender_reference if extracted else None,
        submission_deadline=extracted.submission_deadline if extracted else None,
        estimated_value=extracted.estimated_value if extracted else None,
        requirements_summary=req_summary,
        requirements=requirements,
    )


@router.get(
    "/{job_id}/requirements",
    response_model=RequirementListResponse,
    summary="Get document requirements",
    description="Get all extracted requirements from a tender document.",
)
async def get_document_requirements(
    job_id: UUID,
    category: Optional[str] = Query(default=None, description="Filter by category"),
    classification: Optional[str] = Query(default=None, description="Filter by MANDATORY or OPTIONAL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all requirements extracted from a tender document.
    
    Supports filtering by category and classification.
    """
    query = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.extracted_data))
        .where(IngestionJob.id == job_id)
    )
    
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with job_id {job_id} not found",
        )
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready. Current status: {job.status}",
        )
    
    extracted = job.extracted_data
    if not extracted or not extracted.requirements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No requirements found for this document",
        )
    
    # Filter requirements
    requirements = extracted.requirements
    
    if category:
        requirements = [r for r in requirements if r.get("category", "").upper() == category.upper()]
    
    if classification:
        requirements = [r for r in requirements if r.get("classification", "").upper() == classification.upper()]
    
    # Convert to response objects
    requirement_responses = [
        TenderRequirementResponse(
            requirement_id=r.get("requirement_id", ""),
            category=r.get("category", "OTHER"),
            requirement_text=r.get("requirement_text", ""),
            classification=r.get("classification", "MANDATORY"),
            compliance_status=r.get("compliance_status", "UNKNOWN"),
            page_number=r.get("page_number"),
            source_section=r.get("source_section"),
            notes=r.get("notes"),
        )
        for r in requirements
    ]
    
    # Calculate summaries from filtered list
    total = len(requirements)
    mandatory = sum(1 for r in requirements if r.get("classification") == "MANDATORY")
    
    return RequirementListResponse(
        job_id=job.id,
        filename=job.filename,
        title=extracted.title if extracted else None,
        requirements_summary=RequirementSummary(
            total=total,
            mandatory=mandatory,
            optional=total - mandatory,
        ),
        requirements=requirement_responses,
        by_category=_count_by_category(requirements),
    )


@router.get(
    "/{job_id}/content",
    summary="Get full document content",
    description="Get the complete parsed text content of a document.",
)
async def get_document_content(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the full text content of a document.
    
    Only available for completed ingestions.
    """
    query = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.document))
        .where(IngestionJob.id == job_id)
    )
    
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with job_id {job_id} not found",
        )
    
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready. Current status: {job.status}",
        )
    
    if not job.document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document content not found",
        )
    
    return {
        "job_id": str(job.id),
        "filename": job.filename,
        "content": job.document.content,
        "page_count": job.document.page_count,
    }


@router.get(
    "/export/requirements/csv",
    summary="Export all requirements to CSV",
    description="Export all requirements from all completed documents to a CSV file.",
    response_class=StreamingResponse,
)
async def export_requirements_csv(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    classification: Optional[str] = Query(default=None, description="Filter by MANDATORY or OPTIONAL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all requirements from all documents to a CSV file.
    
    Each row includes:
    - Document source information (filename, title, tender reference)
    - Requirement details (ID, category, text, classification, compliance, etc.)
    
    Supports filtering by category and classification.
    """
    # Query all completed jobs with extracted data
    query = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.extracted_data))
        .where(IngestionJob.status == "COMPLETED")
        .order_by(IngestionJob.created_at.desc())
    )
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Write header row
    headers = [
        "Document Filename",
        "Document Title",
        "Tender Reference",
        "Document Type",
        "Requirement ID",
        "Category",
        "Requirement Text",
        "Classification",
        "Compliance Status",
        "Page Number",
        "Source Section",
        "Notes",
        "Document Upload Date",
    ]
    writer.writerow(headers)
    
    # Track statistics
    total_requirements = 0
    total_documents = 0
    
    # Process each job
    for job in jobs:
        extracted = job.extracted_data
        if not extracted or not extracted.requirements:
            continue
        
        requirements = extracted.requirements
        
        # Apply filters
        if category:
            requirements = [r for r in requirements if r.get("category", "").upper() == category.upper()]
        
        if classification:
            requirements = [r for r in requirements if r.get("classification", "").upper() == classification.upper()]
        
        if not requirements:
            continue
        
        total_documents += 1
        
        # Write each requirement as a row
        for req in requirements:
            page_num = req.get("page_number")
            row = [
                job.filename,
                extracted.title or "",
                extracted.tender_reference or "",
                extracted.document_type or "",
                req.get("requirement_id", ""),
                req.get("category", "OTHER"),
                req.get("requirement_text", ""),
                req.get("classification", "MANDATORY"),
                req.get("compliance_status", "UNKNOWN"),
                str(page_num) if page_num is not None else "",
                req.get("source_section", "") or "",
                req.get("notes", "") or "",
                job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else "",
            ]
            writer.writerow(row)
            total_requirements += 1
    
    # Reset stream position
    output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"requirements_export_{timestamp}.csv"
    
    # Add filter info to filename if filters applied
    if category or classification:
        filter_parts = []
        if category:
            filter_parts.append(f"cat-{category}")
        if classification:
            filter_parts.append(f"class-{classification}")
        filename = f"requirements_export_{'-'.join(filter_parts)}_{timestamp}.csv"
    
    logger.info(f"Exported {total_requirements} requirements from {total_documents} documents to CSV")
    
    # Return streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Requirements": str(total_requirements),
            "X-Total-Documents": str(total_documents),
        },
    )


@router.get(
    "/export/requirements/json",
    summary="Export all requirements to JSON",
    description="Export all requirements from all completed documents as JSON.",
)
async def export_requirements_json(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    classification: Optional[str] = Query(default=None, description="Filter by MANDATORY or OPTIONAL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all requirements from all documents as JSON.
    
    Useful for programmatic access to all requirements.
    """
    # Query all completed jobs with extracted data
    query = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.extracted_data))
        .where(IngestionJob.status == "COMPLETED")
        .order_by(IngestionJob.created_at.desc())
    )
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    all_requirements = []
    documents_with_requirements = []
    
    for job in jobs:
        extracted = job.extracted_data
        if not extracted or not extracted.requirements:
            continue
        
        requirements = extracted.requirements
        
        # Apply filters
        if category:
            requirements = [r for r in requirements if r.get("category", "").upper() == category.upper()]
        
        if classification:
            requirements = [r for r in requirements if r.get("classification", "").upper() == classification.upper()]
        
        if not requirements:
            continue
        
        doc_info = {
            "job_id": str(job.id),
            "filename": job.filename,
            "title": extracted.title,
            "tender_reference": extracted.tender_reference,
            "document_type": extracted.document_type,
            "upload_date": job.created_at.isoformat() if job.created_at else None,
            "requirements_count": len(requirements),
        }
        documents_with_requirements.append(doc_info)
        
        for req in requirements:
            all_requirements.append({
                "source_document": {
                    "job_id": str(job.id),
                    "filename": job.filename,
                    "title": extracted.title,
                    "tender_reference": extracted.tender_reference,
                },
                "requirement_id": req.get("requirement_id", ""),
                "category": req.get("category", "OTHER"),
                "requirement_text": req.get("requirement_text", ""),
                "classification": req.get("classification", "MANDATORY"),
                "compliance_status": req.get("compliance_status", "UNKNOWN"),
                "page_number": req.get("page_number"),
                "source_section": req.get("source_section"),
                "notes": req.get("notes"),
            })
    
    # Calculate category breakdown
    category_counts = {}
    classification_counts = {"MANDATORY": 0, "OPTIONAL": 0}
    compliance_counts = {"YES": 0, "NO": 0, "PARTIAL": 0, "UNKNOWN": 0}
    
    for req in all_requirements:
        cat = req["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        cls = req["classification"]
        if cls in classification_counts:
            classification_counts[cls] += 1
        
        comp = req["compliance_status"]
        if comp in compliance_counts:
            compliance_counts[comp] += 1
    
    return {
        "export_date": datetime.now().isoformat(),
        "filters_applied": {
            "category": category,
            "classification": classification,
        },
        "summary": {
            "total_requirements": len(all_requirements),
            "total_documents": len(documents_with_requirements),
            "by_category": category_counts,
            "by_classification": classification_counts,
            "by_compliance": compliance_counts,
        },
        "documents": documents_with_requirements,
        "requirements": all_requirements,
    }
