"""Add client messages, email threads, payroll sync logs, and portal API tokens.

Revision ID: 194_roadmap_features
Revises: 193_client_surveys_and_custom_domain
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "194_roadmap_features"
down_revision = "193_client_surveys_and_custom_domain"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "client_messages" not in tables:
        op.create_table(
            "client_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender_type", sa.String(length=20), nullable=False),
            sa.Column("sender_id", sa.Integer(), nullable=True),
            sa.Column("sender_name", sa.String(length=200), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachments", sa.JSON(), nullable=True),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_client_messages_client_id", "client_messages", ["client_id"])
        op.create_index("ix_client_messages_client_created", "client_messages", ["client_id", "created_at"])

    if "email_threads" not in tables:
        op.create_table(
            "email_threads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("external_thread_id", sa.String(length=255), nullable=False),
            sa.Column("subject", sa.String(length=500), nullable=True),
            sa.Column("snippet", sa.Text(), nullable=True),
            sa.Column("participants", sa.JSON(), nullable=True),
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
            sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
            sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
            sa.Column("last_message_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_email_threads_external_thread_id", "email_threads", ["external_thread_id"])
        op.create_index("ix_email_threads_client_id", "email_threads", ["client_id"])
        op.create_index("ix_email_threads_lead_id", "email_threads", ["lead_id"])
        op.create_index("ix_email_threads_deal_id", "email_threads", ["deal_id"])

    if "email_messages" not in tables:
        op.create_table(
            "email_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("thread_id", sa.Integer(), sa.ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("external_message_id", sa.String(length=255), nullable=False),
            sa.Column("from_address", sa.String(length=320), nullable=True),
            sa.Column("to_addresses", sa.JSON(), nullable=True),
            sa.Column("subject", sa.String(length=500), nullable=True),
            sa.Column("body_text", sa.Text(), nullable=True),
            sa.Column("body_html", sa.Text(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_email_messages_thread_id", "email_messages", ["thread_id"])
        op.create_index("ix_email_messages_external_message_id", "email_messages", ["external_message_id"])

    if "payroll_sync_logs" not in tables:
        op.create_table(
            "payroll_sync_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
            sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hours_total", sa.Float(), nullable=False, server_default="0"),
            sa.Column("external_batch_id", sa.String(length=255), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("payload_summary", sa.JSON(), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    if "api_tokens" in tables and not _has_column(inspector, "api_tokens", "client_id"):
        op.add_column("api_tokens", sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True))
        op.create_index("ix_api_tokens_client_id", "api_tokens", ["client_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "api_tokens" in tables and _has_column(inspector, "api_tokens", "client_id"):
        op.drop_index("ix_api_tokens_client_id", table_name="api_tokens")
        op.drop_column("api_tokens", "client_id")

    if "payroll_sync_logs" in tables:
        op.drop_table("payroll_sync_logs")
    if "email_messages" in tables:
        op.drop_table("email_messages")
    if "email_threads" in tables:
        op.drop_table("email_threads")
    if "client_messages" in tables:
        op.drop_table("client_messages")
