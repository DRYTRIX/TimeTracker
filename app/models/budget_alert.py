from datetime import datetime, timedelta
from app import db


class BudgetAlert(db.Model):
    """Budget alert model for tracking project budget warnings and notifications"""

    __tablename__ = "budget_alerts"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)

    # Alert details
    alert_type = db.Column(db.String(20), nullable=False)  # 'warning_80', 'warning_100', 'over_budget'
    alert_level = db.Column(db.String(20), nullable=False)  # 'info', 'warning', 'critical'
    budget_consumed_percent = db.Column(db.Numeric(5, 2), nullable=False)  # Percentage of budget consumed
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Budget at time of alert
    consumed_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Amount consumed at time of alert

    # Alert message and status
    message = db.Column(db.Text, nullable=False)
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    project = db.relationship("Project", backref=db.backref("budget_alerts", lazy="dynamic"))

    def __init__(
        self, project_id, alert_type, alert_level, budget_consumed_percent, budget_amount, consumed_amount, message
    ):
        self.project_id = project_id
        self.alert_type = alert_type
        self.alert_level = alert_level
        self.budget_consumed_percent = budget_consumed_percent
        self.budget_amount = budget_amount
        self.consumed_amount = consumed_amount
        self.message = message

    def __repr__(self):
        return f"<BudgetAlert {self.alert_type} for Project {self.project_id}>"

    def acknowledge(self, user_id):
        """Mark this alert as acknowledged by a user"""
        self.is_acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert budget alert to dictionary for API responses"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "alert_type": self.alert_type,
            "alert_level": self.alert_level,
            "budget_consumed_percent": float(self.budget_consumed_percent),
            "budget_amount": float(self.budget_amount),
            "consumed_amount": float(self.consumed_amount),
            "message": self.message,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_active_alerts(cls, project_id=None, acknowledged=False):
        """Get active alerts, optionally filtered by project"""
        query = cls.query.filter_by(is_acknowledged=acknowledged)

        if project_id:
            query = query.filter_by(project_id=project_id)

        return query.order_by(cls.created_at.desc()).all()

    @classmethod
    def create_alert(cls, project_id, alert_type, budget_consumed_percent, budget_amount, consumed_amount):
        """Create a new budget alert"""
        # Determine alert level based on type
        alert_levels = {"warning_80": "warning", "warning_100": "critical", "over_budget": "critical"}
        alert_level = alert_levels.get(alert_type, "info")

        # Generate alert message
        message = cls._generate_message(alert_type, budget_consumed_percent, budget_amount, consumed_amount)

        # Check if similar alert already exists (avoid duplicates)
        recent_alert = (
            cls.query.filter_by(project_id=project_id, alert_type=alert_type, is_acknowledged=False)
            .filter(cls.created_at >= datetime.utcnow() - timedelta(hours=24))
            .first()
        )

        if recent_alert:
            return recent_alert

        # Create new alert
        alert = cls(
            project_id=project_id,
            alert_type=alert_type,
            alert_level=alert_level,
            budget_consumed_percent=budget_consumed_percent,
            budget_amount=budget_amount,
            consumed_amount=consumed_amount,
            message=message,
        )

        db.session.add(alert)
        db.session.commit()

        return alert

    @staticmethod
    def _generate_message(alert_type, budget_consumed_percent, budget_amount, consumed_amount):
        """Generate alert message based on alert type"""
        messages = {
            "warning_80": f"Warning: Project has consumed {budget_consumed_percent:.1f}% of budget (${consumed_amount:.2f} of ${budget_amount:.2f})",
            "warning_100": f"Alert: Project has reached 100% of budget (${consumed_amount:.2f} of ${budget_amount:.2f})",
            "over_budget": f"Critical: Project is over budget by ${consumed_amount - budget_amount:.2f} ({budget_consumed_percent:.1f}% consumed)",
        }
        return messages.get(alert_type, "Budget alert")

    @classmethod
    def get_alert_summary(cls, project_id=None):
        """Get summary statistics for budget alerts"""
        query = cls.query

        if project_id:
            query = query.filter_by(project_id=project_id)

        total_alerts = query.count()
        unacknowledged_alerts = query.filter_by(is_acknowledged=False).count()
        critical_alerts = query.filter_by(alert_level="critical", is_acknowledged=False).count()

        return {
            "total_alerts": total_alerts,
            "unacknowledged_alerts": unacknowledged_alerts,
            "critical_alerts": critical_alerts,
        }
