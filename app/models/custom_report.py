"""
Custom Report Builder models
"""

from datetime import datetime
from app import db


class CustomReportConfig(db.Model):
    """Custom report configuration with drag-and-drop builder settings"""

    __tablename__ = "custom_report_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Report type
    report_type = db.Column(db.String(50), nullable=False)  # 'time', 'project', 'invoice', 'expense', 'combined'

    # Builder configuration (JSON)
    builder_config = db.Column(db.JSON, nullable=False)  # Columns, filters, groupings, charts

    # Layout
    layout_config = db.Column(db.JSON, nullable=True)  # Drag-and-drop layout positions

    # Sharing
    scope = db.Column(db.String(20), default="private", nullable=False)  # 'private', 'team', 'public'
    shared_with = db.Column(db.JSON, nullable=True)  # List of user IDs

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = db.relationship("User", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<CustomReportConfig {self.name} ({self.report_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "report_type": self.report_type,
            "builder_config": self.builder_config,
            "layout_config": self.layout_config,
            "scope": self.scope,
            "shared_with": self.shared_with or [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
