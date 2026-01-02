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


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    """Add integration OAuth credential columns to settings table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "settings"):
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}

    with op.batch_alter_table('settings', schema=None) as batch_op:
        # Google Calendar
        if 'google_calendar_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('google_calendar_client_id', sa.String(length=255), nullable=True))
        if 'google_calendar_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('google_calendar_client_secret', sa.String(length=255), nullable=True))
        
        # Outlook Calendar
        if 'outlook_calendar_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('outlook_calendar_client_id', sa.String(length=255), nullable=True))
        if 'outlook_calendar_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('outlook_calendar_client_secret', sa.String(length=255), nullable=True))
        if 'outlook_calendar_tenant_id' not in settings_cols:
            batch_op.add_column(sa.Column('outlook_calendar_tenant_id', sa.String(length=255), nullable=True))
        
        # Microsoft Teams
        if 'microsoft_teams_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('microsoft_teams_client_id', sa.String(length=255), nullable=True))
        if 'microsoft_teams_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('microsoft_teams_client_secret', sa.String(length=255), nullable=True))
        if 'microsoft_teams_tenant_id' not in settings_cols:
            batch_op.add_column(sa.Column('microsoft_teams_tenant_id', sa.String(length=255), nullable=True))
        
        # Asana
        if 'asana_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('asana_client_id', sa.String(length=255), nullable=True))
        if 'asana_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('asana_client_secret', sa.String(length=255), nullable=True))
        
        # Trello
        if 'trello_api_key' not in settings_cols:
            batch_op.add_column(sa.Column('trello_api_key', sa.String(length=255), nullable=True))
        if 'trello_api_secret' not in settings_cols:
            batch_op.add_column(sa.Column('trello_api_secret', sa.String(length=255), nullable=True))
        
        # GitLab
        if 'gitlab_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('gitlab_client_id', sa.String(length=255), nullable=True))
        if 'gitlab_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('gitlab_client_secret', sa.String(length=255), nullable=True))
        if 'gitlab_instance_url' not in settings_cols:
            batch_op.add_column(sa.Column('gitlab_instance_url', sa.String(length=500), nullable=True))
        
        # QuickBooks
        if 'quickbooks_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('quickbooks_client_id', sa.String(length=255), nullable=True))
        if 'quickbooks_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('quickbooks_client_secret', sa.String(length=255), nullable=True))
        
        # Xero
        if 'xero_client_id' not in settings_cols:
            batch_op.add_column(sa.Column('xero_client_id', sa.String(length=255), nullable=True))
        if 'xero_client_secret' not in settings_cols:
            batch_op.add_column(sa.Column('xero_client_secret', sa.String(length=255), nullable=True))
    
    # Refresh column list after alterations, then set defaults only for columns that exist.
    inspector = sa.inspect(op.get_bind())
    settings_cols = {c["name"] for c in inspector.get_columns("settings")}

    set_parts = []
    for col in [
        "google_calendar_client_id",
        "google_calendar_client_secret",
        "outlook_calendar_client_id",
        "outlook_calendar_client_secret",
        "outlook_calendar_tenant_id",
        "microsoft_teams_client_id",
        "microsoft_teams_client_secret",
        "microsoft_teams_tenant_id",
        "asana_client_id",
        "asana_client_secret",
        "trello_api_key",
        "trello_api_secret",
        "gitlab_client_id",
        "gitlab_client_secret",
        "gitlab_instance_url",
        "quickbooks_client_id",
        "quickbooks_client_secret",
        "xero_client_id",
        "xero_client_secret",
    ]:
        if col in settings_cols:
            set_parts.append(f"{col} = ''")

    if set_parts:
        where_col = (
            "google_calendar_client_id"
            if "google_calendar_client_id" in settings_cols
            else set_parts[0].split(" = ")[0]
        )
        op.execute(
            f"UPDATE settings SET {', '.join(set_parts)} WHERE {where_col} IS NULL"
        )


def downgrade():
    """Remove integration credential columns from settings table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "settings"):
        return

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}

    with op.batch_alter_table('settings', schema=None) as batch_op:
        for col in [
            'xero_client_secret',
            'xero_client_id',
            'quickbooks_client_secret',
            'quickbooks_client_id',
            'gitlab_instance_url',
            'gitlab_client_secret',
            'gitlab_client_id',
            'trello_api_secret',
            'trello_api_key',
            'asana_client_secret',
            'asana_client_id',
            'microsoft_teams_tenant_id',
            'microsoft_teams_client_secret',
            'microsoft_teams_client_id',
            'outlook_calendar_tenant_id',
            'outlook_calendar_client_secret',
            'outlook_calendar_client_id',
            'google_calendar_client_secret',
            'google_calendar_client_id',
        ]:
            if col in settings_cols:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass

