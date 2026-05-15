"""Per-user custom theme preferences.

Adds five nullable columns to the ``users`` table so each user can pick
from the built-in themes catalogue (``ThemeService.BUILT_IN_THEMES``) and
optionally customise the accent colour, sidebar style, font size and
corner radius. All columns are nullable with sensible string defaults so
the migration is fully backwards-compatible: users that have not yet
picked a theme keep seeing the existing TimeTracker look (``"default"``)
without any visual change.

Columns added:

* ``theme_name``          – String(50)  default ``"default"``
* ``theme_accent_color``  – String(7)   nullable, hex ``#RRGGBB``
* ``theme_sidebar_style`` – String(20)  default ``"default"``
                            allowed: ``default``/``compact``/``minimal``
* ``theme_font_size``     – String(10)  default ``"base"``
                            allowed: ``sm``/``base``/``lg``
* ``theme_border_radius`` – String(10)  default ``"default"``
                            allowed: ``none``/``default``/``full``

Each column is added defensively – we inspect the existing schema first
and skip the ``ADD COLUMN`` if it has already been applied (e.g. on a
database that was pre-seeded, or where this migration was run partially
in a previous deployment).

Revision ID: 156_add_user_theme_columns
Revises: 155_add_integration_columns
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "156_add_user_theme_columns"
down_revision = "155_add_integration_columns"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        # Nothing to do on an empty schema; the table itself will be
        # created by the initial schema migration which already includes
        # these columns via the model on a fresh install.
        return

    if not _has_column(inspector, "users", "theme_name"):
        op.add_column(
            "users",
            sa.Column(
                "theme_name",
                sa.String(length=50),
                nullable=True,
                server_default="default",
            ),
        )

    # Refresh the inspector between adds so the SQLite/Postgres dialects
    # both see freshly added columns.
    inspector = inspect(bind)
    if not _has_column(inspector, "users", "theme_accent_color"):
        op.add_column(
            "users",
            sa.Column("theme_accent_color", sa.String(length=7), nullable=True),
        )

    inspector = inspect(bind)
    if not _has_column(inspector, "users", "theme_sidebar_style"):
        op.add_column(
            "users",
            sa.Column(
                "theme_sidebar_style",
                sa.String(length=20),
                nullable=True,
                server_default="default",
            ),
        )

    inspector = inspect(bind)
    if not _has_column(inspector, "users", "theme_font_size"):
        op.add_column(
            "users",
            sa.Column(
                "theme_font_size",
                sa.String(length=10),
                nullable=True,
                server_default="base",
            ),
        )

    inspector = inspect(bind)
    if not _has_column(inspector, "users", "theme_border_radius"):
        op.add_column(
            "users",
            sa.Column(
                "theme_border_radius",
                sa.String(length=10),
                nullable=True,
                server_default="default",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        return

    for column in (
        "theme_border_radius",
        "theme_font_size",
        "theme_sidebar_style",
        "theme_accent_color",
        "theme_name",
    ):
        inspector = inspect(bind)
        if _has_column(inspector, "users", column):
            try:
                op.drop_column("users", column)
            except Exception:
                # Best-effort downgrade; ignore failures (e.g. SQLite
                # without batch mode) so reverting other parts of the
                # release does not break.
                pass
