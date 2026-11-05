"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_person", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("default_hourly_rate", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_clients_name", "clients", ["name"], unique=True)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_login", sa.TIMESTAMP(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=True)
    op.create_index("idx_users_role", "users", ["role"])

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("billable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("hourly_rate", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("billing_ref", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_projects_client_id", "projects", ["client_id"])
    op.create_index("idx_projects_status", "projects", ["status"])

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tasks_project_id", "tasks", ["project_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_priority", "tasks", ["priority"])

    # Create time_entries table
    op.create_table(
        "time_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(), nullable=True),
        sa.Column("duration", sa.Interval(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.String(length=500), nullable=True),
        sa.Column("billable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_time_entries_user_id", "time_entries", ["user_id"])
    op.create_index("idx_time_entries_project_id", "time_entries", ["project_id"])
    op.create_index("idx_time_entries_start_time", "time_entries", ["start_time"])

    # Create settings table
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("company_address", sa.Text(), nullable=True),
        sa.Column("company_phone", sa.String(length=50), nullable=True),
        sa.Column("company_email", sa.String(length=200), nullable=True),
        sa.Column("company_website", sa.String(length=200), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="Europe/Rome"),
        sa.Column("rounding_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("single_active_timer", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("idle_timeout_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("allow_self_register", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_analytics", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("logo_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_invoices_client_id", "invoices", ["client_id"])
    op.create_index("idx_invoices_status", "invoices", ["status"])

    # Create invoice_items table
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(precision=9, scale=2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("time_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["time_entry_id"], ["time_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_invoice_items_invoice_id", "invoice_items", ["invoice_id"])


def downgrade():
    # Drop tables in reverse order
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("settings")
    op.drop_table("time_entries")
    op.drop_table("tasks")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("clients")
