"""Add tenant billing and Stripe webhook idempotency

Revision ID: 102_add_tenant_billing_and_stripe_events
Revises: 101_add_tenant_id_to_core_tables
Create Date: 2026-01-03
"""

from alembic import op
import sqlalchemy as sa


revision = "102_add_tenant_billing_and_stripe_events"
down_revision = "101_add_tenant_id_to_core_tables"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tenant_billing" not in inspector.get_table_names():
        op.create_table(
            "tenant_billing",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tier", sa.String(length=20), nullable=False, server_default=sa.text("'basic'")),
            sa.Column("seat_quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("stripe_customer_id", sa.String(length=64), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(length=64), nullable=True),
            sa.Column("stripe_subscription_item_id", sa.String(length=64), nullable=True),
            sa.Column("stripe_price_id", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tenant_id", name="uq_tenant_billing_tenant_id"),
            sa.UniqueConstraint("stripe_subscription_id", name="uq_tenant_billing_stripe_subscription_id"),
        )
        op.create_index("ix_tenant_billing_tenant_id", "tenant_billing", ["tenant_id"], unique=False)
        op.create_index("ix_tenant_billing_stripe_customer_id", "tenant_billing", ["stripe_customer_id"], unique=False)
        op.create_index("ix_tenant_billing_stripe_subscription_id", "tenant_billing", ["stripe_subscription_id"], unique=False)

    inspector = sa.inspect(bind)
    if "stripe_events" not in inspector.get_table_names():
        op.create_table(
            "stripe_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("stripe_event_id", sa.String(length=128), nullable=False),
            sa.Column("event_type", sa.String(length=128), nullable=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.UniqueConstraint("stripe_event_id", name="uq_stripe_events_event_id"),
        )
        op.create_index("ix_stripe_events_stripe_event_id", "stripe_events", ["stripe_event_id"], unique=True)
        op.create_index("ix_stripe_events_event_type", "stripe_events", ["event_type"], unique=False)
        op.create_index("ix_stripe_events_tenant_id", "stripe_events", ["tenant_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "stripe_events" in inspector.get_table_names():
        try:
            op.drop_index("ix_stripe_events_tenant_id", table_name="stripe_events")
        except Exception:
            pass
        try:
            op.drop_index("ix_stripe_events_event_type", table_name="stripe_events")
        except Exception:
            pass
        try:
            op.drop_index("ix_stripe_events_stripe_event_id", table_name="stripe_events")
        except Exception:
            pass
        op.drop_table("stripe_events")

    inspector = sa.inspect(bind)
    if "tenant_billing" in inspector.get_table_names():
        try:
            op.drop_index("ix_tenant_billing_stripe_subscription_id", table_name="tenant_billing")
        except Exception:
            pass
        try:
            op.drop_index("ix_tenant_billing_stripe_customer_id", table_name="tenant_billing")
        except Exception:
            pass
        try:
            op.drop_index("ix_tenant_billing_tenant_id", table_name="tenant_billing")
        except Exception:
            pass
        op.drop_table("tenant_billing")

