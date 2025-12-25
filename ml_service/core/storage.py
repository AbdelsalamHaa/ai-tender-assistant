"""
File storage utilities for handling uploaded files.
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from ml_service.config import get_settings

settings = get_settings()


def get_upload_directory() -> Path:
    """Get the upload directory path, creating it if necessary."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_uploaded_file(file: BinaryIO, original_filename: str) -> str:
    """
    Save an uploaded file to the upload directory.
    
    Args:
        file: File-like object to save
        original_filename: Original filename for extension extraction
        
    Returns:
        Path to the saved file
    """
    upload_dir = get_upload_directory()
    
    # Generate unique filename
    file_ext = Path(original_filename).suffix.lower()
    unique_filename = f"{uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as dest:
        shutil.copyfileobj(file, dest)
    
    return str(file_path)


def delete_file(file_path: str) -> bool:
    """
    Delete a file from storage.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception:
        return False


def validate_file_extension(filename: str) -> bool:
    """
    Validate that a file has an allowed extension.
    
    Args:
        filename: Filename to validate
        
    Returns:
        True if extension is allowed
    """
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_extensions


def validate_file_size(file: BinaryIO) -> bool:
    """
    Validate that a file doesn't exceed the maximum size.
    
    Args:
        file: File-like object to validate
        
    Returns:
        True if file size is acceptable
    """
    # Get file size by seeking to end
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size = settings.max_file_size_mb * 1024 * 1024
    return size <= max_size

