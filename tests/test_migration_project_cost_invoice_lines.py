"""Migration 221: project costs know their invoice line and their recurring cost.

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
    "221_add_project_cost_invoice_lines.py",
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_221", MIGRATION_PATH)
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
        path = os.path.join(tempfile.gettempdir(), f"migration_221_{uuid.uuid4().hex}.sqlite")
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
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="manual"),
    )
    sa.Table(
        "expense_categories", meta, sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(100))
    )
    sa.Table(
        "recurring_project_costs",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("description", sa.String(500)),
    )
    sa.Table(
        "project_costs",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("expense_categories.id"), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=True),
    )
    meta.drop_all(engine)
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO projects (id, name) VALUES (1, 'P')"))
        conn.execute(sa.text("INSERT INTO expense_categories (id, name) VALUES (1, 'Software')"))
        conn.execute(
            sa.text("INSERT INTO invoices (id, invoice_number, project_id) VALUES (1, 'A-1', 1), (2, 'A-2', 1)")
        )
        conn.execute(
            sa.text(
                "INSERT INTO invoice_items (id, invoice_id, description, unit_price, kind) VALUES "
                "(1, 1, 'Design', 400, 'time'), "
                "(2, 1, 'Looker (Software)', 200, 'manual'), "
                "(3, 1, 'Hosting (travel)', 45, 'manual'), "
                "(4, 2, 'Renamed by hand', 99, 'manual'), "
                "(5, 1, 'Looker (Software)', 200, 'manual'), "
                "(6, 2, 'Tools (software)', 30, 'manual')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO project_costs (id, project_id, description, category, category_id, amount, invoice_id) "
                "VALUES "
                "(1, 1, 'Looker', 'software', 1, 200, 1), "  # category by id: matches line 2
                "(2, 1, 'Hosting', 'travel', NULL, 45, 1), "  # legacy category string: matches line 3
                "(3, 1, 'Metabase', 'software', 1, 99, 2), "  # its line was renamed: stays without a line
                "(4, 1, 'Looker', 'software', 1, 200, 1), "  # a second cost with the same text takes line 5
                "(5, 1, 'Unbilled', 'software', 1, 10, NULL), "
                # written before costs had catalog categories: the line names the old category text
                "(6, 1, 'Tools', 'software', 1, 30, 2)"
            )
        )
    yield engine
    meta.drop_all(engine)
    engine.dispose()
    if path and os.path.exists(path):
        os.remove(path)


def test_upgrade_links_old_costs_to_their_line(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)

    assert {"invoice_item_id", "recurring_cost_id"} <= _columns(engine, "project_costs")
    assert "costs_layout" in _columns(engine, "invoices")
    with engine.connect() as conn:
        costs = dict(conn.execute(sa.text("SELECT id, invoice_item_id FROM project_costs ORDER BY id")).fetchall())
        kinds = dict(conn.execute(sa.text("SELECT id, kind FROM invoice_items ORDER BY id")).fetchall())
    assert costs == {1: 2, 2: 3, 3: None, 4: 5, 5: None, 6: 6}
    assert kinds == {1: "time", 2: "cost", 3: "cost", 4: "manual", 5: "cost", 6: "cost"}

    # Running it twice changes nothing
    _run(engine, migration.upgrade)
    with engine.connect() as conn:
        again = dict(conn.execute(sa.text("SELECT id, invoice_item_id FROM project_costs ORDER BY id")).fetchall())
    assert again == costs


def test_downgrade_drops_the_columns_and_keeps_the_rows(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)
    _run(engine, migration.downgrade)
    assert not ({"invoice_item_id", "recurring_cost_id"} & _columns(engine, "project_costs"))
    assert "costs_layout" not in _columns(engine, "invoices")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT count(*) FROM project_costs")).scalar() == 6
        assert conn.execute(sa.text("SELECT count(*) FROM invoice_items")).scalar() == 6
