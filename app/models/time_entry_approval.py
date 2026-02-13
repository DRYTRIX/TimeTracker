"""
Time Entry Approval models for manager approval workflow
"""

from datetime import datetime
from app import db
from sqlalchemy import Enum as SQLEnum
import enum


class ApprovalStatus(enum.Enum):
    """Time entry approval status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TimeEntryApproval(db.Model):
    """Time entry approval request"""

    __tablename__ = "time_entry_approvals"

    id = db.Column(db.Integer, primary_key=True)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id"), nullable=False, index=True)

    # Approval workflow (use enum value for PostgreSQL: 'pending' not 'PENDING')
    status = db.Column(
        SQLEnum(ApprovalStatus, values_callable=lambda x: [e.value for e in x]),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Timestamps
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)

    # Comments
    request_comment = db.Column(db.Text, nullable=True)
    approval_comment = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Approval chain (for multi-level approvals)
    parent_approval_id = db.Column(db.Integer, db.ForeignKey("time_entry_approvals.id"), nullable=True)
    approval_level = db.Column(db.Integer, default=1, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    time_entry = db.relationship("TimeEntry", backref=db.backref("approvals", lazy="dynamic"))
    requester = db.relationship(
        "User", foreign_keys=[requested_by], backref=db.backref("approval_requests", lazy="dynamic")
    )
    approver = db.relationship(
        "User", foreign_keys=[approved_by], backref=db.backref("approvals_given", lazy="dynamic")
    )
    parent_approval = db.relationship(
        "TimeEntryApproval", remote_side=[id], backref=db.backref("child_approvals", lazy="dynamic")
    )

    def __repr__(self):
        return f"<TimeEntryApproval {self.id} for entry {self.time_entry_id} - {self.status.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "time_entry_id": self.time_entry_id,
            "status": self.status.value if isinstance(self.status, ApprovalStatus) else self.status,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "request_comment": self.request_comment,
            "approval_comment": self.approval_comment,
            "rejection_reason": self.rejection_reason,
            "parent_approval_id": self.parent_approval_id,
            "approval_level": self.approval_level,
        }

    def approve(self, approver_id: int, comment: str = None):
        """Approve this request"""
        self.status = ApprovalStatus.APPROVED
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        self.approval_comment = comment
        db.session.commit()

    def reject(self, approver_id: int, reason: str):
        """Reject this request"""
        self.status = ApprovalStatus.REJECTED
        self.approved_by = approver_id
        self.rejected_at = datetime.utcnow()
        self.rejection_reason = reason
        db.session.commit()

    def cancel(self):
        """Cancel this request"""
        self.status = ApprovalStatus.CANCELLED
        db.session.commit()


class ApprovalPolicy(db.Model):
    """Approval policy for projects/users"""

    __tablename__ = "approval_policies"

    id = db.Column(db.Integer, primary_key=True)

    # Policy scope
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    applies_to_all = db.Column(db.Boolean, default=False, nullable=False)

    # Approval requirements
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)
    approval_levels = db.Column(db.Integer, default=1, nullable=False)  # Multi-level approvals
    approver_user_ids = db.Column(db.String(500), nullable=True)  # Comma-separated user IDs

    # Conditions
    min_hours = db.Column(db.Numeric(10, 2), nullable=True)  # Require approval if >= this many hours
    billable_only = db.Column(db.Boolean, default=False, nullable=False)  # Only require approval for billable time

    # Auto-approval rules
    auto_approve_after_hours = db.Column(db.Integer, nullable=True)  # Auto-approve after X hours if no response
    auto_approve_for_admins = db.Column(db.Boolean, default=False, nullable=False)

    # Status
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = db.relationship("Project", backref=db.backref("approval_policies", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("approval_policies", lazy="dynamic"))

    def __repr__(self):
        scope = f"project={self.project_id}" if self.project_id else f"user={self.user_id}" if self.user_id else "all"
        return f"<ApprovalPolicy {self.id} - {scope}>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "applies_to_all": self.applies_to_all,
            "requires_approval": self.requires_approval,
            "approval_levels": self.approval_levels,
            "approver_user_ids": self.approver_user_ids.split(",") if self.approver_user_ids else [],
            "min_hours": float(self.min_hours) if self.min_hours else None,
            "billable_only": self.billable_only,
            "auto_approve_after_hours": self.auto_approve_after_hours,
            "auto_approve_for_admins": self.auto_approve_for_admins,
            "enabled": self.enabled,
        }

    def get_approvers(self):
        """Get list of approver user IDs"""
        if self.approver_user_ids:
            return [int(uid) for uid in self.approver_user_ids.split(",") if uid.strip()]
        return []

    def applies_to_entry(self, time_entry) -> bool:
        """Check if this policy applies to a time entry"""
        if not self.enabled or not self.requires_approval:
            return False

        # Check project match
        if self.project_id and time_entry.project_id != self.project_id:
            return False

        # Check user match
        if self.user_id and time_entry.user_id != self.user_id:
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
