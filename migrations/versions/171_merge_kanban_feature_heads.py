"""Merge the three parallel kanban feature migration heads into one.

The per-column WIP limits (168), task checklists (169), and board templates
(170) migrations were each authored off 166_add_slack_user_id as an independent
branch, so with all three merged the revision graph has three heads and
``flask db upgrade`` fails with "Multiple head revisions are present". This
no-op merge migration rejoins them into a single head; each feature migration is
independent (adds its own table/column), so no ordering constraint is imposed.

Revision ID: 171_merge_kanban_feature_heads
Revises: 168_add_kanban_wip_limit, 169_add_task_checklist_items, 170_add_kanban_board_templates
"""

revision = "171_merge_kanban_feature_heads"
down_revision = (
    "168_add_kanban_wip_limit",
    "169_add_task_checklist_items",
    "170_add_kanban_board_templates",
)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
