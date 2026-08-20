"""Fix PostgreSQL approvalstatus enum to use lowercase values.

SQLAlchemy create_all() can create approvalstatus with member names
(PENDING, APPROVED, ...) while the model emits values (pending, approved, ...).
Migration 070 skipped recreating the type when it already existed, leaving
/approvals queries failing with InvalidTextRepresentation.

Revision ID: 178_fix_approvalstatus_enum_case
Revises: 177_add_app_base_url
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "178_fix_approvalstatus_enum_case"
down_revision = "177_add_app_base_url"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = inspect(bind)
    if "time_entry_approvals" not in inspector.get_table_names():
        return

    row = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'approvalstatus' AND e.enumlabel = 'pending'"
        )
    ).fetchone()
    if row:
        return

    type_exists = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'approvalstatus'")
    ).fetchone()
    if not type_exists:
        return

    op.execute("ALTER TABLE time_entry_approvals ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE time_entry_approvals "
        "ALTER COLUMN status TYPE VARCHAR(20) USING status::text"
    )
    op.execute("UPDATE time_entry_approvals SET status = LOWER(status)")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute(
        "CREATE TYPE approvalstatus AS ENUM "
        "('pending', 'approved', 'rejected', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE time_entry_approvals "
        "ALTER COLUMN status TYPE approvalstatus "
        "USING status::approvalstatus"
    )
    op.execute(
        "ALTER TABLE time_entry_approvals "
        "ALTER COLUMN status SET DEFAULT 'pending'::approvalstatus"
    )


def downgrade():
    # Lowercase labels match the application model; do not restore uppercase.
    pass
