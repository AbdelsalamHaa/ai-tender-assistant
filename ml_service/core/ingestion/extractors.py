"""
Structured data extraction using LlamaIndex and Pydantic.
Specialized for tender document requirement extraction with page tracking.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from llama_index.core.llms import LLM
from llama_index.core.prompts import PromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentEntity(BaseModel):
    """An entity extracted from the document."""
    name: str = Field(description="Name of the entity")
    entity_type: str = Field(description="Type: PERSON, ORGANIZATION, LOCATION, DATE, OTHER")


class TenderRequirement(BaseModel):
    """A single requirement from a tender document."""
    requirement_id: str = Field(description="Unique ID like REQ-001, REQ-002")
    category: str = Field(description="Category: EQUIPMENT_SPECIFICATION, TIMELINE, COMPLIANCE, TECHNICAL, FINANCIAL, LEGAL, DOCUMENTATION, QUALITY, SAFETY, ENVIRONMENTAL, DELIVERY, WARRANTY, OTHER")
    requirement_text: str = Field(description="The specific requirement text")
    classification: str = Field(description="MANDATORY or OPTIONAL")
    compliance_status: str = Field(default="UNKNOWN", description="YES, NO, PARTIAL, or UNKNOWN")
    page_number: Optional[int] = Field(default=None, description="Page number where requirement was found (1-indexed)")
    source_section: Optional[str] = Field(default=None, description="Section where requirement was found")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class TenderMetadataSchema(BaseModel):
    """Schema for tender document metadata extraction."""
    title: str = Field(description="The title of the tender document")
    author: Optional[str] = Field(default=None, description="Issuing organization")
    summary: str = Field(description="Brief summary of the tender scope")
    document_type: str = Field(description="Type: TENDER, RFP, RFQ, CONTRACT, SPECIFICATION, OTHER")
    key_topics: List[str] = Field(default=[], description="Main topics covered")
    entities: List[DocumentEntity] = Field(default=[], description="Key entities")
    language: str = Field(default="en", description="Primary language code")
    tender_reference: Optional[str] = Field(default=None, description="Tender reference number")
    submission_deadline: Optional[str] = Field(default=None, description="Submission deadline")
    estimated_value: Optional[str] = Field(default=None, description="Estimated contract value")


class RequirementsExtractionSchema(BaseModel):
    """Schema for requirements extraction response."""
    requirements: List[TenderRequirement] = Field(default=[], description="List of requirements")
    has_more: bool = Field(default=False, description="Whether there might be more requirements")


METADATA_EXTRACTION_PROMPT = PromptTemplate(
    template="""You are an expert tender document analyzer. Analyze the following tender/RFP document and extract metadata.

Document Content:
{content}

Extract the following information in JSON format:
1. title: The document title or tender name
2. author: The issuing organization if identifiable
3. summary: A 2-3 sentence summary of the tender scope and purpose
4. document_type: One of [TENDER, RFP, RFQ, CONTRACT, SPECIFICATION, TECHNICAL_DOCUMENT, OTHER]
5. key_topics: List of 3-7 main topics (e.g., "Electrical Equipment", "Transformers", "Installation Services")
6. entities: Key organizations, locations, dates mentioned
7. language: Primary language code (e.g., "en", "ar", "fr")
8. tender_reference: The tender reference/ID number if present
9. submission_deadline: Submission deadline date if mentioned
10. estimated_value: Estimated contract value if mentioned

Respond with valid JSON only.
"""
)


REQUIREMENTS_EXTRACTION_PROMPT = PromptTemplate(
    template="""You are an expert at extracting requirements from tender documents. 
Analyze the following section of a tender document and extract ALL requirements.

The document section is from PAGE {page_start} to PAGE {page_end}.

A requirement is any statement that specifies:
- What equipment/materials must be provided (e.g., "500 MVA transformer, 400/220kV ICT")
- Technical specifications that must be met
- Timelines or deadlines
- Compliance standards or certifications required
- Documentation that must be submitted
- Quality standards
- Safety requirements
- Warranty terms
- Delivery conditions

Document Section:
{content}

For EACH requirement found, extract:
1. requirement_id: Assign sequential IDs (REQ-001, REQ-002, etc.) starting from {start_id}
2. category: One of [EQUIPMENT_SPECIFICATION, TIMELINE, COMPLIANCE, TECHNICAL, FINANCIAL, LEGAL, DOCUMENTATION, QUALITY, SAFETY, ENVIRONMENTAL, DELIVERY, WARRANTY, OTHER]
3. requirement_text: The exact or summarized requirement text
4. classification: MANDATORY (must comply) or OPTIONAL (preferred but not required)
5. compliance_status: Set to "UNKNOWN" (will be assessed later)
6. page_number: The page number where this requirement appears (look for [PAGE X] markers in the text, use the page number from the marker)
7. source_section: The section heading if identifiable
8. notes: Any additional context

IMPORTANT: 
- Look for [PAGE X] markers in the text to determine page numbers
- Extract ALL requirements you can find
- Be thorough and accurate with page numbers for traceability

Return a JSON object with:
- requirements: Array of requirement objects (each MUST include page_number)
- has_more: true if this appears to be a partial extraction

Respond with valid JSON only.
"""
)


class StructuredExtractor:
    """
    Extract structured data from tender documents using LLM.
    Handles both metadata extraction and detailed requirement extraction with page tracking.
    """
    
    def __init__(self, llm: LLM):
        """
        Initialize the extractor.
        
        Args:
            llm: LlamaIndex LLM instance
        """
        self.llm = llm
        self.metadata_prompt = METADATA_EXTRACTION_PROMPT
        self.requirements_prompt = REQUIREMENTS_EXTRACTION_PROMPT
    
    def extract(
        self, 
        content: str,
        pages_with_content: Optional[List[Tuple[int, str]]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data including requirements from tender document.
        
        Args:
            content: Full document text content (with [PAGE X] markers)
            pages_with_content: Optional list of (page_number, page_text) tuples
            
        Returns:
            Dictionary containing metadata and requirements
        """
        # Step 1: Extract metadata from first part of document
        metadata = self._extract_metadata(content[:15000])
        
        # Step 2: Extract requirements with page tracking
        if pages_with_content:
            requirements = self._extract_requirements_with_pages(pages_with_content)
        else:
            requirements = self._extract_requirements(content)
        
        # Combine results
        result = {
            **metadata,
            "requirements": requirements,
        }
        
        logger.info(f"Extracted {len(requirements)} requirements from document")
        
        return result
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract document metadata."""
        try:
            structured_llm = self.llm.as_structured_llm(
                output_cls=TenderMetadataSchema
            )
            
            formatted_prompt = self.metadata_prompt.format(content=content)
            response = structured_llm.complete(formatted_prompt)
            
            if hasattr(response, 'raw'):
                extracted = response.raw
            else:
                extracted = TenderMetadataSchema.model_validate_json(response.text)
            
            result = extracted.model_dump()
            
            # Convert entities to serializable format
            if result.get("entities"):
                result["entities"] = [
                    {"name": e["name"], "entity_type": e["entity_type"]}
                    for e in result["entities"]
                ]
            
            return result
            
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            return self._fallback_metadata(content)
    
    def _extract_requirements_with_pages(
        self, 
        pages_with_content: List[Tuple[int, str]]
    ) -> List[Dict[str, Any]]:
        """
        Extract requirements from document with accurate page tracking.
        Processes pages in batches to maintain page context.
        """
        all_requirements = []
        
        # Process pages in batches (e.g., 3-5 pages at a time for context)
        batch_size = 4
        total_pages = len(pages_with_content)
        
        logger.info(f"Processing {total_pages} pages for requirement extraction")
        
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch_pages = pages_with_content[batch_start:batch_end]
            
            # Build content with page markers
            batch_content = ""
            page_start = batch_pages[0][0]
            page_end = batch_pages[-1][0]
            
            for page_num, page_text in batch_pages:
                batch_content += f"\n[PAGE {page_num}]\n{page_text}\n"
            
            start_id = len(all_requirements) + 1
            
            try:
                batch_requirements = self._extract_requirements_from_chunk_with_pages(
                    batch_content,
                    page_start=page_start,
                    page_end=page_end,
                    start_id=start_id
                )
                
                # Deduplicate and add
                for req in batch_requirements:
                    if not self._is_duplicate(req, all_requirements):
                        all_requirements.append(req)
                
                logger.info(
                    f"Pages {page_start}-{page_end}: Found {len(batch_requirements)} requirements"
                )
                
            except Exception as e:
                logger.warning(f"Failed to extract requirements from pages {page_start}-{page_end}: {e}")
                continue
        
        # Re-number requirements sequentially
        for i, req in enumerate(all_requirements, 1):
            req["requirement_id"] = f"REQ-{i:03d}"
        
        return all_requirements
    
    def _extract_requirements_from_chunk_with_pages(
        self,
        content: str,
        page_start: int,
        page_end: int,
        start_id: int = 1
    ) -> List[Dict[str, Any]]:
        """Extract requirements from a chunk with page tracking."""
        try:
            formatted_prompt = self.requirements_prompt.format(
                content=content,
                page_start=page_start,
                page_end=page_end,
                start_id=start_id
            )
            
            response = self.llm.complete(formatted_prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            data = self._parse_json_response(response_text)
            
            if not data:
                return []
            
            requirements = data.get("requirements", [])
            
            # Validate and clean requirements
            cleaned = []
            for req in requirements:
                page_num = req.get("page_number")
                
                # Validate page number is within expected range
                if page_num is not None:
                    try:
                        page_num = int(page_num)
                        if page_num < page_start or page_num > page_end:
                            # If out of range, default to start of batch
                            page_num = page_start
                    except (ValueError, TypeError):
                        page_num = page_start
                else:
                    # If not provided, try to infer from content
                    page_num = self._infer_page_number(
                        req.get("requirement_text", ""),
                        content,
                        page_start
                    )
                
                cleaned.append({
                    "requirement_id": req.get("requirement_id", f"REQ-{start_id + len(cleaned):03d}"),
                    "category": self._normalize_category(req.get("category", "OTHER")),
                    "requirement_text": req.get("requirement_text", "")[:1000],
                    "classification": self._normalize_classification(req.get("classification", "MANDATORY")),
                    "compliance_status": req.get("compliance_status", "UNKNOWN"),
                    "page_number": page_num,
                    "source_section": req.get("source_section"),
                    "notes": req.get("notes"),
                })
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Requirements extraction error: {e}")
            return []
    
    def _infer_page_number(
        self, 
        requirement_text: str, 
        content: str,
        default_page: int
    ) -> int:
        """Infer page number by finding where requirement text appears in content."""
        if not requirement_text:
            return default_page
        
        # Find the requirement text (or part of it) in content
        search_text = requirement_text[:100].lower()
        content_lower = content.lower()
        
        pos = content_lower.find(search_text)
        if pos == -1:
            # Try with first few words
            words = search_text.split()[:5]
            search_text = " ".join(words)
            pos = content_lower.find(search_text)
        
        if pos == -1:
            return default_page
        
        # Find the nearest [PAGE X] marker before this position
        page_pattern = r'\[PAGE (\d+)\]'
        content_before = content[:pos]
        matches = list(re.finditer(page_pattern, content_before))
        
        if matches:
            return int(matches[-1].group(1))
        
        return default_page
    
    def _extract_requirements(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract requirements from document (legacy method without page tracking).
        """
        all_requirements = []
        
        chunk_size = 8000
        overlap = 500
        chunks = self._split_into_chunks(content, chunk_size, overlap)
        
        logger.info(f"Processing {len(chunks)} chunks for requirement extraction")
        
        for i, chunk in enumerate(chunks):
            start_id = len(all_requirements) + 1
            
            # Try to determine page range from chunk content
            page_start, page_end = self._get_page_range_from_chunk(chunk)
            
            try:
                chunk_requirements = self._extract_requirements_from_chunk_with_pages(
                    chunk,
                    page_start=page_start or 1,
                    page_end=page_end or 1,
                    start_id=start_id
                )
                
                for req in chunk_requirements:
                    if not self._is_duplicate(req, all_requirements):
                        all_requirements.append(req)
                
                logger.info(f"Chunk {i+1}/{len(chunks)}: Found {len(chunk_requirements)} requirements")
                
            except Exception as e:
                logger.warning(f"Failed to extract requirements from chunk {i+1}: {e}")
                continue
        
        # Re-number requirements sequentially
        for i, req in enumerate(all_requirements, 1):
            req["requirement_id"] = f"REQ-{i:03d}"
        
        return all_requirements
    
    def _get_page_range_from_chunk(self, chunk: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract page range from [PAGE X] markers in chunk."""
        page_pattern = r'\[PAGE (\d+)\]'
        matches = re.findall(page_pattern, chunk)
        
        if not matches:
            return None, None
        
        pages = [int(p) for p in matches]
        return min(pages), max(pages)
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        try:
            if response_text.startswith("{"):
                return json.loads(response_text)
            elif "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                return json.loads(response_text[json_start:json_end])
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                return json.loads(response_text[json_start:json_end])
            else:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response_text[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
        return None
    
    def _split_into_chunks(
        self, 
        content: str, 
        chunk_size: int, 
        overlap: int
    ) -> List[str]:
        """Split content into overlapping chunks, preserving page markers."""
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            
            # Try to break at a page boundary or sentence
            if end < len(content):
                # Prefer breaking at page markers
                page_marker = chunk.rfind("[PAGE")
                if page_marker > chunk_size * 0.5:
                    chunk = content[start:start + page_marker]
                    end = start + page_marker
                else:
                    last_period = chunk.rfind(".")
                    last_newline = chunk.rfind("\n")
                    break_point = max(last_period, last_newline)
                    
                    if break_point > chunk_size * 0.7:
                        chunk = content[start:start + break_point + 1]
                        end = start + break_point + 1
            
            chunks.append(chunk)
            start = end - overlap
            
            if start >= len(content):
                break
        
        return chunks
    
    def _is_duplicate(
        self, 
        new_req: Dict[str, Any], 
        existing: List[Dict[str, Any]]
    ) -> bool:
        """Check if a requirement is a duplicate."""
        new_text = new_req.get("requirement_text", "").lower().strip()
        
        if len(new_text) < 10:
            return True
        
        for existing_req in existing:
            existing_text = existing_req.get("requirement_text", "").lower().strip()
            
            if new_text == existing_text:
                return True
            
            if len(new_text) > 20 and len(existing_text) > 20:
                shorter = min(len(new_text), len(existing_text))
                if new_text[:shorter] == existing_text[:shorter]:
                    return True
        
        return False
    
    def _normalize_category(self, category: str) -> str:
        """Normalize category to valid values."""
        valid_categories = {
            "EQUIPMENT_SPECIFICATION", "TIMELINE", "COMPLIANCE", "TECHNICAL",
            "FINANCIAL", "LEGAL", "DOCUMENTATION", "QUALITY", "SAFETY",
            "ENVIRONMENTAL", "DELIVERY", "WARRANTY", "OTHER"
        }
        
        category_upper = category.upper().replace(" ", "_").replace("-", "_")
        
        category_mapping = {
            "EQUIPMENT": "EQUIPMENT_SPECIFICATION",
            "SPEC": "EQUIPMENT_SPECIFICATION",
            "SPECIFICATION": "EQUIPMENT_SPECIFICATION",
            "TECHNICAL_SPECIFICATION": "TECHNICAL",
            "TIME": "TIMELINE",
            "SCHEDULE": "TIMELINE",
            "DEADLINE": "TIMELINE",
            "LEGAL_COMPLIANCE": "COMPLIANCE",
            "REGULATORY": "COMPLIANCE",
            "DOCUMENT": "DOCUMENTATION",
            "DOCS": "DOCUMENTATION",
            "QUALITY_ASSURANCE": "QUALITY",
            "QA": "QUALITY",
            "HEALTH_SAFETY": "SAFETY",
            "HSE": "SAFETY",
            "ENVIRONMENT": "ENVIRONMENTAL",
            "SHIPPING": "DELIVERY",
            "TRANSPORT": "DELIVERY",
            "GUARANTEE": "WARRANTY",
            "PAYMENT": "FINANCIAL",
            "PRICE": "FINANCIAL",
            "COST": "FINANCIAL",
        }
        
        if category_upper in valid_categories:
            return category_upper
        
        if category_upper in category_mapping:
            return category_mapping[category_upper]
        
        return "OTHER"
    
    def _normalize_classification(self, classification: str) -> str:
        """Normalize classification to MANDATORY or OPTIONAL."""
        classification_upper = classification.upper().strip()
        
        mandatory_keywords = ["MANDATORY", "REQUIRED", "MUST", "SHALL", "ESSENTIAL"]
        optional_keywords = ["OPTIONAL", "PREFERRED", "DESIRED", "MAY", "SHOULD"]
        
        for kw in mandatory_keywords:
            if kw in classification_upper:
                return "MANDATORY"
        
        for kw in optional_keywords:
            if kw in classification_upper:
                return "OPTIONAL"
        
        return "MANDATORY"
    
    def _fallback_metadata(self, content: str) -> Dict[str, Any]:
        """Fallback metadata extraction."""
        try:
            response = self.llm.complete(
                f"""Analyze this tender document and provide:
1. A suitable title (one line)
2. A brief 2-sentence summary
3. The tender reference number if visible

Document (first 3000 chars):
{content[:3000]}

Format:
Title: [title here]
Summary: [summary here]
Reference: [reference or "Not specified"]
"""
            )
            
            text = response.text
            title = "Untitled Tender Document"
            summary = "Tender document content available for review."
            reference = None
            
            if "Title:" in text:
                title_line = text.split("Title:")[1].split("\n")[0].strip()
                if title_line:
                    title = title_line
            
            if "Summary:" in text:
                summary_part = text.split("Summary:")[1].split("\n")[0].strip()
                if summary_part:
                    summary = summary_part[:500]
            
            if "Reference:" in text:
                ref_part = text.split("Reference:")[1].split("\n")[0].strip()
                if ref_part and ref_part.lower() != "not specified":
                    reference = ref_part
            
            return {
                "title": title,
                "author": None,
                "summary": summary,
                "document_type": "TENDER",
                "key_topics": [],
                "entities": [],
                "language": "en",
                "tender_reference": reference,
                "submission_deadline": None,
                "estimated_value": None,
            }
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return {
                "title": "Untitled Tender Document",
                "author": None,
                "summary": "Failed to extract document summary.",
                "document_type": "TENDER",
                "key_topics": [],
                "entities": [],
                "language": "en",
                "tender_reference": None,
                "submission_deadline": None,
                "estimated_value": None,
            }
