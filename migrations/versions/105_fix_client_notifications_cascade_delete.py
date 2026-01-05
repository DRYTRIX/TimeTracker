"""Fix client_notifications foreign keys to cascade on delete

Revision ID: 105_fix_client_notifications_cascade_delete
Revises: 104_add_missing_quotes_columns
Create Date: 2026-01-05

This migration fixes the foreign key constraints on client_notifications.client_id
and client_notification_preferences.client_id to cascade delete when a client is
deleted, preventing NOT NULL constraint violations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '105_fix_client_notifications_cascade_delete'
down_revision = '104_add_missing_quotes_columns'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_foreign_key(inspector, table_name: str, fk_name: str = None, column_name: str = None) -> bool:
    """Check if a foreign key exists"""
    try:
        fks = inspector.get_foreign_keys(table_name)
        if fk_name:
            return any((fk.get("name") or "") == fk_name for fk in fks)
        if column_name:
            return any(col in (fk.get("constrained_columns") or []) for fk in fks for col in fk.get("constrained_columns", []))
        return len(fks) > 0
    except Exception:
        return False


def _get_foreign_key_name(inspector, table_name: str, column_name: str) -> str:
    """Get the name of a foreign key constraint for a column"""
    try:
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            if column_name in (fk.get("constrained_columns") or []):
                return fk.get("name") or ""
    except Exception:
        pass
    return ""


def _fix_foreign_key(table_name: str, column_name: str, fk_name_prefix: str):
    """Helper function to fix a foreign key constraint to cascade on delete"""
    bind = op.get_bind()
    inspector = inspect(bind)
    dialect_name = bind.dialect.name if bind else 'generic'
    
    if not _has_table(inspector, table_name):
        print(f"[Migration 105] ⊘ {table_name} table does not exist, skipping")
        return
    
    # Check if foreign key exists
    fk_name = _get_foreign_key_name(inspector, table_name, column_name)
    
    if not fk_name:
        # No foreign key exists, create it with CASCADE
        print(f"[Migration 105] No foreign key found for {table_name}.{column_name}, creating with CASCADE...")
        try:
            if dialect_name == 'sqlite':
                with op.batch_alter_table(table_name, schema=None) as batch_op:
                    batch_op.create_foreign_key(
                        fk_name_prefix,
                        'clients',
                        [column_name],
                        ['id'],
                        ondelete='CASCADE'
                    )
            else:
                op.create_foreign_key(
                    fk_name_prefix,
                    table_name,
                    'clients',
                    [column_name],
                    ['id'],
                    ondelete='CASCADE'
                )
            print(f"[Migration 105] ✓ Foreign key created with CASCADE for {table_name}")
        except Exception as e:
            print(f"[Migration 105] ⚠ Warning: Could not create foreign key for {table_name}: {e}")
        return
    
    # Foreign key exists, recreate with CASCADE
    print(f"[Migration 105] Found foreign key {fk_name} for {table_name}.{column_name}, recreating with CASCADE...")
    
    if dialect_name == 'sqlite':
        try:
            with op.batch_alter_table(table_name, schema=None) as batch_op:
                # Drop old constraint
                batch_op.drop_constraint(fk_name, type_='foreignkey')
                # Create new one with CASCADE
                batch_op.create_foreign_key(
                    fk_name_prefix,
                    'clients',
                    [column_name],
                    ['id'],
                    ondelete='CASCADE'
                )
            print(f"[Migration 105] ✓ Foreign key recreated with CASCADE for {table_name}")
        except Exception as e:
            print(f"[Migration 105] ⚠ Warning: Could not recreate foreign key for {table_name}: {e}")
    else:
        # PostgreSQL and other databases
        try:
            # Drop old constraint
            op.drop_constraint(fk_name, table_name, type_='foreignkey')
            print(f"[Migration 105] ✓ Dropped old constraint: {fk_name}")
            
            # Create new one with CASCADE
            op.create_foreign_key(
                fk_name_prefix,
                table_name,
                'clients',
                [column_name],
                ['id'],
                ondelete='CASCADE'
            )
            print(f"[Migration 105] ✓ Created new foreign key with CASCADE for {table_name}")
        except Exception as e:
            print(f"[Migration 105] ✗ Error recreating foreign key for {table_name}: {e}")
            raise


def upgrade():
    """Fix client_notifications and client_notification_preferences foreign keys to cascade on delete"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    dialect_name = bind.dialect.name if bind else 'generic'
    print(f"[Migration 105] Running on {dialect_name} database")
    
    # Fix client_notifications
    _fix_foreign_key('client_notifications', 'client_id', 'fk_client_notifications_client_id')
    
    # Fix client_notification_preferences
    _fix_foreign_key('client_notification_preferences', 'client_id', 'fk_client_notification_preferences_client_id')
    
    print("[Migration 105] ✓ Migration completed successfully")


def downgrade():
    """Revert foreign keys to not cascade (original behavior)"""
    bind = op.get_bind()
    inspector = inspect(bind)
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Revert client_notifications
    if _has_table(inspector, 'client_notifications'):
        if _has_foreign_key(inspector, 'client_notifications', fk_name='fk_client_notifications_client_id'):
            try:
                if dialect_name == 'sqlite':
                    with op.batch_alter_table('client_notifications', schema=None) as batch_op:
                        batch_op.drop_constraint('fk_client_notifications_client_id', type_='foreignkey')
                        batch_op.create_foreign_key(
                            'fk_client_notifications_client_id',
                            'clients',
                            ['client_id'],
                            ['id']
                        )
                else:
                    op.drop_constraint('fk_client_notifications_client_id', 'client_notifications', type_='foreignkey')
                    op.create_foreign_key(
                        'fk_client_notifications_client_id',
                        'client_notifications',
                        'clients',
                        ['client_id'],
                        ['id']
                    )
                print("[Migration 105] ✓ Reverted client_notifications foreign key (no CASCADE)")
            except Exception as e:
                print(f"[Migration 105] ⚠ Warning: Could not revert client_notifications foreign key: {e}")
    
    # Revert client_notification_preferences
    if _has_table(inspector, 'client_notification_preferences'):
        if _has_foreign_key(inspector, 'client_notification_preferences', fk_name='fk_client_notification_preferences_client_id'):
            try:
                if dialect_name == 'sqlite':
                    with op.batch_alter_table('client_notification_preferences', schema=None) as batch_op:
                        batch_op.drop_constraint('fk_client_notification_preferences_client_id', type_='foreignkey')
                        batch_op.create_foreign_key(
                            'fk_client_notification_preferences_client_id',
                            'clients',
                            ['client_id'],
                            ['id']
                        )
                else:
                    op.drop_constraint('fk_client_notification_preferences_client_id', 'client_notification_preferences', type_='foreignkey')
                    op.create_foreign_key(
                        'fk_client_notification_preferences_client_id',
                        'client_notification_preferences',
                        'clients',
                        ['client_id'],
                        ['id']
                    )
                print("[Migration 105] ✓ Reverted client_notification_preferences foreign key (no CASCADE)")
            except Exception as e:
                print(f"[Migration 105] ⚠ Warning: Could not revert client_notification_preferences foreign key: {e}")
