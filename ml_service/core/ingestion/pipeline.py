"""
LlamaIndex-based PDF ingestion pipeline.

This pipeline handles:
1. PDF parsing using SimpleDirectoryReader
2. Structured data extraction using LLM
3. Document chunking using SentenceSplitter
4. Embedding generation using OpenAI
5. Vector storage using PGVectorStore
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from uuid import UUID

from llama_index.core import Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import make_url
from sqlalchemy.orm import Session

from ml_service.config import get_settings
from ml_service.core.ingestion.extractors import StructuredExtractor

logger = logging.getLogger(__name__)


class PDFIngestionPipeline:
    """
    Complete PDF ingestion pipeline using LlamaIndex.
    
    This class orchestrates the entire ingestion process:
    - Parse PDF → Extract structured data → Chunk → Embed → Store
    """
    
    def __init__(self, db_session: Session, job_id: UUID):
        """
        Initialize the ingestion pipeline.
        
        Args:
            db_session: SQLAlchemy database session
            job_id: UUID of the current ingestion job
        """
        self.db_session = db_session
        self.job_id = job_id
        self.settings = get_settings()
        
        # Configure LlamaIndex global settings
        self._configure_llama_index()
        
        # Initialize components
        self.extractor = StructuredExtractor(self.llm)
        self.node_parser = SentenceSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        self.vector_store = self._create_vector_store()
    
    def _configure_llama_index(self) -> None:
        """Configure LlamaIndex global settings."""
        # Set OpenAI API key
        os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        
        # Initialize embedding model
        self.embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,
            dimensions=self.settings.embedding_dimensions,
        )
        
        # Initialize LLM
        self.llm = OpenAI(
            model=self.settings.llm_model,
            temperature=0.1,
        )
        
        # Set global defaults
        Settings.embed_model = self.embed_model
        Settings.llm = self.llm
        Settings.chunk_size = self.settings.chunk_size
        Settings.chunk_overlap = self.settings.chunk_overlap
    
    def _create_vector_store(self) -> PGVectorStore:
        """Create PGVectorStore instance for PostgreSQL + pgvector."""
        url = make_url(self.settings.sync_database_url)
        
        vector_store = PGVectorStore.from_params(
            database=url.database,
            host=url.host,
            port=url.port,
            user=url.username,
            password=url.password,
            table_name=self.settings.vector_table_name,
            embed_dim=self.settings.embedding_dimensions,
            hnsw_kwargs={
                "hnsw_m": self.settings.hnsw_m,
                "hnsw_ef_construction": self.settings.hnsw_ef_construction,
                "hnsw_ef_search": self.settings.hnsw_ef_search,
                "hnsw_dist_method": "vector_cosine_ops",
            },
        )
        
        return vector_store
    
    def parse_pdf(self, file_path: str) -> Tuple[str, int, Dict[str, Any], List[Tuple[int, str]]]:
        """
        Parse a PDF file and extract text content with page tracking.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (full_text, page_count, metadata, pages_with_content)
            where pages_with_content is a list of (page_number, page_text) tuples
        """
        from llama_index.core import SimpleDirectoryReader
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        logger.info(f"Parsing PDF: {file_path}")
        
        # Use SimpleDirectoryReader for single file
        reader = SimpleDirectoryReader(
            input_files=[str(path)],
        )
        documents = reader.load_data()
        
        if not documents:
            raise ValueError(f"No content extracted from PDF: {file_path}")
        
        # Track page content separately for requirement extraction
        # LlamaIndex typically returns one document per page
        pages_with_content: List[Tuple[int, str]] = []
        for i, doc in enumerate(documents):
            page_num = i + 1  # 1-indexed page numbers
            pages_with_content.append((page_num, doc.text))
        
        # Combine all document content (with page markers for context)
        full_text_parts = []
        for page_num, page_text in pages_with_content:
            full_text_parts.append(f"[PAGE {page_num}]\n{page_text}")
        full_text = "\n\n".join(full_text_parts)
        
        page_count = len(documents)
        
        # Collect metadata from first document
        metadata = {}
        if documents[0].metadata:
            metadata = dict(documents[0].metadata)
            # Remove any file system paths for security
            metadata.pop("file_path", None)
        
        logger.info(f"Parsed PDF: {page_count} pages, {len(full_text)} characters")
        
        return full_text, page_count, metadata, pages_with_content
    
    def extract_structured_data(
        self, 
        content: str,
        pages_with_content: Optional[List[Tuple[int, str]]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data and requirements from document content using LLM.
        
        For tender documents, this includes extracting all requirements
        which can number from 1 to 100+.
        
        Args:
            content: Full text content of the document (with page markers)
            pages_with_content: Optional list of (page_number, page_text) tuples
                              for more accurate page number tracking
            
        Returns:
            Dictionary containing extracted metadata and requirements
        """
        logger.info("Extracting structured data and requirements from document")
        
        # Use full content for extraction, passing pages for page number tracking
        extracted = self.extractor.extract(content, pages_with_content)
        
        requirements_count = len(extracted.get('requirements', []))
        logger.info(
            f"Extracted: title='{extracted.get('title', 'Unknown')}', "
            f"requirements={requirements_count}"
        )
        
        return extracted
    
    def chunk_document(
        self,
        content: str,
        job_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextNode]:
        """
        Chunk the document content into smaller pieces.
        
        Args:
            content: Full text content
            job_id: UUID of the ingestion job
            metadata: Optional document metadata
            
        Returns:
            List of TextNode objects
        """
        logger.info("Chunking document")
        
        # Create a Document object
        doc = Document(
            text=content,
            metadata={
                "job_id": str(job_id),
                **(metadata or {}),
            },
        )
        
        # Parse into nodes
        nodes = self.node_parser.get_nodes_from_documents([doc])
        
        # Add job_id to each node's metadata
        for i, node in enumerate(nodes):
            node.metadata["job_id"] = str(job_id)
            node.metadata["chunk_index"] = i
        
        logger.info(f"Created {len(nodes)} chunks")
        
        return nodes
    
    def embed_and_store(self, nodes: List[TextNode]) -> int:
        """
        Generate embeddings and store nodes in vector database.
        
        Args:
            nodes: List of TextNode objects to embed and store
            
        Returns:
            Number of nodes stored
        """
        logger.info(f"Generating embeddings for {len(nodes)} nodes")
        
        # Generate embeddings for all nodes
        for node in nodes:
            embedding = self.embed_model.get_text_embedding(node.text)
            node.embedding = embedding
        
        # Add nodes to vector store
        self.vector_store.add(nodes)
        
        logger.info(f"Stored {len(nodes)} nodes with embeddings")
        
        return len(nodes)
    
    def run_full_pipeline(self, file_path: str) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.
        
        This is a convenience method that runs all steps in sequence.
        For more control, use individual methods.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with ingestion results
        """
        # Step 1: Parse PDF (now returns pages_with_content for page tracking)
        content, page_count, doc_metadata, pages_with_content = self.parse_pdf(file_path)
        
        # Step 2: Extract structured data (with page tracking for requirements)
        extracted = self.extract_structured_data(content, pages_with_content)
        
        # Step 3: Chunk document
        nodes = self.chunk_document(content, self.job_id, doc_metadata)
        
        # Step 4: Embed and store
        chunk_count = self.embed_and_store(nodes)
        
        return {
            "content": content,
            "page_count": page_count,
            "metadata": doc_metadata,
            "extracted": extracted,
            "chunk_count": chunk_count,
        }


async def get_vector_store_index():
    """
    Get a VectorStoreIndex for semantic search queries.
    
    Returns:
        VectorStoreIndex connected to the PostgreSQL vector store
    """
    from llama_index.core import VectorStoreIndex
    
    settings = get_settings()
    
    # Set OpenAI API key
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    # Initialize embedding model
    embed_model = OpenAIEmbedding(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    
    # Set global defaults
    Settings.embed_model = embed_model
    
    # Create vector store connection
    url = make_url(settings.sync_database_url)
    
    vector_store = PGVectorStore.from_params(
        database=url.database,
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        table_name=settings.vector_table_name,
        embed_dim=settings.embedding_dimensions,
    )
    
    # Create index from existing vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )
    
    return index

