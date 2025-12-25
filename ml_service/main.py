"""
FastAPI application entry point for the ML Service.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ml_service.api.routes import api_router
from ml_service.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    
    # Create upload directory
    from pathlib import Path
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## Enest ML Service

A FastAPI-based service for PDF ingestion and AI-powered document processing.

### Features
- **PDF Ingestion**: Upload PDF files for processing
- **Structured Extraction**: Extract title, author, summary, key topics using LLM
- **Vector Storage**: Chunk and embed documents for semantic search
- **Background Processing**: Async task processing with Celery

### API Overview
- `POST /api/v1/ingest` - Upload a PDF for processing
- `GET /api/v1/jobs/{job_id}` - Get job status and details
- `GET /api/v1/documents` - List all ingested documents
- `GET /api/v1/documents/{job_id}` - Get document details with extracted data
- `POST /api/v1/search` - **Semantic search** across all documents
- `GET /api/v1/search?q=...` - Semantic search via query params
""",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

