"""
Client Portal Dashboard Preference model.
Stores per-client (and optionally per-user) widget visibility and order for the client portal dashboard.
"""

from datetime import datetime

from app import db


# Widget keys for the client portal dashboard (default layout order)
DEFAULT_WIDGET_ORDER = [
    "stats",
    "pending_actions",
    "projects",
    "invoices",
    "time_entries",
]
VALID_WIDGET_IDS = frozenset(DEFAULT_WIDGET_ORDER)


class ClientPortalDashboardPreference(db.Model):
    """Per-client or per-user dashboard widget preferences for the client portal."""

    __tablename__ = "client_portal_dashboard_preferences"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    widget_ids = db.Column(db.JSON, nullable=False)  # list of widget keys, e.g. ["stats", "projects"]
    widget_order = db.Column(db.JSON, nullable=True)  # display order; if null, use widget_ids order
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("client_id", "user_id", name="uq_client_portal_dashboard_pref_client_user"),
    )

    client = db.relationship("Client", backref=db.backref("dashboard_preferences", lazy="dynamic", cascade="all, delete-orphan"))
    user = db.relationship("User", backref=db.backref("client_portal_dashboard_preference", uselist=False))

    def __repr__(self):
        return f"<ClientPortalDashboardPreference client_id={self.client_id} user_id={self.user_id}>"

    def to_dict(self):
        order = self.widget_order if self.widget_order is not None else self.widget_ids
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "widget_ids": self.widget_ids,
            "widget_order": order,
        }
