from datetime import datetime

from app import db


class TenantMember(db.Model):
    """Links a User to a Tenant with a tenant-scoped role."""

    __tablename__ = "tenant_members"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_members_tenant_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    role = db.Column(db.String(20), default="member", nullable=False)  # owner | admin | member
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tenant = db.relationship("Tenant", backref=db.backref("members", lazy="dynamic", cascade="all, delete-orphan"))
    user = db.relationship("User", backref=db.backref("tenant_memberships", lazy="dynamic", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<TenantMember tenant_id={self.tenant_id} user_id={self.user_id} role={self.role}>"

