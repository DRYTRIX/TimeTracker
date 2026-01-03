from datetime import datetime, timedelta
import secrets

from app import db


class TenantInvite(db.Model):
    """Invitation for a user to join a tenant."""

    __tablename__ = "tenant_invites"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    email = db.Column(db.String(200), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="member")  # admin | member

    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    accepted_at = db.Column(db.DateTime, nullable=True)
    accepted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    revoked_at = db.Column(db.DateTime, nullable=True)
    revoked_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    tenant = db.relationship("Tenant", backref=db.backref("invites", lazy="dynamic", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<TenantInvite tenant_id={self.tenant_id} email={self.email} role={self.role}>"

    @property
    def is_expired(self) -> bool:
        try:
            return self.expires_at is not None and self.expires_at < datetime.utcnow()
        except Exception:
            return True

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_active(self) -> bool:
        return (not self.is_accepted) and (not self.is_revoked) and (not self.is_expired)

    @classmethod
    def new_invite(cls, tenant_id: int, email: str, role: str, created_by_user_id: int | None = None):
        email_norm = (email or "").strip().lower()
        role_norm = (role or "member").strip().lower()
        if role_norm not in ("admin", "member"):
            role_norm = "member"
        token = secrets.token_urlsafe(32)
        return cls(
            tenant_id=tenant_id,
            email=email_norm,
            role=role_norm,
            token=token,
            created_by_user_id=created_by_user_id,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

