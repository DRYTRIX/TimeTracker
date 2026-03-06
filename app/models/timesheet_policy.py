from datetime import datetime

from app import db


class TimesheetPolicy(db.Model):
    """Configurable lock and approval-chain policy for period workflows."""

    __tablename__ = "timesheet_policies"

    id = db.Column(db.Integer, primary_key=True)
    default_period_type = db.Column(db.String(20), nullable=False, default="weekly")
    auto_lock_days = db.Column(db.Integer, nullable=True)
    approver_user_ids = db.Column(db.String(1000), nullable=True)
    enable_multi_level_approval = db.Column(db.Boolean, nullable=False, default=False)
    require_rejection_comment = db.Column(db.Boolean, nullable=False, default=True)
    enable_admin_override = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def get_approver_ids(self):
        if not self.approver_user_ids:
            return []
        result = []
        for raw in self.approver_user_ids.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                result.append(int(raw))
            except ValueError:
                continue
        return result

    def to_dict(self):
        return {
            "id": self.id,
            "default_period_type": self.default_period_type,
            "auto_lock_days": self.auto_lock_days,
            "approver_user_ids": self.get_approver_ids(),
            "enable_multi_level_approval": self.enable_multi_level_approval,
            "require_rejection_comment": self.require_rejection_comment,
            "enable_admin_override": self.enable_admin_override,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
