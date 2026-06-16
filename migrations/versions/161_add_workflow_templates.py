"""Add workflow_templates table and seed starter presets."""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "161_add_workflow_templates"
down_revision = "160_add_invoice_expense_integration_metadata"
branch_labels = None
depends_on = None

SEED_TEMPLATES = [
    {
        "name": "Notify on task completion",
        "description": "Send a notification when a task is marked completed.",
        "category": "Tasks",
        "tags": ["tasks", "notifications"],
        "trigger_type": "task_completed",
        "trigger_conditions": [],
        "actions": [
            {
                "type": "send_notification",
                "title": "Task completed",
                "message": "{{task.name}} has been completed.",
            }
        ],
    },
    {
        "name": "Webhook on invoice paid",
        "description": "POST to a webhook when an invoice is paid.",
        "category": "Invoices",
        "tags": ["invoices", "webhooks"],
        "trigger_type": "invoice_paid",
        "trigger_conditions": [],
        "actions": [
            {
                "type": "webhook",
                "url": "https://example.com/webhooks/invoice-paid",
                "payload": {"invoice_id": "{{invoice.id}}", "amount": "{{invoice.total_amount}}"},
            }
        ],
    },
    {
        "name": "Assign task on status change",
        "description": "Assign a task to a user when status changes to in progress.",
        "category": "Tasks",
        "tags": ["tasks", "assignment"],
        "trigger_type": "task_status_change",
        "trigger_conditions": [{"field": "status", "operator": "==", "value": "in_progress"}],
        "actions": [{"type": "assign_task", "task_id": "{{task.id}}", "user_id": "{{user_id}}"}],
    },
    {
        "name": "Notify on time logged",
        "description": "Send notification when time is logged on a project.",
        "category": "Time",
        "tags": ["time", "notifications"],
        "trigger_type": "time_logged",
        "trigger_conditions": [],
        "actions": [
            {
                "type": "send_notification",
                "title": "Time logged",
                "message": "Time entry recorded for project {{project_id}}.",
            }
        ],
    },
    {
        "name": "Email on new invoice",
        "description": "Send email when a new invoice is created.",
        "category": "Invoices",
        "tags": ["invoices", "email"],
        "trigger_type": "invoice_created",
        "trigger_conditions": [],
        "actions": [
            {
                "type": "send_email",
                "to": "billing@example.com",
                "subject": "New invoice {{invoice.invoice_number}}",
                "body": "Invoice {{invoice.invoice_number}} was created.",
            }
        ],
    },
]


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "workflow_templates" in inspector.get_table_names():
        return

    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_templates_name", "workflow_templates", ["name"])
    op.create_index("ix_workflow_templates_category", "workflow_templates", ["category"])
    op.create_index("ix_workflow_templates_is_public", "workflow_templates", ["is_public"])
    op.create_index("ix_workflow_templates_created_by", "workflow_templates", ["created_by"])

    # Seed templates using first admin user if available
    conn = op.get_bind()
    admin_row = conn.execute(sa.text("SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1")).fetchone()
    if not admin_row:
        admin_row = conn.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
    if admin_row:
        admin_id = admin_row[0]
        now = datetime.utcnow()
        for tpl in SEED_TEMPLATES:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO workflow_templates
                    (name, description, category, tags, trigger_type, trigger_conditions, actions,
                     is_public, created_by, usage_count, created_at, updated_at)
                    VALUES
                    (:name, :description, :category, :tags, :trigger_type, :trigger_conditions, :actions,
                     true, :created_by, 0, :now, :now)
                    """
                ),
                {
                    "name": tpl["name"],
                    "description": tpl["description"],
                    "category": tpl["category"],
                    "tags": json.dumps(tpl["tags"]),
                    "trigger_type": tpl["trigger_type"],
                    "trigger_conditions": json.dumps(tpl["trigger_conditions"]),
                    "actions": json.dumps(tpl["actions"]),
                    "created_by": admin_id,
                    "now": now,
                },
            )


def downgrade():
    op.drop_table("workflow_templates")
