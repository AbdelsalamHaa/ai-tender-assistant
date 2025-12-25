"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ml_service.db.session import get_db
from ml_service.config import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    status: str
    service: str
    version: str
    database: str
    redis: str


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns service status without checking dependencies.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version="0.1.0",
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed health check that verifies database connectivity.
    """
    db_status = "healthy"
    redis_status = "unknown"
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis (via Celery)
    try:
        from ml_service.tasks.celery_app import celery_app
        celery_app.control.ping(timeout=1)
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall_status = "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        service=settings.app_name,
        version="0.1.0",
        database=db_status,
        redis=redis_status,
    )

