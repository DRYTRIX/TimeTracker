"""add kanban columns table

Revision ID: 019
Revises: 018
Create Date: 2025-10-11 16:35:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    """Add kanban_columns table for customizable kanban board columns"""

    # Create kanban_columns table
    op.create_table(
        "kanban_columns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=True, server_default="fas fa-circle"),
        sa.Column("color", sa.String(length=50), nullable=True, server_default="secondary"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_complete_state", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # Create indexes
    op.create_index("idx_kanban_columns_key", "kanban_columns", ["key"])
    op.create_index("idx_kanban_columns_position", "kanban_columns", ["position"])

    # Insert default kanban columns
    connection = op.get_bind()
    connection.execute(text("""
        INSERT INTO kanban_columns (key, label, icon, color, position, is_active, is_system, is_complete_state)
        VALUES
            ('todo', 'To Do', 'fas fa-list-check', 'secondary', 0, true, true, false),
            ('in_progress', 'In Progress', 'fas fa-spinner', 'warning', 1, true, true, false),
            ('review', 'Review', 'fas fa-user-check', 'info', 2, true, false, false),
            ('done', 'Done', 'fas fa-check-circle', 'success', 3, true, true, true)
    """))


def downgrade():
    """Remove kanban_columns table"""
    op.drop_index("idx_kanban_columns_position", table_name="kanban_columns")
    op.drop_index("idx_kanban_columns_key", table_name="kanban_columns")
    op.drop_table("kanban_columns")
