"""Per-user dismissals for smart in-app notifications (by local calendar date and kind)."""

from datetime import datetime

from app import db


class UserSmartNotificationDismissal(db.Model):
    __tablename__ = "user_smart_notification_dismissals"
    __table_args__ = (db.UniqueConstraint("user_id", "local_date", "kind", name="uq_user_smart_notif_dismissal"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    local_date = db.Column(db.String(64), nullable=False)  # YYYY-MM-DD in user's timezone, or bucket key
    kind = db.Column(db.String(32), nullable=False)
    dismissed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
