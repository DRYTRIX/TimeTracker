"""
File upload utilities with validation and security.
"""

from typing import Optional, Tuple
from werkzeug.utils import secure_filename
from flask import current_app
import os
from pathlib import Path
from app.constants import MAX_FILE_SIZE, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_DOCUMENT_EXTENSIONS


def validate_file_upload(
    file, allowed_extensions: Optional[set] = None, max_size: int = MAX_FILE_SIZE
) -> Tuple[bool, Optional[str]]:
    """
    Validate a file upload.

    Args:
        file: File object from request
        allowed_extensions: Set of allowed extensions (defaults to all)
        max_size: Maximum file size in bytes

    Returns:
        tuple of (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "No file provided"

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > max_size:
        return False, f"File size exceeds maximum of {max_size / (1024*1024):.1f}MB"

    # Check extension
    if allowed_extensions:
        filename = secure_filename(file.filename)
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"

    return True, None


def save_uploaded_file(
    file, upload_folder: str, subfolder: Optional[str] = None, prefix: Optional[str] = None
) -> Optional[str]:
    """
    Save an uploaded file securely.

    Args:
        file: File object from request
        upload_folder: Base upload folder
        subfolder: Optional subfolder (e.g., 'receipts', 'avatars')
        prefix: Optional filename prefix

    Returns:
        Saved file path or None on error
    """
    try:
        # Secure filename
        filename = secure_filename(file.filename)
        if not filename:
            return None

        # Add prefix if provided
        if prefix:
            name, ext = os.path.splitext(filename)
            filename = f"{prefix}_{name}{ext}"

        # Create directory structure
        if subfolder:
            upload_path = os.path.join(upload_folder, subfolder)
        else:
            upload_path = upload_folder

        os.makedirs(upload_path, exist_ok=True)

        # Ensure unique filename
        filepath = os.path.join(upload_path, filename)
        counter = 1
        while os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            filepath = os.path.join(upload_path, f"{name}_{counter}{ext}")
            counter += 1

        # Save file
        file.save(filepath)

        # Return relative path
        if subfolder:
            return os.path.join(subfolder, os.path.basename(filepath))
        return os.path.basename(filepath)

    except Exception as e:
        current_app.logger.error(f"Error saving uploaded file: {e}")
        return None


def delete_uploaded_file(filepath: str, upload_folder: str) -> bool:
    """
    Delete an uploaded file.

    Args:
        filepath: Relative file path
        upload_folder: Base upload folder

    Returns:
        True if deleted, False otherwise
    """
    try:
        full_path = os.path.join(upload_folder, filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Error deleting file {filepath}: {e}")
        return False


def get_file_info(filepath: str, upload_folder: str) -> Optional[dict]:
    """
    Get information about an uploaded file.

    Args:
        filepath: Relative file path
        upload_folder: Base upload folder

    Returns:
        dict with file info or None
    """
    try:
        full_path = os.path.join(upload_folder, filepath)
        if not os.path.exists(full_path):
            return None

        stat = os.stat(full_path)
        return {
            "path": filepath,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "extension": Path(filepath).suffix.lower(),
        }
    except Exception as e:
        current_app.logger.error(f"Error getting file info: {e}")
        return None
