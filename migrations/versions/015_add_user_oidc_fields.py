"""add OIDC fields to users

Revision ID: 015
Revises: 014
Create Date: 2025-10-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in [col['name'] for col in inspector.get_columns(table_name)]


def _has_constraint(inspector, table_name: str, constraint_name: str) -> bool:
    try:
        constraints = inspector.get_unique_constraints(table_name)
        return any(c.get('name') == constraint_name for c in constraints)
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Ensure users table exists
    if 'users' not in inspector.get_table_names():
        return

    # Add columns if missing
    if not _has_column(inspector, 'users', 'email'):
        op.add_column('users', sa.Column('email', sa.String(length=200), nullable=True))
        try:
            op.create_index('ix_users_email', 'users', ['email'], unique=False)
        except Exception:
            pass

    if not _has_column(inspector, 'users', 'oidc_sub'):
        op.add_column('users', sa.Column('oidc_sub', sa.String(length=255), nullable=True))

    if not _has_column(inspector, 'users', 'oidc_issuer'):
        op.add_column('users', sa.Column('oidc_issuer', sa.String(length=255), nullable=True))

    # Add composite unique constraint if not present
    if not _has_constraint(inspector, 'users', 'uq_users_oidc_issuer_sub'):
        try:
            # SQLite can't generally add constraints with ALTER TABLE; use batch mode there.
            if bind.dialect.name == 'sqlite':
                with op.batch_alter_table('users') as batch_op:
                    batch_op.create_unique_constraint('uq_users_oidc_issuer_sub', ['oidc_issuer', 'oidc_sub'])
            else:
                op.create_unique_constraint('uq_users_oidc_issuer_sub', 'users', ['oidc_issuer', 'oidc_sub'])
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    # Drop unique constraint if exists
    try:
        op.drop_constraint('uq_users_oidc_issuer_sub', 'users', type_='unique')
    except Exception:
        pass

    # Drop columns if exist (order doesn't matter)
    for col in ['oidc_issuer', 'oidc_sub', 'email']:
        if _has_column(inspector, 'users', col):
            try:
                op.drop_column('users', col)
            except Exception:
                pass

