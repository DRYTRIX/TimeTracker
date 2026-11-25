"""Migration 220: line kind and edited flags, invoice layout and period, project defaults.

Runs on SQLite by default; set MIGRATION_TEST_DATABASE_URL to run it on PostgreSQL.
"""

import importlib.util
import os
import tempfile
import uuid

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

pytestmark = [pytest.mark.unit, pytest.mark.database]

MIGRATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "migrations",
    "versions",
    "220_add_invoice_hours_layout.py",
)

NEW_COLUMNS = {
    "invoice_items": {"kind", "description_edited", "quantity_edited", "price_edited"},
    "invoices": {"period_start", "period_end", "hours_layout", "line_template"},
    "projects": {"last_hours_layout", "last_line_template"},
}


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_220", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine, fn):
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            fn()


def _columns(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


@pytest.fixture
def engine():
    url = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    path = None
    if not url:
        path = os.path.join(tempfile.gettempdir(), f"migration_220_{uuid.uuid4().hex}.sqlite")
        url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table("projects", meta, sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(200)))
    sa.Table(
        "invoices",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_number", sa.String(50)),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
    )
    sa.Table(
        "invoice_items",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("time_entry_ids", sa.Text),
    )
    sa.Table(
        "invoice_time_links",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("time_entry_id", sa.Integer, nullable=False),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("invoice_item_id", sa.Integer, sa.ForeignKey("invoice_items.id"), nullable=True),
        sa.Column("released_at", sa.DateTime, nullable=True),
    )
    meta.drop_all(engine)
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO projects (id, name) VALUES (1, 'P')"))
        conn.execute(
            sa.text("INSERT INTO invoices (id, invoice_number, project_id) VALUES (1, 'A-1', 1), (2, 'A-2', 1)")
        )
        conn.execute(
            sa.text(
                "INSERT INTO invoice_items (id, invoice_id, description, time_entry_ids) VALUES "
                "(1, 1, 'Hours', '10,11'), (2, 1, 'Fixed fee', NULL), (3, 2, 'Cancelled hours', '12')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO invoice_time_links (time_entry_id, invoice_id, invoice_item_id, released_at) VALUES "
                "(10, 1, 1, NULL), (11, 1, 1, NULL), (12, 2, 3, CURRENT_TIMESTAMP), (13, 1, NULL, NULL)"
            )
        )
    yield engine
    meta.drop_all(engine)
    engine.dispose()
    if path and os.path.exists(path):
        os.remove(path)


def test_upgrade_adds_columns_and_marks_linked_lines_as_time(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)

    for table, columns in NEW_COLUMNS.items():
        assert columns <= _columns(engine, table), table
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, kind, description_edited, quantity_edited, price_edited FROM invoice_items ORDER BY id")
        ).fetchall()
        layout = conn.execute(sa.text("SELECT hours_layout, line_template, period_start FROM invoices")).fetchall()
        project = conn.execute(sa.text("SELECT last_hours_layout, last_line_template FROM projects")).fetchall()
    assert [(r[0], r[1], bool(r[2]), bool(r[3]), bool(r[4])) for r in rows] == [
        (1, "time", False, False, False),
        (2, "manual", False, False, False),
        (3, "time", False, False, False),  # a released link still makes it a time line
    ]
    assert all(row == (None, None, None) for row in layout)
    assert project == [(None, None)]

    # Running it twice changes nothing
    _run(engine, migration.upgrade)
    assert NEW_COLUMNS["invoice_items"] <= _columns(engine, "invoice_items")


def test_new_rows_default_to_manual_and_not_edited(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO invoice_items (id, invoice_id, description) VALUES (9, 1, 'New')"))
        row = conn.execute(
            sa.text("SELECT kind, description_edited, quantity_edited, price_edited FROM invoice_items WHERE id = 9")
        ).one()
    assert (row[0], bool(row[1]), bool(row[2]), bool(row[3])) == ("manual", False, False, False)


def test_downgrade_drops_the_columns_and_keeps_the_data(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)
    _run(engine, migration.downgrade)
    for table, columns in NEW_COLUMNS.items():
        assert not (columns & _columns(engine, table)), table
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT count(*) FROM invoice_items")).scalar() == 3
        assert conn.execute(sa.text("SELECT count(*) FROM invoice_time_links")).scalar() == 4
