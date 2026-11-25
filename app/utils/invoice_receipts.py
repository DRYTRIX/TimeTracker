"""Receipts of expenses and bills of project costs, uploaded from an invoice.

Files go where the expense form puts receipts (``<UPLOAD_FOLDER>/receipts``), stored as
``uploads/receipts/<file>``, with the same allowed types.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

from werkzeug.utils import secure_filename


class ReceiptUploadError(ValueError):
    """The file cannot be stored as a receipt (no file, a type that is not allowed, a disk error)."""


def save_receipt(file, prefix: str = "") -> str:
    """Store an uploaded file as a receipt and return its stored path ``uploads/receipts/<file>``."""
    from app.routes.expenses import UPLOAD_FOLDER, allowed_file, get_receipt_upload_folder

    if file is None or not getattr(file, "filename", ""):
        raise ReceiptUploadError("Choose a file")
    if not allowed_file(file.filename):
        raise ReceiptUploadError("Receipts can be PNG, JPG, GIF or PDF files")
    name = secure_filename(file.filename)
    if not name:
        raise ReceiptUploadError("Invalid file name")
    name = f"{prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"
    try:
        folder = get_receipt_upload_folder()
        file.save(os.path.join(folder, name))
    except OSError as exc:
        raise ReceiptUploadError("Could not save the file") from exc
    return os.path.join(UPLOAD_FOLDER, name).replace("\\", "/")


def receipt_location(stored_path: Optional[str]) -> Optional[Tuple[str, str]]:
    """``(folder, file name)`` of a stored receipt that exists on disk, else None."""
    from app.routes.expenses import get_receipt_upload_folder
    from app.utils.paths import safe_path_under_or_none

    if not stored_path:
        return None
    name = secure_filename(os.path.basename(stored_path))
    if not name:
        return None
    try:
        folder = get_receipt_upload_folder()
    except OSError:
        return None
    path = safe_path_under_or_none(folder, name)
    if path is None or not os.path.isfile(path):
        return None
    return folder, name
