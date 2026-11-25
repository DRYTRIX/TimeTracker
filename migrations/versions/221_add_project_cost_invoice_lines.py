"""Project costs on invoice lines: which line bills a cost, and the recurring cost it came from.

- ``project_costs``: ``invoice_item_id`` (the line of kind ``cost`` that bills the cost; one line may
  bill several costs) and ``recurring_cost_id`` (the recurring cost that generated it).
- ``invoices``: ``costs_layout``, how the invoice's project costs became lines.

Existing invoiced costs are linked to their line: a line of the same invoice whose description is
``"<description> (<category>)"`` (the catalog category's name, or the old category text) and whose
unit price is the cost's amount, as Generate from Time wrote it. The line becomes a ``cost`` line. Costs without such a line stay unlinked and are counted
in the log. The downgrade only drops the columns.

Revision ID: 221_add_project_cost_invoice_lines
Revises: 220_add_invoice_hours_layout
"""

import logging
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "221_add_project_cost_invoice_lines"
down_revision = "220_add_invoice_hours_layout"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

MONEY = Decimal("0.01")


def _has_table(inspector, name):
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _columns(inspector, table_name):
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _money(value):
    try:
        return Decimal(str(value if value is not None else 0)).quantize(MONEY)
    except Exception:
        return None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_table(inspector, "project_costs"):
        existing = _columns(inspector, "project_costs")
        with op.batch_alter_table("project_costs") as batch:
            if "invoice_item_id" not in existing:
                batch.add_column(sa.Column("invoice_item_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(
                    "fk_project_costs_invoice_item_id",
                    "invoice_items",
                    ["invoice_item_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch.create_index("ix_project_costs_invoice_item_id", ["invoice_item_id"])
            if "recurring_cost_id" not in existing and _has_table(inspector, "recurring_project_costs"):
                batch.add_column(sa.Column("recurring_cost_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(
                    "fk_project_costs_recurring_cost_id",
                    "recurring_project_costs",
                    ["recurring_cost_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch.create_index("ix_project_costs_recurring_cost_id", ["recurring_cost_id"])

    if _has_table(inspector, "invoices") and "costs_layout" not in _columns(inspector, "invoices"):
        # Plain ADD COLUMN (no batch copy): SQLite keeps the table, so foreign keys pointing at it stay valid
        op.add_column("invoices", sa.Column("costs_layout", sa.String(length=20), nullable=True))

    _link_existing(bind, inspect(bind))


def _link_existing(bind, inspector):
    """Link invoiced costs to the line Generate from Time wrote for them."""
    if not _has_table(inspector, "invoice_items") or "kind" not in _columns(inspector, "invoice_items"):
        return
    has_categories = _has_table(inspector, "expense_categories")
    category_join = "LEFT JOIN expense_categories ec ON ec.id = pc.category_id" if has_categories else ""
    category_name = "ec.name" if has_categories else "NULL"
    costs = bind.execute(
        sa.text(
            "SELECT pc.id, pc.invoice_id, pc.description, pc.category, pc.amount, "
            f"{category_name} AS category_name "
            f"FROM project_costs pc {category_join} "
            "WHERE pc.invoice_id IS NOT NULL AND pc.invoice_item_id IS NULL "
            "ORDER BY pc.id"
        )
    ).fetchall()
    if not costs:
        return

    invoice_ids = sorted({row[1] for row in costs})
    lines = {}
    for start in range(0, len(invoice_ids), 500):
        chunk = invoice_ids[start : start + 500]
        rows = bind.execute(
            sa.text(
                "SELECT id, invoice_id, description, unit_price, kind FROM invoice_items "
                "WHERE invoice_id IN ({}) ORDER BY id".format(",".join(str(int(i)) for i in chunk))
            )
        ).fetchall()
        for item_id, invoice_id, description, unit_price, kind in rows:
            lines.setdefault(invoice_id, []).append(
                {"id": item_id, "description": (description or "").strip(), "price": _money(unit_price), "kind": kind}
            )

    used = set()
    linked = missed = 0
    for cost_id, invoice_id, description, legacy, amount, category_name in costs:
        # The line names the category as it was when it was written: the catalog name, or the old
        # category text for lines written before costs had catalog categories
        labels = [label for label in dict.fromkeys([category_name, legacy]) if label]
        wanted = {f"{(description or '').strip()} ({label})" for label in labels}
        price = _money(amount)
        match = next(
            (
                line
                for line in lines.get(invoice_id, [])
                if line["id"] not in used
                and line["kind"] != "time"
                and line["description"] in wanted
                and line["price"] == price
            ),
            None,
        )
        if match is None:
            missed += 1
            continue
        used.add(match["id"])
        bind.execute(
            sa.text("UPDATE project_costs SET invoice_item_id = :item WHERE id = :cost"),
            {"item": match["id"], "cost": cost_id},
        )
        bind.execute(sa.text("UPDATE invoice_items SET kind = 'cost' WHERE id = :item"), {"item": match["id"]})
        linked += 1
    logger.info("Project costs linked to their invoice line: %d; left without a line: %d", linked, missed)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "costs_layout" in _columns(inspector, "invoices"):
        op.drop_column("invoices", "costs_layout")
    existing = _columns(inspector, "project_costs")
    if not existing & {"invoice_item_id", "recurring_cost_id"}:
        return
    with op.batch_alter_table("project_costs") as batch:
        if "recurring_cost_id" in existing:
            batch.drop_index("ix_project_costs_recurring_cost_id")
            batch.drop_constraint("fk_project_costs_recurring_cost_id", type_="foreignkey")
            batch.drop_column("recurring_cost_id")
        if "invoice_item_id" in existing:
            batch.drop_index("ix_project_costs_invoice_item_id")
            batch.drop_constraint("fk_project_costs_invoice_item_id", type_="foreignkey")
            batch.drop_column("invoice_item_id")
