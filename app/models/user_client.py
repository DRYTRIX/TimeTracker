"""User-Client association for subcontractor scope (restrict user to assigned clients)."""

from datetime import datetime
from app import db


class UserClient(db.Model):
    """Association: user is allowed to see this client (subcontractor scope)."""

    __tablename__ = "user_clients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "client_id", name="uq_user_client"),)

    def __repr__(self):
        return f"<UserClient user_id={self.user_id} client_id={self.client_id}>"
