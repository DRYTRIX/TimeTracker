"""Add stock lots (valuation layers) for devaluation support

Revision ID: 097_add_stock_lots_for_devaluation
Revises: 20250127_000001
Create Date: 2026-01-03

This migration introduces:
- stock_lots: per-warehouse valuation layers (unit_cost + quantity)
- stock_lot_allocations: links stock_movements to lots for FIFO and auditing

It also seeds an initial "legacy" lot per (warehouse_stock, stock_item) where quantity_on_hand > 0,
using StockItem.default_cost (or 0) as unit_cost.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "097_add_stock_lots_for_devaluation"
down_revision = "20250127_000001"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        indexes = inspector.get_indexes(table_name)
        return any((idx.get("name") or "") == index_name for idx in indexes)
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"

    # Create stock_lots table (idempotent)
    if not _has_table(inspector, "stock_lots"):
        op.create_table(
            "stock_lots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("stock_item_id", sa.Integer(), sa.ForeignKey("stock_items.id"), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("lot_type", sa.String(length=20), nullable=False, server_default="normal"),
            sa.Column("unit_cost", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
            sa.Column("quantity_on_hand", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("source_movement_id", sa.Integer(), sa.ForeignKey("stock_movements.id"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )

    # Indexes (best-effort)
    for idx_name, cols, unique in [
        ("ix_stock_lots_stock_item_id", ["stock_item_id"], False),
        ("ix_stock_lots_warehouse_id", ["warehouse_id"], False),
        ("ix_stock_lots_lot_type", ["lot_type"], False),
        ("ix_stock_lots_created_at", ["created_at"], False),
        ("ix_stock_lots_created_by", ["created_by"], False),
        ("ix_stock_lots_source_movement_id", ["source_movement_id"], False),
        ("ix_stock_lots_item_wh_cost_type", ["stock_item_id", "warehouse_id", "unit_cost", "lot_type"], False),
    ]:
        try:
            if _has_table(inspector, "stock_lots") and not _has_index(inspector, "stock_lots", idx_name):
                op.create_index(idx_name, "stock_lots", cols, unique=unique)
        except Exception:
            pass

    # Create stock_lot_allocations table (idempotent)
    if not _has_table(inspector, "stock_lot_allocations"):
        op.create_table(
            "stock_lot_allocations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("stock_movement_id", sa.Integer(), sa.ForeignKey("stock_movements.id"), nullable=False),
            sa.Column("stock_lot_id", sa.Integer(), sa.ForeignKey("stock_lots.id"), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("unit_cost", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    for idx_name, cols, unique in [
        ("ix_stock_lot_allocations_stock_movement_id", ["stock_movement_id"], False),
        ("ix_stock_lot_allocations_stock_lot_id", ["stock_lot_id"], False),
        ("ix_stock_lot_allocations_created_at", ["created_at"], False),
        ("ix_stock_lot_allocations_move_lot", ["stock_movement_id", "stock_lot_id"], False),
    ]:
        try:
            if _has_table(inspector, "stock_lot_allocations") and not _has_index(inspector, "stock_lot_allocations", idx_name):
                op.create_index(idx_name, "stock_lot_allocations", cols, unique=unique)
        except Exception:
            pass

    # Seed legacy lots from current warehouse_stock (best-effort)
    if not (_has_table(inspector, "warehouse_stock") and _has_table(inspector, "stock_items") and _has_table(inspector, "stock_lots")):
        return

    # We only seed when there are no lots yet.
    try:
        existing_any = bind.execute(sa.text("SELECT 1 FROM stock_lots LIMIT 1")).scalar()
        if existing_any is not None:
            return
    except Exception:
        # If we can't check, don't seed.
        return

    # Use SQL to seed quickly across dialects.
    # created_at is set to current_timestamp (SQLite/Postgres compatible).
    try:
        bind.execute(
            sa.text(
                """
                INSERT INTO stock_lots (stock_item_id, warehouse_id, lot_type, unit_cost, quantity_on_hand, created_at, created_by, source_movement_id, notes)
                SELECT
                    ws.stock_item_id,
                    ws.warehouse_id,
                    'normal' AS lot_type,
                    COALESCE(si.default_cost, 0) AS unit_cost,
                    ws.quantity_on_hand AS quantity_on_hand,
                    CURRENT_TIMESTAMP AS created_at,
                    NULL AS created_by,
                    NULL AS source_movement_id,
                    'Legacy seed from warehouse_stock' AS notes
                FROM warehouse_stock ws
                JOIN stock_items si ON si.id = ws.stock_item_id
                WHERE ws.quantity_on_hand > 0
                """
            )
        )
    except Exception:
        # Best-effort; if it fails, runtime will auto-create legacy lots when needed.
        pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop allocations first (FK dependency)
    if _has_table(inspector, "stock_lot_allocations"):
        for idx in [
            "ix_stock_lot_allocations_move_lot",
            "ix_stock_lot_allocations_created_at",
            "ix_stock_lot_allocations_stock_lot_id",
            "ix_stock_lot_allocations_stock_movement_id",
        ]:
            try:
                if _has_index(inspector, "stock_lot_allocations", idx):
                    op.drop_index(idx, table_name="stock_lot_allocations")
            except Exception:
                pass
        try:
            op.drop_table("stock_lot_allocations")
        except Exception:
            pass

    if _has_table(inspector, "stock_lots"):
        for idx in [
            "ix_stock_lots_item_wh_cost_type",
            "ix_stock_lots_source_movement_id",
            "ix_stock_lots_created_by",
            "ix_stock_lots_created_at",
            "ix_stock_lots_lot_type",
            "ix_stock_lots_warehouse_id",
            "ix_stock_lots_stock_item_id",
        ]:
            try:
                if _has_index(inspector, "stock_lots", idx):
                    op.drop_index(idx, table_name="stock_lots")
            except Exception:
                pass
        try:
            op.drop_table("stock_lots")
        except Exception:
            pass

