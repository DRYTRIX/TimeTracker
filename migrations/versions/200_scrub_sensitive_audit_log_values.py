"""Scrub sensitive field values from audit_logs (issue #801).

Revision ID: 200_scrub_sensitive_audit_log_values
Revises: 199_task_multi_assignees
"""

from alembic import op
from sqlalchemy import inspect, text

revision = "200_scrub_sensitive_audit_log_values"
down_revision = "199_task_multi_assignees"
branch_labels = None
depends_on = None

# Keep aligned with EXCLUDED_FIELDS secrets in app/utils/audit.py
_SENSITIVE_FIELD_NAMES = (
    "password",
    "password_hash",
    "two_factor_secret",
    "portal_password_hash",
    "password_setup_token",
    "mail_password",
    "peppol_access_point_token",
    "ai_api_key",
    "jira_client_secret",
    "slack_client_secret",
    "github_client_secret",
    "google_calendar_client_secret",
    "outlook_calendar_client_secret",
    "microsoft_teams_client_secret",
    "asana_client_secret",
    "trello_api_secret",
    "gitlab_client_secret",
    "quickbooks_client_secret",
    "xero_client_secret",
)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "audit_logs" not in inspector.get_table_names():
        return

    # Null out stored secret material; keep the change row (who/when/field).
    placeholders = ", ".join(f":f{i}" for i in range(len(_SENSITIVE_FIELD_NAMES)))
    params = {f"f{i}": name for i, name in enumerate(_SENSITIVE_FIELD_NAMES)}
    bind.execute(
        text(
            f"""
            UPDATE audit_logs
            SET old_value = NULL, new_value = NULL
            WHERE field_name IN ({placeholders})
              AND (old_value IS NOT NULL OR new_value IS NOT NULL)
            """
        ),
        params,
    )


def downgrade():
    # Irreversible data scrub; nothing to restore.
    pass
