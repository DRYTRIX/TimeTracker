from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone
import os


def local_now():
    """Get current time in local timezone as naive datetime (for database storage)"""
    return now_in_app_timezone().replace(tzinfo=None)


class QuoteImage(db.Model):
    """Model for decorative images in quotes"""

    __tablename__ = "quote_images"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=True)

    # Position and display properties (in millimeters for PDF)
    position_x = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # X position in mm
    position_y = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Y position in mm
    width = db.Column(db.Numeric(10, 2), nullable=True)  # Width in mm (null = auto)
    height = db.Column(db.Numeric(10, 2), nullable=True)  # Height in mm (null = auto)
    opacity = db.Column(db.Numeric(3, 2), nullable=False, default=1.0)  # Opacity 0.0-1.0
    z_index = db.Column(db.Integer, nullable=False, default=0)  # Layer order

    # Upload information
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=local_now, nullable=False)

    # Relationships
    quote = db.relationship("Quote", backref="decorative_images")
    uploader = db.relationship("User", backref="uploaded_quote_images")

    def __init__(self, quote_id, filename, original_filename, file_path, file_size, uploaded_by, **kwargs):
        self.quote_id = quote_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.uploaded_by = uploaded_by
        self.mime_type = kwargs.get("mime_type")
        self.position_x = kwargs.get("position_x", 0)
        self.position_y = kwargs.get("position_y", 0)
        self.width = kwargs.get("width")
        self.height = kwargs.get("height")
        self.opacity = kwargs.get("opacity", 1.0)
        self.z_index = kwargs.get("z_index", 0)

    def __repr__(self):
        return f"<QuoteImage {self.original_filename} for Quote {self.quote_id}>"

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

    def to_dict(self):
        """Convert image to dictionary for API responses"""
        return {
            "id": self.id,
            "quote_id": self.quote_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_size_display": self.file_size_display,
            "mime_type": self.mime_type,
            "position_x": float(self.position_x) if self.position_x else 0,
            "position_y": float(self.position_y) if self.position_y else 0,
            "width": float(self.width) if self.width else None,
            "height": float(self.height) if self.height else None,
            "opacity": float(self.opacity) if self.opacity else 1.0,
            "z_index": self.z_index,
            "uploaded_by": self.uploaded_by,
            "uploader": self.uploader.username if self.uploader else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "file_extension": self.file_extension,
            "is_image": self.is_image,
        }

    @classmethod
    def get_quote_images(cls, quote_id):
        """Get all decorative images for a quote, ordered by z_index"""
        return cls.query.filter_by(quote_id=quote_id).order_by(cls.z_index.asc(), cls.uploaded_at.asc()).all()
