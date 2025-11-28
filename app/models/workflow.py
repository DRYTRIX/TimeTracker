"""
Workflow automation models for rule-based automation
"""

from datetime import datetime
from app import db
from sqlalchemy import JSON


class WorkflowRule(db.Model):
    """Workflow rule model for automation"""

    __tablename__ = "workflow_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Trigger configuration
    trigger_type = db.Column(db.String(50), nullable=False)  # 'task_status_change', 'time_logged', etc.
    trigger_conditions = db.Column(JSON, nullable=True)  # Additional conditions

    # Actions to perform
    actions = db.Column(JSON, nullable=False)  # List of actions

    # Rule status
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=0, nullable=False)  # Higher priority runs first

    # Ownership
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_executed_at = db.Column(db.DateTime, nullable=True)
    execution_count = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("workflow_rules", lazy="dynamic"))
    creator = db.relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<WorkflowRule {self.name} ({self.trigger_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_conditions": self.trigger_conditions,
            "actions": self.actions,
            "enabled": self.enabled,
            "priority": self.priority,
            "user_id": self.user_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_count": self.execution_count,
        }


class WorkflowExecution(db.Model):
    """Workflow execution log"""

    __tablename__ = "workflow_executions"

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("workflow_rules.id"), nullable=False, index=True)

    # Execution details
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    result = db.Column(JSON, nullable=True)  # Execution results

    # Context
    trigger_event = db.Column(JSON, nullable=True)  # Event that triggered execution
    execution_time_ms = db.Column(db.Integer, nullable=True)  # Execution duration

    # Relationships
    rule = db.relationship("WorkflowRule", backref=db.backref("executions", lazy="dynamic"))

    def __repr__(self):
        return f"<WorkflowExecution rule={self.rule_id} success={self.success}>"

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "result": self.result,
            "trigger_event": self.trigger_event,
            "execution_time_ms": self.execution_time_ms,
        }

