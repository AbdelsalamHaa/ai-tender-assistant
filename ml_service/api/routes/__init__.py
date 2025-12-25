"""
API route modules.
"""

from fastapi import APIRouter

from ml_service.api.routes.health import router as health_router
from ml_service.api.routes.ingest import router as ingest_router
from ml_service.api.routes.jobs import router as jobs_router
from ml_service.api.routes.documents import router as documents_router
from ml_service.api.routes.search import router as search_router

# Main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])

