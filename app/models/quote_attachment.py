from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import os


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class QuoteAttachment(db.Model):
    """Model for quote file attachments"""

    __tablename__ = "quote_attachments"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=True)

    # Metadata
    description = db.Column(db.Text, nullable=True)
    is_visible_to_client = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Whether attachment is visible in client portal

    # Upload information
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=local_now, nullable=False)

    # Relationships
    quote = db.relationship("Quote", backref="attachments")
    uploader = db.relationship("User", backref="uploaded_quote_attachments")

    def __init__(self, quote_id, filename, original_filename, file_path, file_size, uploaded_by, **kwargs):
        self.quote_id = quote_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.uploaded_by = uploaded_by
        self.mime_type = kwargs.get("mime_type")
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.is_visible_to_client = kwargs.get("is_visible_to_client", False)

    def __repr__(self):
        return f"<QuoteAttachment {self.original_filename} for Quote {self.quote_id}>"

    @property
    def file_size_mb(self):
        """Get file size in megabytes"""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def file_size_kb(self):
        """Get file size in kilobytes"""
        return round(self.file_size / 1024, 2)

    @property
    def file_size_display(self):
        """Get human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size_kb} KB"
        else:
            return f"{self.file_size_mb} MB"

    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()

    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_extension in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]

    @property
    def is_pdf(self):
        """Check if file is a PDF"""
        return self.file_extension == ".pdf"

    @property
    def is_document(self):
        """Check if file is a document"""
        return self.file_extension in [".doc", ".docx", ".txt", ".rtf"]

    @property
    def download_url(self):
        """Get URL for downloading the attachment"""
        from flask import url_for

        return url_for("quotes.download_attachment", attachment_id=self.id)

    def to_dict(self):
        """Convert attachment to dictionary for API responses"""
        return {
            "id": self.id,
            "quote_id": self.quote_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_size_display": self.file_size_display,
            "mime_type": self.mime_type,
            "description": self.description,
            "is_visible_to_client": self.is_visible_to_client,
            "uploaded_by": self.uploaded_by,
            "uploader": self.uploader.username if self.uploader else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "file_extension": self.file_extension,
            "is_image": self.is_image,
            "is_pdf": self.is_pdf,
            "is_document": self.is_document,
            "download_url": self.download_url,
        }

    @classmethod
    def get_quote_attachments(cls, quote_id, include_client_visible=True):
        """Get all attachments for a quote"""
        query = cls.query.filter_by(quote_id=quote_id)

        if not include_client_visible:
            query = query.filter_by(is_visible_to_client=False)

        return query.order_by(cls.uploaded_at.desc()).all()
