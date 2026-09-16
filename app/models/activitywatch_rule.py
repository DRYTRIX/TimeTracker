"""ActivityWatch mapping rules and pending review queue."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app import db


class ActivityWatchRule(db.Model):
    __tablename__ = "activitywatch_rules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    pattern_type = db.Column(db.String(30), nullable=False, default="app")  # app|domain|title_regex|url_regex
    pattern_value = db.Column(db.String(500), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    billable = db.Column(db.Boolean, nullable=False, default=True)
    min_duration_seconds = db.Column(db.Integer, nullable=True)
    priority = db.Column(db.Integer, nullable=False, default=100)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "pattern_value": self.pattern_value,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "tags": self.tags or [],
            "billable": self.billable,
            "min_duration_seconds": self.min_duration_seconds,
            "priority": self.priority,
            "is_active": self.is_active,
        }

    def matches(self, *, app: str = "", title: str = "", url: str = "") -> bool:
        value = (self.pattern_value or "").strip()
        if not value:
            return False
        ptype = (self.pattern_type or "app").lower()
        try:
            if ptype == "app":
                return value.lower() in (app or "").lower()
            if ptype == "domain":
                return value.lower() in (url or "").lower()
            if ptype == "title_regex":
                return bool(re.search(value, title or "", re.IGNORECASE))
            if ptype == "url_regex":
                return bool(re.search(value, url or "", re.IGNORECASE))
        except re.error:
            return False
        return False

    @classmethod
    def match_event(cls, user_id: int, app: str, title: str, url: str) -> Optional["ActivityWatchRule"]:
        rules = (
            cls.query.filter_by(user_id=user_id, is_active=True)
            .order_by(cls.priority.asc(), cls.id.asc())
            .all()
        )
        for rule in rules:
            if rule.matches(app=app, title=title, url=url):
                return rule
        return None


class PendingActivity(db.Model):
    __tablename__ = "pending_activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    aw_bucket = db.Column(db.String(255), nullable=True)
    app_name = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(500), nullable=True)
    url = db.Column(db.String(1000), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False, default=0)
    matched_rule_id = db.Column(db.Integer, db.ForeignKey("activitywatch_rules.id"), nullable=True)
    suggested_project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    suggested_task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    suggested_billable = db.Column(db.Boolean, nullable=False, default=True)
    external_uid = db.Column(db.String(255), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)  # pending|approved|discarded
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "aw_bucket": self.aw_bucket,
            "app_name": self.app_name,
            "title": self.title,
            "url": self.url,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_seconds": self.duration_seconds,
            "matched_rule_id": self.matched_rule_id,
            "suggested_project_id": self.suggested_project_id,
            "suggested_task_id": self.suggested_task_id,
            "suggested_billable": self.suggested_billable,
            "status": self.status,
            "notes": self.notes,
        }
