"""Receipts of expenses and bills of project costs, uploaded from an invoice.

Files go where the expense form puts receipts (``<UPLOAD_FOLDER>/receipts``), stored as
``uploads/receipts/<file>``, with the same allowed types.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional, Tuple

from werkzeug.utils import secure_filename


class ReceiptUploadError(ValueError):
    """The file cannot be stored as a receipt.

    ``problem``: ``no_file``, ``file_type`` (not PNG, JPG, GIF or PDF), ``file_name`` or ``not_saved``,
    so a page can say it in its own words.
    """

    code = "receipt_not_saved"

    def __init__(self, problem: str):
        self.problem = problem
        super().__init__(problem)


def save_receipt(file, prefix: str = "") -> str:
    """Store an uploaded file as a receipt and return its stored path ``uploads/receipts/<file>``."""
    from app.routes.expenses import UPLOAD_FOLDER, allowed_file, get_receipt_upload_folder

    if file is None or not getattr(file, "filename", ""):
        raise ReceiptUploadError("no_file")
    if not allowed_file(file.filename):
        raise ReceiptUploadError("file_type")
    name = secure_filename(file.filename)
    if not name:
        raise ReceiptUploadError("file_name")
    name = f"{prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"
    try:
        folder = get_receipt_upload_folder()
        file.save(os.path.join(folder, name))
    except OSError as exc:
        raise ReceiptUploadError("not_saved") from exc
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


def invoice_files(invoice) -> List[Tuple[str, Optional[str]]]:
    """``[(label, stored path)]`` of the files the invoice PDF is followed by, in print order.

    Receipts of its expenses (with ``attach_receipts``), then the supplier bills of its project costs
    (with ``attach_bills``), each by date. A path is None when the expense or cost has no file.
    """
    from app.models import Expense, ProjectCost

    files: List[Tuple[str, Optional[str]]] = []
    if getattr(invoice, "attach_receipts", False):
        for expense in invoice.expenses.order_by(Expense.expense_date.asc(), Expense.id.asc()).all():
            files.append((expense.title, expense.receipt_path))
    if getattr(invoice, "attach_bills", False):
        costs = (
            ProjectCost.query.filter(ProjectCost.invoice_id == invoice.id)
            .order_by(ProjectCost.cost_date.asc(), ProjectCost.id.asc())
            .all()
        )
        for cost in costs:
            files.append((cost.description, cost.receipt_path))
    return files


# An image larger than this is not opened: a small file can unpack into a huge picture
MAX_RECEIPT_PIXELS = 50_000_000


class AttachedFiles:
    """What happened to the files the invoice PDF is set to attach."""

    def __init__(self):
        self.missing: List[str] = []  # labels of expenses or costs without a file on disk
        self.unreadable: List[str] = []  # labels of files that are there but could not be read


def _file_as_pdf(path: str):
    """The file as an open pikepdf document: a PDF as it is, an image on its own page."""
    import io

    import pikepdf
    from PIL import Image

    if path.lower().endswith(".pdf"):
        return pikepdf.open(path)
    buffer = io.BytesIO()
    with Image.open(path) as image:
        width, height = image.size
        if width * height > MAX_RECEIPT_PIXELS:
            raise ValueError("image too large")
        image.convert("RGB").save(buffer, format="PDF", resolution=150.0)
    return pikepdf.open(io.BytesIO(buffer.getvalue()))


def append_invoice_files(pdf_bytes: bytes, invoice) -> Tuple[bytes, AttachedFiles]:
    """The invoice PDF followed by its receipts and bills: a PDF's pages as they are, an image on a page.

    Used for every PDF of the invoice: download and preview, the email to the client, the client
    portal and the API. Peppol sends XML and attaches nothing. Returns the new PDF and what could not
    be added: files missing, and files that could not be read (not a PDF or an image, broken, or an
    image of more than ``MAX_RECEIPT_PIXELS`` pixels).
    """
    import io
    import logging

    import pikepdf

    report = AttachedFiles()
    files = invoice_files(invoice)
    if not files:
        return pdf_bytes, report

    out = pikepdf.open(io.BytesIO(pdf_bytes))
    sources = []
    try:
        for label, stored in files:
            location = receipt_location(stored)
            if location is None:
                report.missing.append(label)
                continue
            try:
                source = _file_as_pdf(os.path.join(*location))
            except Exception:
                logging.getLogger(__name__).info("Could not read %s to attach it", location[1], exc_info=True)
                report.unreadable.append(label)
                continue
            sources.append(source)
            out.pages.extend(source.pages)
        result = io.BytesIO()
        out.save(result)
        return result.getvalue(), report
    finally:
        for source in sources:
            source.close()
        out.close()


def attach_invoice_files(pdf_bytes: bytes, invoice, where: str) -> Tuple[bytes, Optional[AttachedFiles]]:
    """``append_invoice_files`` that never fails: on an error the PDF goes as it is and the error is logged.

    Returns the PDF and the report (None when attaching failed as a whole).
    """
    import logging

    try:
        return append_invoice_files(pdf_bytes, invoice)
    except Exception:
        logging.getLogger(__name__).warning(
            "Could not attach receipts and bills to invoice %s (%s)", getattr(invoice, "id", None), where, exc_info=True
        )
        return pdf_bytes, None
