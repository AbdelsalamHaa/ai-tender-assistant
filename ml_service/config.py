"""
Configuration settings for the ML service.
Uses pydantic-settings for environment variable management.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Enest ML Service"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://enest:enest_password@localhost:5432/enest_db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI
    openai_api_key: str = ""
    
    # LlamaIndex Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # File Upload
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = [".pdf"]
    
    # Vector Store
    vector_table_name: str = "document_chunks"
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    hnsw_ef_search: int = 40
    
    @property
    def async_database_url(self) -> str:
        """Convert sync URL to async URL for asyncpg."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def sync_database_url(self) -> str:
        """Ensure sync URL for SQLAlchemy sync operations."""
        url = self.database_url
        if "+asyncpg" in url:
            url = url.replace("postgresql+asyncpg://", "postgresql://")
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

