"""
Client Time Entry Approval models
Similar to manager approval but for client-side approval
"""

from datetime import datetime
from app import db
from sqlalchemy import Enum as SQLEnum
import enum


class ClientApprovalStatus(enum.Enum):
    """Client approval status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ClientTimeApproval(db.Model):
    """Client-side time entry approval request"""

    __tablename__ = "client_time_approvals"

    id = db.Column(db.Integer, primary_key=True)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)

    # Approval workflow
    status = db.Column(SQLEnum(ClientApprovalStatus), default=ClientApprovalStatus.PENDING, nullable=False, index=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    approved_by = db.Column(db.Integer, nullable=True)  # Client contact ID (not user ID)

    # Timestamps
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)

    # Comments
    request_comment = db.Column(db.Text, nullable=True)
    approval_comment = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    time_entry = db.relationship("TimeEntry", backref=db.backref("client_approvals", lazy="dynamic"))
    project = db.relationship("Project", backref=db.backref("client_approvals", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("time_approvals", lazy="dynamic"))
    requester = db.relationship("User", foreign_keys=[requested_by])

    def __repr__(self):
        return f"<ClientTimeApproval {self.id} for entry {self.time_entry_id} - {self.status.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "time_entry_id": self.time_entry_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "status": self.status.value if isinstance(self.status, ClientApprovalStatus) else self.status,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "request_comment": self.request_comment,
            "approval_comment": self.approval_comment,
            "rejection_reason": self.rejection_reason,
        }

    def approve(self, contact_id: int, comment: str = None):
        """Approve this request"""
        self.status = ClientApprovalStatus.APPROVED
        self.approved_by = contact_id
        self.approved_at = datetime.utcnow()
        self.approval_comment = comment
        db.session.commit()

    def reject(self, contact_id: int, reason: str):
        """Reject this request"""
        self.status = ClientApprovalStatus.REJECTED
        self.approved_by = contact_id
        self.rejected_at = datetime.utcnow()
        self.rejection_reason = reason
        db.session.commit()

    def cancel(self):
        """Cancel this request"""
        self.status = ClientApprovalStatus.CANCELLED
        db.session.commit()


class ClientApprovalPolicy(db.Model):
    """Approval policy for client-side approvals"""

    __tablename__ = "client_approval_policies"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)

    # Approval requirements
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)
    auto_approve_after_days = db.Column(db.Integer, nullable=True)  # Auto-approve if no response

    # Conditions
    min_hours = db.Column(db.Numeric(10, 2), nullable=True)  # Require approval if >= this many hours
    billable_only = db.Column(db.Boolean, default=False, nullable=False)

    # Status
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = db.relationship("Client", backref=db.backref("approval_policies", lazy="dynamic"))
    project = db.relationship("Project", backref=db.backref("client_approval_policies", lazy="dynamic"))

    def __repr__(self):
        return f"<ClientApprovalPolicy client={self.client_id} project={self.project_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "requires_approval": self.requires_approval,
            "auto_approve_after_days": self.auto_approve_after_days,
            "min_hours": float(self.min_hours) if self.min_hours else None,
            "billable_only": self.billable_only,
            "enabled": self.enabled,
        }

    def applies_to_entry(self, time_entry) -> bool:
        """Check if this policy applies to a time entry"""
        if not self.enabled or not self.requires_approval:
            return False

        # Check project match
        if self.project_id and time_entry.project_id != self.project_id:
            return False

        # Check client match
        if time_entry.project.client_id != self.client_id:
            return False

        # Check billable requirement
        if self.billable_only and not time_entry.billable:
            return False

        # Check minimum hours
        if self.min_hours and time_entry.duration_seconds:
            hours = time_entry.duration_seconds / 3600
            if hours < float(self.min_hours):
                return False

        return True
