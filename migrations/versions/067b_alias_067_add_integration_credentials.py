"""Alias revision for older databases

Revision ID: 067_add_integration_credentials
Revises: 067_integration_credentials
Create Date: 2026-01-02

Some deployments recorded the revision id as '067_add_integration_credentials'
in the database, while the actual migration shipped as '067_integration_credentials'.

This revision is a no-op "alias" that lets Alembic resolve and continue the
migration chain.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "067_add_integration_credentials"
down_revision = "067_integration_credentials"
branch_labels = None
depends_on = None


def upgrade():
    # No-op alias revision
    pass


def downgrade():
    # No-op alias revision
    pass

