"""Workflow template service."""

from datetime import datetime
from typing import Optional

from app import db
from app.models.workflow import WorkflowRule, WorkflowTemplate


class WorkflowTemplateService:
    """Manage workflow template library and cloning."""

    def list_available(self, user_id: int, is_admin: bool = False):
        query = WorkflowTemplate.query
        if is_admin:
            return query.order_by(WorkflowTemplate.category, WorkflowTemplate.name).all()
        return (
            query.filter((WorkflowTemplate.is_public == True) | (WorkflowTemplate.created_by == user_id))  # noqa: E712
            .order_by(WorkflowTemplate.category, WorkflowTemplate.name)
            .all()
        )

    def get_template(self, template_id: int) -> Optional[WorkflowTemplate]:
        return WorkflowTemplate.query.get(template_id)

    def create_template(self, data: dict, created_by: int) -> WorkflowTemplate:
        template = WorkflowTemplate(
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            tags=data.get("tags") or [],
            trigger_type=data["trigger_type"],
            trigger_conditions=data.get("trigger_conditions") or [],
            actions=data.get("actions") or [],
            is_public=bool(data.get("is_public", False)),
            created_by=created_by,
        )
        db.session.add(template)
        db.session.commit()
        return template

    def update_template(self, template: WorkflowTemplate, data: dict) -> WorkflowTemplate:
        for field in (
            "name",
            "description",
            "category",
            "tags",
            "trigger_type",
            "trigger_conditions",
            "actions",
            "is_public",
        ):
            if field in data:
                setattr(template, field, data[field])
        db.session.commit()
        return template

    def delete_template(self, template: WorkflowTemplate) -> None:
        db.session.delete(template)
        db.session.commit()

    def clone_to_rule(self, template_id: int, user_id: int, name: Optional[str] = None) -> WorkflowRule:
        template = WorkflowTemplate.query.get_or_404(template_id)
        if not template.is_public and template.created_by != user_id:
            from flask import abort

            abort(403)

        rule = WorkflowRule(
            name=name or template.name,
            description=template.description,
            trigger_type=template.trigger_type,
            trigger_conditions=template.trigger_conditions or [],
            actions=template.actions or [],
            enabled=True,
            priority=0,
            user_id=user_id,
            created_by=user_id,
        )
        template.usage_count = (template.usage_count or 0) + 1
        template.last_used_at = datetime.utcnow()
        db.session.add(rule)
        db.session.commit()
        return rule
