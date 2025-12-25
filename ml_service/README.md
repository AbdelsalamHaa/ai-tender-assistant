# Enest ML Service

A FastAPI-based ML/AI service for PDF ingestion and document processing using LlamaIndex.

## Features

- **PDF Ingestion Pipeline**: Upload PDFs for automatic processing
- **Structured Data Extraction**: Extract title, author, summary, key topics using LLM
- **Document Chunking**: Split documents into semantic chunks
- **Vector Embeddings**: Generate and store embeddings using OpenAI
- **PostgreSQL + pgvector**: Store vectors for semantic search
- **Async Processing**: Background task processing with Celery + Redis

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│   Celery    │────▶│  LlamaIndex │
│   (API)     │     │  (Worker)   │     │  (Pipeline) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ PostgreSQL  │     │    Redis    │     │   OpenAI    │
│ + pgvector  │     │  (Broker)   │     │   (LLM)     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key

### 1. Configure Environment

```bash
# Copy environment template
cp env.template .env

# Edit .env and add your OpenAI API key
nano .env
```

### 2. Start Services with Docker

```bash
# From the enest-agent root directory
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- ML Service API (port 8000)
- Celery Worker

### 3. Access the API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest` | Upload PDF for processing |
| `GET` | `/api/v1/jobs/{id}` | Get job status and details |
| `GET` | `/api/v1/jobs/{id}/status` | Get simplified status (for polling) |
| `GET` | `/api/v1/jobs/{id}/document` | Get parsed document content |
| `GET` | `/api/v1/jobs/{id}/extracted` | Get extracted structured data |
| `GET` | `/api/v1/jobs` | List recent jobs |
| `GET` | `/api/v1/health` | Health check |

## Development

### Local Setup (without Docker)

```bash
# Install dependencies
pip install uv
uv pip install -e .

# Start PostgreSQL and Redis (or use Docker for just these)
docker-compose up -d postgres redis

# Run the API server
uvicorn ml_service.main:app --reload --port 8000

# In another terminal, run Celery worker
celery -A ml_service.tasks.celery_app worker --loglevel=info
```

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

## Configuration

Environment variables (see `env.template`):

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://enest:enest_password@localhost:5432/enest_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |
| `LLM_MODEL` | OpenAI LLM model | `gpt-4o-mini` |
| `CHUNK_SIZE` | Document chunk size | `512` |
| `CHUNK_OVERLAP` | Chunk overlap | `50` |

## Project Structure

```
ml_service/
├── api/                    # FastAPI routes
│   └── routes/
│       ├── health.py       # Health check endpoints
│       ├── ingest.py       # PDF upload endpoint
│       └── jobs.py         # Job status endpoints
├── core/                   # Business logic
│   └── ingestion/
│       ├── pipeline.py     # LlamaIndex ingestion pipeline
│       └── extractors.py   # Structured data extraction
├── db/                     # Database layer
│   ├── models.py           # SQLAlchemy models
│   ├── session.py          # Database connections
│   └── repositories/       # Data access layer
├── schemas/                # Pydantic schemas
├── tasks/                  # Celery tasks
│   ├── celery_app.py       # Celery configuration
│   └── ingestion_task.py   # PDF processing task
├── tests/                  # Test suite
├── config.py               # Settings management
└── main.py                 # FastAPI app entry
```

## License

MIT

