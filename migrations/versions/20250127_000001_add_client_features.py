"""Add client features: notifications, comments, etc.

Revision ID: 20250127_000001
Revises: 096_add_missing_portal_issues_enabled
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250127_000001'
down_revision = '096_add_missing_portal_issues_enabled'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_fk(inspector, table_name: str, fk_name: str) -> bool:
    try:
        fks = inspector.get_foreign_keys(table_name)
        return any((fk.get("name") or "") == fk_name for fk in fks)
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        indexes = inspector.get_indexes(table_name)
        return any((idx.get("name") or "") == index_name for idx in indexes)
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')
    bool_false_default = '0' if dialect_name == 'sqlite' else ('false' if dialect_name == 'postgresql' else '0')

    # Create client_notifications table (idempotent)
    if not _has_table(inspector, "client_notifications"):
        op.create_table(
            'client_notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('link_url', sa.String(length=500), nullable=True),
            sa.Column('link_text', sa.String(length=100), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('extra_data', sa.JSON(), nullable=True),  # renamed from 'metadata'
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    for idx_name, cols, unique in [
        (op.f('ix_client_notifications_client_id'), ['client_id'], False),
        (op.f('ix_client_notifications_type'), ['type'], False),
        (op.f('ix_client_notifications_is_read'), ['is_read'], False),
        (op.f('ix_client_notifications_created_at'), ['created_at'], False),
    ]:
        try:
            if _has_table(inspector, "client_notifications") and not _has_index(inspector, "client_notifications", idx_name):
                op.create_index(idx_name, 'client_notifications', cols, unique=unique)
        except Exception:
            pass

    # Create client_notification_preferences table (idempotent)
    if not _has_table(inspector, "client_notification_preferences"):
        op.create_table(
            'client_notification_preferences',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_invoice_created', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_invoice_paid', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_invoice_overdue', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_project_milestone', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_budget_alert', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_time_entry_approval', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('email_project_status_change', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)),
            sa.Column('email_quote_available', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('client_id')
        )

    idx_pref = op.f('ix_client_notification_preferences_client_id')
    try:
        if _has_table(inspector, "client_notification_preferences") and not _has_index(inspector, "client_notification_preferences", idx_pref):
            op.create_index(idx_pref, 'client_notification_preferences', ['client_id'], unique=True)
    except Exception:
        pass

    # Update comments table to support client comments (SQLite-safe via batch mode)
    if _has_table(inspector, "comments"):
        if dialect_name == "sqlite":
            with op.batch_alter_table("comments") as batch_op:
                if not _has_column(inspector, "comments", "client_contact_id"):
                    batch_op.add_column(sa.Column('client_contact_id', sa.Integer(), nullable=True))
                if not _has_column(inspector, "comments", "is_client_comment"):
                    batch_op.add_column(sa.Column('is_client_comment', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)))
                # user_id may already be nullable in some installs
                if _has_column(inspector, "comments", "user_id"):
                    batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=True)

                # FK only if contacts table exists
                if _has_table(inspector, "contacts") and not _has_fk(inspector, "comments", "fk_comments_client_contact"):
                    batch_op.create_foreign_key('fk_comments_client_contact', 'contacts', ['client_contact_id'], ['id'])
        else:
            if not _has_column(inspector, "comments", "client_contact_id"):
                op.add_column('comments', sa.Column('client_contact_id', sa.Integer(), nullable=True))
            if not _has_column(inspector, "comments", "is_client_comment"):
                op.add_column('comments', sa.Column('is_client_comment', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)))
            try:
                if _has_column(inspector, "comments", "user_id"):
                    op.alter_column('comments', 'user_id', existing_type=sa.Integer(), nullable=True)
            except Exception:
                pass
            try:
                if _has_table(inspector, "contacts") and not _has_fk(inspector, "comments", "fk_comments_client_contact"):
                    op.create_foreign_key('fk_comments_client_contact', 'comments', 'contacts', ['client_contact_id'], ['id'])
            except Exception:
                pass

        # Index for lookups (best-effort)
        idx_comments = op.f('ix_comments_client_contact_id')
        try:
            if not _has_index(inspector, "comments", idx_comments):
                op.create_index(idx_comments, 'comments', ['client_contact_id'], unique=False)
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"

    # Remove comment changes (best-effort; downgrades are not commonly used)
    if _has_table(inspector, "comments"):
        idx_comments = op.f('ix_comments_client_contact_id')
        try:
            op.drop_index(idx_comments, table_name='comments')
        except Exception:
            pass
        try:
            op.drop_constraint('fk_comments_client_contact', 'comments', type_='foreignkey')
        except Exception:
            pass
        try:
            if dialect_name == "sqlite":
                with op.batch_alter_table("comments") as batch_op:
                    if _has_column(inspector, "comments", "user_id"):
                        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
                    if _has_column(inspector, "comments", "is_client_comment"):
                        batch_op.drop_column('is_client_comment')
                    if _has_column(inspector, "comments", "client_contact_id"):
                        batch_op.drop_column('client_contact_id')
            else:
                if _has_column(inspector, "comments", "user_id"):
                    op.alter_column('comments', 'user_id', existing_type=sa.Integer(), nullable=False)
                if _has_column(inspector, "comments", "is_client_comment"):
                    op.drop_column('comments', 'is_client_comment')
                if _has_column(inspector, "comments", "client_contact_id"):
                    op.drop_column('comments', 'client_contact_id')
        except Exception:
            pass

    # Remove notification preferences
    if _has_table(inspector, "client_notification_preferences"):
        try:
            op.drop_index(op.f('ix_client_notification_preferences_client_id'), table_name='client_notification_preferences')
        except Exception:
            pass
        try:
            op.drop_table('client_notification_preferences')
        except Exception:
            pass

    # Remove notifications
    if _has_table(inspector, "client_notifications"):
        for idx_name in [
            op.f('ix_client_notifications_created_at'),
            op.f('ix_client_notifications_is_read'),
            op.f('ix_client_notifications_type'),
            op.f('ix_client_notifications_client_id'),
        ]:
            try:
                op.drop_index(idx_name, table_name='client_notifications')
            except Exception:
                pass
        try:
            op.drop_table('client_notifications')
        except Exception:
            pass
