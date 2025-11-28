from datetime import datetime
from app import db


class SavedFilter(db.Model):
    """User-defined saved filters for reuse across views.

    Stores JSON payload with supported keys like project_id, user_id, date ranges,
    tags, billable, status, etc.
    """

    __tablename__ = "saved_filters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    scope = db.Column(db.String(50), nullable=False, default="global")  # e.g., 'time', 'projects', 'tasks', 'reports'
    payload = db.Column(db.JSON, nullable=False, default={})

    is_shared = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "name", "scope", name="ux_saved_filter_user_name_scope"),)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "scope": self.scope,
            "payload": self.payload,
            "is_shared": self.is_shared,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
