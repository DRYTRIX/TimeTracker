"""Dead-letter queue for integration sync failures."""

from datetime import datetime

from app import db


class IntegrationSyncError(db.Model):
    __tablename__ = "integration_sync_errors"

    id = db.Column(db.Integer, primary_key=True)
    connector = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=True, index=True)
    error_message = db.Column(db.Text, nullable=False)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    resolved = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_retry_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "connector": self.connector,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
        }

    @classmethod
    def record(cls, connector: str, entity_type: str, entity_id, error_message: str):
        row = cls(
            connector=connector,
            entity_type=entity_type,
            entity_id=int(entity_id) if entity_id is not None else None,
            error_message=(error_message or "")[:4000],
        )
        db.session.add(row)
        return row
