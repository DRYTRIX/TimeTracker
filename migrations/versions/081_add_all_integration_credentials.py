"""Add all integration OAuth credentials to Settings model

Revision ID: 081_add_int_oauth_creds
Revises: 080_fix_metadata_column_names
Create Date: 2025-01-15 12:00:00

This migration adds OAuth credential columns for all integrations:
- Google Calendar
- Outlook Calendar
- Microsoft Teams
- Asana
- Trello
- GitLab
- QuickBooks
- Xero
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '081_add_int_oauth_creds'
down_revision = '080_fix_metadata_column_names'
branch_labels = None
depends_on = None


def upgrade():
    """Add integration OAuth credential columns to settings table"""
    with op.batch_alter_table('settings', schema=None) as batch_op:
        # Google Calendar
        batch_op.add_column(sa.Column('google_calendar_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('google_calendar_client_secret', sa.String(length=255), nullable=True))
        
        # Outlook Calendar
        batch_op.add_column(sa.Column('outlook_calendar_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('outlook_calendar_client_secret', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('outlook_calendar_tenant_id', sa.String(length=255), nullable=True))
        
        # Microsoft Teams
        batch_op.add_column(sa.Column('microsoft_teams_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('microsoft_teams_client_secret', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('microsoft_teams_tenant_id', sa.String(length=255), nullable=True))
        
        # Asana
        batch_op.add_column(sa.Column('asana_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('asana_client_secret', sa.String(length=255), nullable=True))
        
        # Trello
        batch_op.add_column(sa.Column('trello_api_key', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('trello_api_secret', sa.String(length=255), nullable=True))
        
        # GitLab
        batch_op.add_column(sa.Column('gitlab_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('gitlab_client_secret', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('gitlab_instance_url', sa.String(length=500), nullable=True))
        
        # QuickBooks
        batch_op.add_column(sa.Column('quickbooks_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('quickbooks_client_secret', sa.String(length=255), nullable=True))
        
        # Xero
        batch_op.add_column(sa.Column('xero_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('xero_client_secret', sa.String(length=255), nullable=True))
    
    # Set default empty values for existing rows
    op.execute("""
        UPDATE settings 
        SET google_calendar_client_id = '',
            google_calendar_client_secret = '',
            outlook_calendar_client_id = '',
            outlook_calendar_client_secret = '',
            outlook_calendar_tenant_id = '',
            microsoft_teams_client_id = '',
            microsoft_teams_client_secret = '',
            microsoft_teams_tenant_id = '',
            asana_client_id = '',
            asana_client_secret = '',
            trello_api_key = '',
            trello_api_secret = '',
            gitlab_client_id = '',
            gitlab_client_secret = '',
            gitlab_instance_url = '',
            quickbooks_client_id = '',
            quickbooks_client_secret = '',
            xero_client_id = '',
            xero_client_secret = ''
        WHERE google_calendar_client_id IS NULL
    """)


def downgrade():
    """Remove integration credential columns from settings table"""
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_column('xero_client_secret')
        batch_op.drop_column('xero_client_id')
        batch_op.drop_column('quickbooks_client_secret')
        batch_op.drop_column('quickbooks_client_id')
        batch_op.drop_column('gitlab_instance_url')
        batch_op.drop_column('gitlab_client_secret')
        batch_op.drop_column('gitlab_client_id')
        batch_op.drop_column('trello_api_secret')
        batch_op.drop_column('trello_api_key')
        batch_op.drop_column('asana_client_secret')
        batch_op.drop_column('asana_client_id')
        batch_op.drop_column('microsoft_teams_tenant_id')
        batch_op.drop_column('microsoft_teams_client_secret')
        batch_op.drop_column('microsoft_teams_client_id')
        batch_op.drop_column('outlook_calendar_tenant_id')
        batch_op.drop_column('outlook_calendar_client_secret')
        batch_op.drop_column('outlook_calendar_client_id')
        batch_op.drop_column('google_calendar_client_secret')
        batch_op.drop_column('google_calendar_client_id')

