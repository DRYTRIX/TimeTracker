"""HTML invoice templates: templates, versions, the default in Settings, the frozen template on invoices,
and a template and logo on legal entities.

Revision ID: 217_invoice_html_templates
Revises: 216_add_client_entities
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "217_invoice_html_templates"
down_revision = "216_add_client_entities"
branch_labels = None
depends_on = None


def _has_table(inspector, name):
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "invoice_html_templates"):
        op.create_table(
            "invoice_html_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("html", sa.Text(), nullable=False, server_default=""),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="created"),
            sa.Column("current_version_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_invoice_html_templates_name", "invoice_html_templates", ["name"])
        op.create_index("ix_invoice_html_templates_deleted_at", "invoice_html_templates", ["deleted_at"])

    if not _has_table(inspector, "invoice_html_template_versions"):
        op.create_table(
            "invoice_html_template_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "template_id",
                sa.Integer(),
                sa.ForeignKey("invoice_html_templates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("html", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("template_id", "number", name="uq_invoice_html_tpl_version"),
        )
        op.create_index(
            "ix_invoice_html_template_versions_template_id", "invoice_html_template_versions", ["template_id"]
        )
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_invoice_html_tpl_current_version",
                "invoice_html_templates",
                "invoice_html_template_versions",
                ["current_version_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_column(inspector, "settings", "invoice_pdf_template"):
        op.add_column(
            "settings",
            sa.Column("invoice_pdf_template", sa.String(length=64), nullable=False, server_default="visual"),
        )

    if _has_table(inspector, "billing_entities"):
        if not _has_column(inspector, "billing_entities", "pdf_template"):
            op.add_column("billing_entities", sa.Column("pdf_template", sa.String(length=64), nullable=True))
        if not _has_column(inspector, "billing_entities", "logo_filename"):
            op.add_column("billing_entities", sa.Column("logo_filename", sa.String(length=255), nullable=True))

    if not _has_column(inspector, "invoices", "pdf_template_ref"):
        op.add_column("invoices", sa.Column("pdf_template_ref", sa.String(length=64), nullable=True))
    if not _has_column(inspector, "invoices", "pdf_template_version_id"):
        with op.batch_alter_table("invoices") as batch:
            batch.add_column(sa.Column("pdf_template_version_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_invoices_pdf_template_version",
                "invoice_html_template_versions",
                ["pdf_template_version_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "invoices", "pdf_template_version_id"):
        with op.batch_alter_table("invoices") as batch:
            batch.drop_constraint("fk_invoices_pdf_template_version", type_="foreignkey")
            batch.drop_column("pdf_template_version_id")
    if _has_column(inspector, "invoices", "pdf_template_ref"):
        with op.batch_alter_table("invoices") as batch:
            batch.drop_column("pdf_template_ref")
    for column in ("logo_filename", "pdf_template"):
        if _has_column(inspector, "billing_entities", column):
            with op.batch_alter_table("billing_entities") as batch:
                batch.drop_column(column)
    if _has_column(inspector, "settings", "invoice_pdf_template"):
        with op.batch_alter_table("settings") as batch:
            batch.drop_column("invoice_pdf_template")
    if _has_table(inspector, "invoice_html_templates") and bind.dialect.name != "sqlite":
        try:
            op.drop_constraint("fk_invoice_html_tpl_current_version", "invoice_html_templates", type_="foreignkey")
        except Exception:
            pass
    if _has_table(inspector, "invoice_html_template_versions"):
        op.drop_table("invoice_html_template_versions")
    if _has_table(inspector, "invoice_html_templates"):
        op.drop_table("invoice_html_templates")
