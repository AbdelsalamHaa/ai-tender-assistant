"""
Pytest configuration and fixtures for ML Service tests.
"""

import os
import pytest
from typing import Generator

# Set test environment variables before imports
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["UPLOAD_DIR"] = "/tmp/test_uploads"


@pytest.fixture(scope="session")
def test_upload_dir() -> Generator[str, None, None]:
    """Create and cleanup test upload directory."""
    import tempfile
    import shutil
    
    test_dir = tempfile.mkdtemp(prefix="ml_service_test_")
    os.environ["UPLOAD_DIR"] = test_dir
    
    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Return minimal PDF content for testing."""
    # Minimal valid PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF
"""

