"""Add integration OAuth credentials to Settings model

Revision ID: 067_add_integration_credentials
Revises: 066_add_integration_framework
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '067_add_integration_credentials'
down_revision = '066_add_integration_framework'
branch_labels = None
depends_on = None


def upgrade():
    """Add integration OAuth credential columns to settings table"""
    # Add integration credential columns
    with op.batch_alter_table('settings', schema=None) as batch_op:
        # Jira
        batch_op.add_column(sa.Column('jira_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('jira_client_secret', sa.String(length=255), nullable=True))
        # Slack
        batch_op.add_column(sa.Column('slack_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('slack_client_secret', sa.String(length=255), nullable=True))
        # GitHub
        batch_op.add_column(sa.Column('github_client_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('github_client_secret', sa.String(length=255), nullable=True))
    
    # Set default empty values for existing rows
    op.execute("""
        UPDATE settings 
        SET jira_client_id = '',
            jira_client_secret = '',
            slack_client_id = '',
            slack_client_secret = '',
            github_client_id = '',
            github_client_secret = ''
        WHERE jira_client_id IS NULL
    """)


def downgrade():
    """Remove integration credential columns from settings table"""
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_column('github_client_secret')
        batch_op.drop_column('github_client_id')
        batch_op.drop_column('slack_client_secret')
        batch_op.drop_column('slack_client_id')
        batch_op.drop_column('jira_client_secret')
        batch_op.drop_column('jira_client_id')

