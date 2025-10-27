"""Add email configuration settings to Settings model

Revision ID: 033_add_email_settings
Revises: 032_add_api_tokens
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033_add_email_settings'
down_revision = '032_add_api_tokens'
branch_labels = None
depends_on = None


def upgrade():
    """Add email configuration columns to settings table"""
    # Add email configuration columns
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mail_enabled', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mail_server', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('mail_port', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('mail_use_tls', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mail_use_ssl', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mail_username', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('mail_password', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('mail_default_sender', sa.String(length=255), nullable=True))
    
    # Set default values for existing rows
    op.execute("""
        UPDATE settings 
        SET mail_enabled = false,
            mail_port = 587,
            mail_use_tls = true,
            mail_use_ssl = false,
            mail_server = '',
            mail_username = '',
            mail_password = '',
            mail_default_sender = ''
        WHERE mail_enabled IS NULL
    """)
    
    # Make mail_enabled non-nullable after setting defaults
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column('mail_enabled', nullable=False)


def downgrade():
    """Remove email configuration columns from settings table"""
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_column('mail_default_sender')
        batch_op.drop_column('mail_password')
        batch_op.drop_column('mail_username')
        batch_op.drop_column('mail_use_ssl')
        batch_op.drop_column('mail_use_tls')
        batch_op.drop_column('mail_port')
        batch_op.drop_column('mail_server')
        batch_op.drop_column('mail_enabled')

