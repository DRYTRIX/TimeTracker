"""Add geofences and workday session location fields.

Revision ID: 191_add_geofences
Revises: 190_add_shared_report_links
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "191_add_geofences"
down_revision = "190_add_shared_report_links"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "geofences" not in tables:
        op.create_table(
            "geofences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("lng", sa.Float(), nullable=False),
            sa.Column("radius_m", sa.Float(), nullable=False, server_default="100"),
            sa.Column("address", sa.String(500), nullable=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("policy", sa.String(10), nullable=False, server_default="log"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_geofences_project_id", "geofences", ["project_id"])

    ws_cols = {c["name"] for c in inspector.get_columns("workday_sessions")}
    if "latitude" not in ws_cols:
        op.add_column("workday_sessions", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in ws_cols:
        op.add_column("workday_sessions", sa.Column("longitude", sa.Float(), nullable=True))
    if "accuracy_m" not in ws_cols:
        op.add_column("workday_sessions", sa.Column("accuracy_m", sa.Float(), nullable=True))
    if "geofence_id" not in ws_cols:
        op.add_column("workday_sessions", sa.Column("geofence_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_workday_sessions_geofence_id",
            "workday_sessions",
            "geofences",
            ["geofence_id"],
            ["id"],
        )
    if "geofence_status" not in ws_cols:
        op.add_column("workday_sessions", sa.Column("geofence_status", sa.String(20), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    ws_cols = {c["name"] for c in inspector.get_columns("workday_sessions")}

    if "geofence_status" in ws_cols:
        op.drop_column("workday_sessions", "geofence_status")
    if "geofence_id" in ws_cols:
        op.drop_constraint("fk_workday_sessions_geofence_id", "workday_sessions", type_="foreignkey")
        op.drop_column("workday_sessions", "geofence_id")
    if "accuracy_m" in ws_cols:
        op.drop_column("workday_sessions", "accuracy_m")
    if "longitude" in ws_cols:
        op.drop_column("workday_sessions", "longitude")
    if "latitude" in ws_cols:
        op.drop_column("workday_sessions", "latitude")

    if "geofences" in inspector.get_table_names():
        op.drop_index("ix_geofences_project_id", table_name="geofences")
        op.drop_table("geofences")
