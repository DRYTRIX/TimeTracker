"""Merge the two parallel 183 migration heads into one.

183_add_device_token_push_subscription and 183_add_idle_needs_review were
both authored off 182_add_project_last_used_at as independent branches,
giving two heads and breaking flask db upgrade. This no-op merge rejoins
them into a single head.

Revision ID: 184_merge_183_heads
Revises: 183_add_device_token_push_subscription, 183_add_idle_needs_review
"""

revision = "184_merge_183_heads"
down_revision = (
    "183_add_device_token_push_subscription",
    "183_add_idle_needs_review",
)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
