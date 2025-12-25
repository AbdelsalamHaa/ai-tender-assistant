"""
Database session management for sync and async operations.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from ml_service.config import get_settings

settings = get_settings()

# Sync engine (for Celery workers and migrations)
engine = create_engine(
    settings.sync_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Async engine (for FastAPI endpoints)
async_engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_sync_db() -> Generator[Session, None, None]:
    """Get sync database session (for Celery tasks)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session (for FastAPI endpoints)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

