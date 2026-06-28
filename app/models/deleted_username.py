from datetime import datetime

from app import db


class DeletedUsername(db.Model):
    """Reserved usernames for deleted users to prevent self-registration recreation."""

    __tablename__ = "deleted_usernames"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    deleted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    deleted_by = db.relationship("User", foreign_keys=[deleted_by_user_id])
