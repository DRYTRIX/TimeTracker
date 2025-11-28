"""Add client portal customization and team chat tables

Revision ID: 072_client_portal_team_chat
Revises: 071_add_recurring_tasks
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '072_client_portal_team_chat'
down_revision = '071_add_recurring_tasks'
branch_labels = None
depends_on = None


def upgrade():
    """Create client portal customization and team chat tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create client_portal_customizations table
    if 'client_portal_customizations' not in inspector.get_table_names():
        op.create_table(
            'client_portal_customizations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('logo_url', sa.String(length=500), nullable=True),
            sa.Column('logo_upload_path', sa.String(length=500), nullable=True),
            sa.Column('favicon_url', sa.String(length=500), nullable=True),
            sa.Column('primary_color', sa.String(length=7), nullable=True),
            sa.Column('secondary_color', sa.String(length=7), nullable=True),
            sa.Column('accent_color', sa.String(length=7), nullable=True),
            sa.Column('font_family', sa.String(length=100), nullable=True),
            sa.Column('heading_font', sa.String(length=100), nullable=True),
            sa.Column('custom_css', sa.Text(), nullable=True),
            sa.Column('custom_header_html', sa.Text(), nullable=True),
            sa.Column('custom_footer_html', sa.Text(), nullable=True),
            sa.Column('portal_title', sa.String(length=200), nullable=True),
            sa.Column('portal_description', sa.Text(), nullable=True),
            sa.Column('welcome_message', sa.Text(), nullable=True),
            sa.Column('show_projects', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('show_invoices', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('show_time_entries', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('show_quotes', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('custom_navigation_items', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('client_id')
        )

    # Create chat_channels table
    if 'chat_channels' not in inspector.get_table_names():
        op.create_table(
            'chat_channels',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('channel_type', sa.String(length=20), nullable=False, server_default='public'),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_chat_channels_project_id'), 'chat_channels', ['project_id'], unique=False)
        op.create_index('ix_chat_channels_type', 'chat_channels', ['channel_type'], unique=False)

    # Create chat_channel_members table
    if 'chat_channel_members' not in inspector.get_table_names():
        op.create_table(
            'chat_channel_members',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('channel_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('muted_until', sa.DateTime(), nullable=True),
            sa.Column('joined_at', sa.DateTime(), nullable=False),
            sa.Column('last_read_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['channel_id'], ['chat_channels.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('channel_id', 'user_id', name='uq_channel_member')
        )
        op.create_index(op.f('ix_chat_channel_members_channel_id'), 'chat_channel_members', ['channel_id'], unique=False)
        op.create_index(op.f('ix_chat_channel_members_user_id'), 'chat_channel_members', ['user_id'], unique=False)
        op.create_index('ix_chat_channel_members_channel_user', 'chat_channel_members', ['channel_id', 'user_id'], unique=False)

    # Create chat_messages table
    if 'chat_messages' not in inspector.get_table_names():
        op.create_table(
            'chat_messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('channel_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('message_type', sa.String(length=20), nullable=False, server_default='text'),
            sa.Column('attachment_url', sa.String(length=500), nullable=True),
            sa.Column('attachment_filename', sa.String(length=255), nullable=True),
            sa.Column('attachment_size', sa.Integer(), nullable=True),
            sa.Column('reply_to_id', sa.Integer(), nullable=True),
            sa.Column('mentions', sa.JSON(), nullable=True),
            sa.Column('reactions', sa.JSON(), nullable=True),
            sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('edited_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['channel_id'], ['chat_channels.id'], ),
            sa.ForeignKeyConstraint(['reply_to_id'], ['chat_messages.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_chat_messages_channel_id'), 'chat_messages', ['channel_id'], unique=False)
        op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)
        op.create_index('ix_chat_messages_channel_created', 'chat_messages', ['channel_id', 'created_at'], unique=False)

    # Create chat_read_receipts table
    if 'chat_read_receipts' not in inspector.get_table_names():
        op.create_table(
            'chat_read_receipts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('read_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('message_id', 'user_id', name='uq_read_receipt')
        )
        op.create_index(op.f('ix_chat_read_receipts_message_id'), 'chat_read_receipts', ['message_id'], unique=False)
        op.create_index(op.f('ix_chat_read_receipts_user_id'), 'chat_read_receipts', ['user_id'], unique=False)

    # Create client_time_approvals table
    if 'client_time_approvals' not in inspector.get_table_names():
        op.create_table(
            'client_time_approvals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('time_entry_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'cancelled', name='clientapprovalstatus', create_type=False), nullable=False),
            sa.Column('requested_by', sa.Integer(), nullable=False),
            sa.Column('approved_by', sa.Integer(), nullable=True),
            sa.Column('requested_at', sa.DateTime(), nullable=False),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('rejected_at', sa.DateTime(), nullable=True),
            sa.Column('request_comment', sa.Text(), nullable=True),
            sa.Column('approval_comment', sa.Text(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['time_entry_id'], ['time_entries.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_client_time_approvals_time_entry_id'), 'client_time_approvals', ['time_entry_id'], unique=False)
        op.create_index(op.f('ix_client_time_approvals_project_id'), 'client_time_approvals', ['project_id'], unique=False)
        op.create_index(op.f('ix_client_time_approvals_client_id'), 'client_time_approvals', ['client_id'], unique=False)
        op.create_index(op.f('ix_client_time_approvals_status'), 'client_time_approvals', ['status'], unique=False)

    # Create client_approval_policies table
    if 'client_approval_policies' not in inspector.get_table_names():
        op.create_table(
            'client_approval_policies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('auto_approve_after_days', sa.Integer(), nullable=True),
            sa.Column('min_hours', sa.Numeric(10, 2), nullable=True),
            sa.Column('billable_only', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_client_approval_policies_client_id'), 'client_approval_policies', ['client_id'], unique=False)
        op.create_index(op.f('ix_client_approval_policies_project_id'), 'client_approval_policies', ['project_id'], unique=False)


def downgrade():
    """Drop tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ['client_approval_policies', 'client_time_approvals', 'chat_read_receipts', 
                  'chat_messages', 'chat_channel_members', 'chat_channels', 
                  'client_portal_customizations']:
        if table in inspector.get_table_names():
            op.drop_table(table)

    # Drop enum if using PostgreSQL
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS clientapprovalstatus")

