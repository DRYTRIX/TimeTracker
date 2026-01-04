"""Add webhooks system for integrations

Revision ID: 046
Revises: 045
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None


def upgrade():
    """Create webhooks and webhook_deliveries tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Create webhooks table
    if 'webhooks' in existing_tables:
        print("✓ Table webhooks already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('webhooks')]
            for idx_name, cols in [
                ('ix_webhooks_user_id', ['user_id']),
                ('ix_webhooks_is_active', ['is_active']),
                ('ix_webhooks_created_at', ['created_at']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'webhooks', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('webhooks',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('name', sa.String(length=200), nullable=False),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('url', sa.String(length=500), nullable=False),
                sa.Column('secret', sa.String(length=128), nullable=True),
                sa.Column('events', sa.JSON(), nullable=False, server_default='[]'),
                sa.Column('http_method', sa.String(length=10), nullable=False, server_default='POST'),
                sa.Column('content_type', sa.String(length=50), nullable=False, server_default='application/json'),
                sa.Column('headers', sa.JSON(), nullable=True),
                sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
                sa.Column('user_id', sa.Integer(), nullable=False),
                sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
                sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='60'),
                sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
                sa.Column('total_deliveries', sa.Integer(), nullable=False, server_default='0'),
                sa.Column('successful_deliveries', sa.Integer(), nullable=False, server_default='0'),
                sa.Column('failed_deliveries', sa.Integer(), nullable=False, server_default='0'),
                sa.Column('last_delivery_at', sa.DateTime(), nullable=True),
                sa.Column('last_success_at', sa.DateTime(), nullable=True),
                sa.Column('last_failure_at', sa.DateTime(), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
                sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            
            # Create indexes for webhooks
            op.create_index('ix_webhooks_user_id', 'webhooks', ['user_id'])
            op.create_index('ix_webhooks_is_active', 'webhooks', ['is_active'])
            op.create_index('ix_webhooks_created_at', 'webhooks', ['created_at'])
            print("✓ Created webhooks table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table webhooks already exists (detected via error)")
            else:
                print(f"✗ Error creating webhooks table: {e}")
                raise
    
    # Create webhook_deliveries table
    if 'webhook_deliveries' in existing_tables:
        print("✓ Table webhook_deliveries already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('webhook_deliveries')]
            for idx_name, cols in [
                ('ix_webhook_deliveries_webhook_id', ['webhook_id']),
                ('ix_webhook_deliveries_status', ['status']),
                ('ix_webhook_deliveries_event_type', ['event_type']),
                ('ix_webhook_deliveries_next_retry_at', ['next_retry_at']),
                ('ix_webhook_deliveries_started_at', ['started_at']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'webhook_deliveries', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('webhook_deliveries',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('webhook_id', sa.Integer(), nullable=False),
                sa.Column('event_type', sa.String(length=100), nullable=False),
                sa.Column('event_id', sa.String(length=100), nullable=True),
                sa.Column('payload', sa.Text(), nullable=False),
                sa.Column('payload_hash', sa.String(length=64), nullable=True),
                sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
                sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
                sa.Column('response_status_code', sa.Integer(), nullable=True),
                sa.Column('response_body', sa.Text(), nullable=True),
                sa.Column('response_headers', sa.JSON(), nullable=True),
                sa.Column('error_message', sa.Text(), nullable=True),
                sa.Column('error_type', sa.String(length=100), nullable=True),
                sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
                sa.Column('completed_at', sa.DateTime(), nullable=True),
                sa.Column('duration_ms', sa.Integer(), nullable=True),
                sa.Column('next_retry_at', sa.DateTime(), nullable=True),
                sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
                sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            
            # Create indexes for webhook_deliveries
            op.create_index('ix_webhook_deliveries_webhook_id', 'webhook_deliveries', ['webhook_id'])
            op.create_index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status'])
            op.create_index('ix_webhook_deliveries_event_type', 'webhook_deliveries', ['event_type'])
            op.create_index('ix_webhook_deliveries_next_retry_at', 'webhook_deliveries', ['next_retry_at'])
            op.create_index('ix_webhook_deliveries_started_at', 'webhook_deliveries', ['started_at'])
            print("✓ Created webhook_deliveries table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table webhook_deliveries already exists (detected via error)")
            else:
                print(f"✗ Error creating webhook_deliveries table: {e}")
                raise


def downgrade():
    """Remove webhooks system tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Drop webhook_deliveries table
    if 'webhook_deliveries' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('webhook_deliveries')]
            for idx_name in ['ix_webhook_deliveries_started_at', 'ix_webhook_deliveries_next_retry_at',
                           'ix_webhook_deliveries_event_type', 'ix_webhook_deliveries_status',
                           'ix_webhook_deliveries_webhook_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='webhook_deliveries')
                    except Exception:
                        pass
            op.drop_table('webhook_deliveries')
            print("✓ Dropped webhook_deliveries table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table webhook_deliveries does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop webhook_deliveries table: {e}")
    
    # Drop webhooks table
    if 'webhooks' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('webhooks')]
            for idx_name in ['ix_webhooks_created_at', 'ix_webhooks_is_active', 'ix_webhooks_user_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='webhooks')
                    except Exception:
                        pass
            op.drop_table('webhooks')
            print("✓ Dropped webhooks table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table webhooks does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop webhooks table: {e}")

