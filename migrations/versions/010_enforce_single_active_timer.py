"""enforce single active timer per user via partial unique index

Revision ID: 010
Revises: 009
Create Date: 2025-09-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    inspector = sa.inspect(bind)
    if "time_entries" not in inspector.get_table_names():
        return

    # Best-effort deduplication: close all but the most recent active timer per user
    try:
        if dialect in ("postgresql", "sqlite"):
            # For backends supporting CTE with window functions in UPDATE
            op.execute(sa.text("""
                    WITH ranked AS (
                        SELECT id, user_id,
                               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY start_time DESC, id DESC) AS rn
                        FROM time_entries
                        WHERE end_time IS NULL
                    )
                    UPDATE time_entries
                    SET end_time = start_time
                    WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
                    """))
    except Exception:
        # Ignore and proceed; server-side logic already prevents future duplicates
        pass

    # Create partial unique index to enforce at DB level
    if dialect in ("postgresql", "sqlite"):
        try:
            op.execute(
                sa.text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_time_entries_one_active_per_user ON time_entries(user_id) WHERE end_time IS NULL"
                )
            )
        except Exception:
            # If index exists or backend doesn't support partial indexes, ignore
            pass


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect in ("postgresql", "sqlite"):
        try:
            op.execute(sa.text("DROP INDEX IF EXISTS ux_time_entries_one_active_per_user"))
        except Exception:
            # SQLite may require table-qualified index drop or ignore if absent
            pass
