"""
Semantic search endpoints using LlamaIndex.
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import make_url

from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from ml_service.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


class SearchResult(BaseModel):
    """A single search result."""
    text: str = Field(description="The chunk text content")
    score: float = Field(description="Similarity score (higher is more relevant)")
    job_id: Optional[str] = Field(default=None, description="Source document job ID")
    chunk_index: Optional[int] = Field(default=None, description="Chunk index in document")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class SearchRequest(BaseModel):
    """Request body for semantic search."""
    query: str = Field(description="Search query text", min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class SearchResponse(BaseModel):
    """Response containing search results."""
    query: str = Field(description="Original query")
    results: List[SearchResult] = Field(description="Search results ordered by relevance")
    total_results: int = Field(description="Number of results returned")


def get_vector_store() -> PGVectorStore:
    """Create a PGVectorStore instance for querying."""
    url = make_url(settings.sync_database_url)
    
    vector_store = PGVectorStore.from_params(
        database=url.database,
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        table_name=settings.vector_table_name,
        embed_dim=settings.embedding_dimensions,
        hnsw_kwargs={
            "hnsw_m": settings.hnsw_m,
            "hnsw_ef_construction": settings.hnsw_ef_construction,
            "hnsw_ef_search": settings.hnsw_ef_search,
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )
    
    return vector_store


def get_embed_model() -> OpenAIEmbedding:
    """Get the embedding model."""
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    return OpenAIEmbedding(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic search",
    description="Search through ingested documents using semantic similarity.",
)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic search across all ingested documents.
    
    The search uses vector embeddings to find the most semantically similar
    chunks to your query. Results are ranked by relevance score.
    
    **Example queries:**
    - "What are the main findings of the research?"
    - "Information about machine learning algorithms"
    - "Contract terms and conditions"
    """
    try:
        # Set up embedding model
        embed_model = get_embed_model()
        Settings.embed_model = embed_model
        
        # Get vector store
        vector_store = get_vector_store()
        
        # Create index from vector store
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
        )
        
        # Create retriever with top_k
        retriever = index.as_retriever(
            similarity_top_k=request.top_k,
        )
        
        # Perform search
        nodes = retriever.retrieve(request.query)
        
        # Format results
        results = []
        for node in nodes:
            metadata = node.node.metadata or {}
            results.append(SearchResult(
                text=node.node.text,
                score=node.score or 0.0,
                job_id=metadata.get("job_id"),
                chunk_index=metadata.get("chunk_index"),
                metadata=metadata,
            ))
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get(
    "",
    response_model=SearchResponse,
    summary="Semantic search (GET)",
    description="Search using query parameters instead of request body.",
)
async def semantic_search_get(
    q: str = Query(..., description="Search query text", min_length=1, max_length=1000),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results to return"),
):
    """
    Perform semantic search using GET parameters.
    
    This is a convenience endpoint for simple searches.
    """
    return await semantic_search(SearchRequest(query=q, top_k=top_k))

