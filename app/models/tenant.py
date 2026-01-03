from datetime import datetime

from app import db


class Tenant(db.Model):
    """A tenant/workspace (aka organization) for SaaS multi-tenancy."""

    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # active | suspended | deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Optional metadata that becomes useful quickly in SaaS
    created_by_user_id = db.Column(db.Integer, nullable=True, index=True)
    primary_owner_user_id = db.Column(db.Integer, nullable=True, index=True)
    billing_email = db.Column(db.String(200), nullable=True)
    default_timezone = db.Column(db.String(50), nullable=True)
    default_currency = db.Column(db.String(3), nullable=True)

    def __repr__(self):
        return f"<Tenant {self.slug}>"

    @staticmethod
    def normalize_slug(slug: str) -> str:
        return (slug or "").strip().lower()

