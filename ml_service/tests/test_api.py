"""
API endpoint tests for ML Service.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# Mock dependencies before importing the app
@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch("ml_service.api.routes.ingest.get_db") as mock:
        mock_session = MagicMock()
        mock.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_celery():
    """Mock Celery task."""
    with patch("ml_service.api.routes.ingest.process_pdf_ingestion") as mock:
        mock.delay = MagicMock()
        yield mock


@pytest.fixture
def client():
    """Create test client."""
    from ml_service.main import app
    return TestClient(app)


def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "docs" in data


def test_ingest_no_file(client):
    """Test ingestion endpoint without file returns error."""
    response = client.post("/api/v1/ingest")
    assert response.status_code == 422  # Unprocessable Entity


def test_ingest_invalid_file_type(client, test_upload_dir):
    """Test ingestion endpoint rejects non-PDF files."""
    response = client.post(
        "/api/v1/ingest",
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_job_not_found(client):
    """Test getting non-existent job returns 404."""
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

