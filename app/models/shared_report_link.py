import json
import uuid
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class SharedReportLink(db.Model):
    """Public shareable link for a saved report configuration snapshot."""

    __tablename__ = "shared_report_links"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    saved_view_id = db.Column(db.Integer, db.ForeignKey("saved_report_views.id"), nullable=False, index=True)
    report_name = db.Column(db.String(120), nullable=True)
    report_config_snapshot = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    saved_view = db.relationship("SavedReportView", backref=db.backref("shared_links", lazy="dynamic"))
    creator = db.relationship("User", backref=db.backref("shared_report_links", lazy="dynamic"))

    def __init__(self, saved_view_id, created_by_id, report_config_snapshot, **kwargs):
        self.token = kwargs.get("token") or str(uuid.uuid4())
        self.saved_view_id = saved_view_id
        self.created_by_id = created_by_id
        if isinstance(report_config_snapshot, dict):
            self.report_config_snapshot = json.dumps(report_config_snapshot)
        else:
            self.report_config_snapshot = report_config_snapshot
        self.report_name = kwargs.get("report_name")
        self.expires_at = kwargs.get("expires_at")
        self.is_active = kwargs.get("is_active", True)
        password = kwargs.get("password")
        if password:
            self.set_password(password)

    def __repr__(self):
        return f"<SharedReportLink {self.token[:8]}... view={self.saved_view_id}>"

    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None

    def check_password(self, password):
        if not self.password_hash:
            return True
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def requires_password(self):
        return bool(self.password_hash)

    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def is_accessible(self):
        return self.is_active and not self.is_expired()

    def get_config(self):
        try:
            return json.loads(self.report_config_snapshot)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

    def record_access(self):
        self.view_count = (self.view_count or 0) + 1
        self.last_accessed_at = datetime.utcnow()

    def to_dict(self, include_url=False):
        data = {
            "token": self.token,
            "saved_view_id": self.saved_view_id,
            "report_name": self.report_name,
            "created_by_id": self.created_by_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "requires_password": self.requires_password,
            "view_count": self.view_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_url:
            from flask import url_for

            data["url"] = url_for("custom_reports.view_shared_report", token=self.token, _external=True)
        return data
