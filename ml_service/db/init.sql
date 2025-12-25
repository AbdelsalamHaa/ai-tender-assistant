-- Initialize PostgreSQL database with pgvector extension
-- This script runs on first container startup

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ingestion Jobs Table
-- Using VARCHAR for status instead of enum for SQLAlchemy compatibility
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    current_step VARCHAR(50),
    error_message TEXT,
    total_pages INTEGER,
    total_chunks INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON ingestion_jobs(created_at DESC);

-- Documents Table (raw parsed content)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_count INTEGER,
    metadata_ JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_job_id ON documents(job_id);

-- Extracted Data Table (structured LLM extraction with tender requirements)
CREATE TABLE IF NOT EXISTS extracted_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    title VARCHAR(500),
    author VARCHAR(255),
    summary TEXT,
    document_type VARCHAR(100),
    key_topics JSONB,
    entities JSONB,
    language VARCHAR(10) DEFAULT 'en',
    -- Tender-specific fields
    tender_reference VARCHAR(255),
    submission_deadline VARCHAR(255),
    estimated_value VARCHAR(255),
    requirements JSONB,  -- Array of requirement objects
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_job_id ON extracted_data(job_id);
-- Index for searching within requirements JSON
CREATE INDEX IF NOT EXISTS idx_extracted_requirements ON extracted_data USING gin(requirements);

-- Document Chunks Table (for PGVectorStore - LlamaIndex will manage this)
-- This creates the table structure that LlamaIndex PGVectorStore expects
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR PRIMARY KEY,
    text TEXT,
    metadata_ JSONB,
    node_id VARCHAR,
    embedding VECTOR(1536)
);

-- HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for ingestion_jobs updated_at
DROP TRIGGER IF EXISTS update_ingestion_jobs_updated_at ON ingestion_jobs;
CREATE TRIGGER update_ingestion_jobs_updated_at
    BEFORE UPDATE ON ingestion_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO enest;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO enest;

