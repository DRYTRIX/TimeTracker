"""
External event link table for integration-driven sync.

Used for idempotency when importing calendar events (e.g., CalDAV -> TimeEntry).
"""

from datetime import datetime

from app import db


class IntegrationExternalEventLink(db.Model):
    __tablename__ = "integration_external_event_links"
    __table_args__ = (
        db.UniqueConstraint("integration_id", "external_uid", name="uq_integration_external_uid"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)

    integration_id = db.Column(
        db.Integer, db.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id", ondelete="CASCADE"), nullable=False, index=True)

    # External identifiers
    external_uid = db.Column(db.String(255), nullable=False, index=True)
    external_href = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    integration = db.relationship("Integration", backref=db.backref("external_event_links", cascade="all, delete-orphan"))
    time_entry = db.relationship("TimeEntry", backref=db.backref("external_event_links", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<IntegrationExternalEventLink integration_id={self.integration_id} uid={self.external_uid}>"


