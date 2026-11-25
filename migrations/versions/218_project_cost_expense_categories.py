"""Link project costs and recurring project costs to expense categories.

Adds ``category_id`` to project_costs and recurring_project_costs. Every category string in use,
plus the standard set the forms used to offer, is matched to an expense category by code or name
(case-insensitive); a missing one is created with receipts and approval off. The legacy
``category`` string stays.

Revision ID: 218_project_cost_expense_categories
Revises: 217_invoice_html_templates
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "218_project_cost_expense_categories"
down_revision = "217_invoice_html_templates"
branch_labels = None
depends_on = None

COST_TABLES = ("project_costs", "recurring_project_costs")
STANDARD_CATEGORIES = ("travel", "materials", "services", "equipment", "software", "other")


def _has_table(inspector, name):
    return name in inspector.get_table_names()


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _find_category_id(bind, value):
    key = value.lower()
    row = bind.execute(sa.text("SELECT id FROM expense_categories WHERE lower(code) = :key"), {"key": key}).first()
    if row is None:
        row = bind.execute(sa.text("SELECT id FROM expense_categories WHERE lower(name) = :key"), {"key": key}).first()
    return row[0] if row else None


def _create_category(bind, value):
    code = value if len(value) <= 20 else None
    if code is not None:
        taken = bind.execute(
            sa.text("SELECT 1 FROM expense_categories WHERE lower(code) = :key"), {"key": code.lower()}
        ).first()
        if taken:
            code = None
    now = datetime.utcnow()
    bind.execute(
        sa.text(
            "INSERT INTO expense_categories "
            "(name, code, budget_threshold_percent, requires_receipt, requires_approval, is_active, "
            "created_at, updated_at) "
            "VALUES (:name, :code, 80, :false, :false, :true, :now, :now)"
        ),
        {"name": value[:1].upper() + value[1:], "code": code, "false": False, "true": True, "now": now},
    )
    return _find_category_id(bind, value)


def _backfill(bind, inspector):
    existing = [t for t in COST_TABLES if _has_table(inspector, t)]
    values = {}
    for value in STANDARD_CATEGORIES:
        values.setdefault(value.lower(), value)
    for table in existing:
        rows = bind.execute(sa.text(f"SELECT DISTINCT category FROM {table} WHERE category IS NOT NULL")).fetchall()
        for (value,) in rows:
            value = (value or "").strip()
            if value:
                values.setdefault(value.lower(), value)

    for key, value in values.items():
        category_id = _find_category_id(bind, value)
        if category_id is None:
            category_id = _create_category(bind, value)
        for table in existing:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET category_id = :category_id "
                    "WHERE category_id IS NULL AND lower(trim(category)) = :key"
                ),
                {"category_id": category_id, "key": key},
            )


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "expense_categories"):
        return

    for table in COST_TABLES:
        if not _has_table(inspector, table) or _has_column(inspector, table, "category_id"):
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_category_id", "expense_categories", ["category_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index(f"ix_{table}_category_id", ["category_id"])

    _backfill(bind, inspect(bind))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Expense categories created by the upgrade are kept: they may already be in use.
    for table in COST_TABLES:
        if not _has_table(inspector, table) or not _has_column(inspector, table, "category_id"):
            continue
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_category_id")
            batch.drop_constraint(f"fk_{table}_category_id", type_="foreignkey")
            batch.drop_column("category_id")
