"""Add global integrations support

Revision ID: 082_add_global_integrations
Revises: 081_add_int_oauth_creds
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '082_add_global_integrations'
down_revision = '081_add_int_oauth_creds'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if integrations table exists
    table_names = set(inspector.get_table_names())
    if 'integrations' not in table_names:
        print("⚠ Integrations table does not exist, skipping migration")
        return
    
    # Check if is_global column already exists
    try:
        current_cols = {c['name'] for c in inspector.get_columns('integrations')}
        if 'is_global' in current_cols:
            print("✓ Column is_global already exists in integrations table")
        else:
            # Add is_global flag
            try:
                with op.batch_alter_table('integrations', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('is_global', sa.Boolean(), nullable=False, server_default='0'))
                print("✓ Added is_global column to integrations table")
            except Exception as e:
                error_msg = str(e)
                if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    print("✓ Column is_global already exists in integrations table (detected via error)")
                else:
                    print(f"✗ Error adding is_global column to integrations table: {e}")
                    raise
    except Exception as e:
        print(f"⚠ Warning checking for is_global column: {e}")
        # Try to add it anyway, catching the error if it already exists
        try:
            with op.batch_alter_table('integrations', schema=None) as batch_op:
                batch_op.add_column(sa.Column('is_global', sa.Boolean(), nullable=False, server_default='0'))
            print("✓ Added is_global column to integrations table")
        except Exception as e2:
            error_msg = str(e2)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Column is_global already exists in integrations table (detected via error)")
            else:
                raise
    
    # Make user_id nullable for global integrations (if not already nullable)
    try:
        current_cols = inspector.get_columns('integrations')
        user_id_col = next((c for c in current_cols if c['name'] == 'user_id'), None)
        if user_id_col and user_id_col.get('nullable', False):
            print("✓ Column user_id is already nullable in integrations table")
        else:
            with op.batch_alter_table('integrations', schema=None) as batch_op:
                batch_op.alter_column('user_id',
                                      existing_type=sa.Integer(),
                                      nullable=True)
            print("✓ Made user_id nullable in integrations table")
    except Exception as e:
        error_msg = str(e)
        if 'already' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column user_id is already nullable in integrations table (detected via error)")
        else:
            print(f"⚠ Warning altering user_id column: {e}")
    
    # Add index for global integrations (if it doesn't exist)
    try:
        indexes = {idx['name'] for idx in inspector.get_indexes('integrations')}
        if 'ix_integrations_is_global' in indexes:
            print("✓ Index ix_integrations_is_global already exists")
        else:
            op.create_index('ix_integrations_is_global', 'integrations', ['is_global'], unique=False)
            print("✓ Created index ix_integrations_is_global")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Index ix_integrations_is_global already exists (detected via error)")
        else:
            print(f"⚠ Warning creating index: {e}")
    
    # Note: Unique constraint for global integrations enforced at application level
    # (one global integration per provider) since SQLite doesn't support partial indexes


def downgrade():
    with op.batch_alter_table('integrations', schema=None) as batch_op:
        # Remove index
        batch_op.drop_index('ix_integrations_is_global')
        
        # Make user_id required again (set to first user for existing records)
        # First, set user_id for any null values
        op.execute("UPDATE integrations SET user_id = (SELECT id FROM users LIMIT 1) WHERE user_id IS NULL")
        
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=False)
        
        # Remove is_global column
        batch_op.drop_column('is_global')

