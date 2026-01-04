from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import os


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class CommentAttachment(db.Model):
    """Model for comment file attachments"""

    __tablename__ = "comment_attachments"

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=True)

    # Upload information
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=local_now, nullable=False)

    # Relationships
    comment = db.relationship("Comment", backref=db.backref("attachments", lazy="dynamic", cascade="all, delete-orphan"))
    uploader = db.relationship("User", backref="uploaded_comment_attachments")

    def __init__(self, comment_id, filename, original_filename, file_path, file_size, uploaded_by, **kwargs):
        self.comment_id = comment_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.uploaded_by = uploaded_by
        self.mime_type = kwargs.get("mime_type")

    def __repr__(self):
        return f"<CommentAttachment {self.original_filename} for Comment {self.comment_id}>"

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
        return self.file_extension in [".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx"]

    @property
    def download_url(self):
        """Get URL for downloading the attachment"""
        from flask import url_for

        return url_for("comments.download_attachment", attachment_id=self.id)

    def to_dict(self):
        """Convert attachment to dictionary for API responses"""
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_size_display": self.file_size_display,
            "mime_type": self.mime_type,
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
    def get_comment_attachments(cls, comment_id):
        """Get all attachments for a comment"""
        return cls.query.filter_by(comment_id=comment_id).order_by(cls.uploaded_at.asc()).all()
