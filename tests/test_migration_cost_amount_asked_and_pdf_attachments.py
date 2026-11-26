"""Migration 222: recurring costs that ask for their amount, receipts and bills attached to the invoice PDF.

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
    "222_add_cost_amount_asked_and_pdf_attachments.py",
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_222", MIGRATION_PATH)
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
        path = os.path.join(tempfile.gettempdir(), f"migration_222_{uuid.uuid4().hex}.sqlite")
        url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table(
        "invoices", meta, sa.Column("id", sa.Integer, primary_key=True), sa.Column("invoice_number", sa.String(50))
    )
    sa.Table(
        "recurring_project_costs",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("description", sa.String(500)),
        sa.Column("next_run_date", sa.Date),
    )
    sa.Table(
        "project_costs",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cost_date", sa.Date),
        sa.Column("recurring_cost_id", sa.Integer),
    )
    meta.drop_all(engine)
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO invoices (id, invoice_number) VALUES (1, 'A-1')"))
        conn.execute(
            sa.text(
                "INSERT INTO recurring_project_costs (id, description, next_run_date) VALUES "
                "(1, 'Hosting', '2026-12-04'), (2, 'Domain', '2027-03-01')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO project_costs (id, cost_date, recurring_cost_id) VALUES "
                "(1, '2026-10-04', 1), (2, '2026-09-04', 1), (3, '2026-11-04', NULL)"
            )
        )
    yield engine
    meta.drop_all(engine)
    engine.dispose()
    if path and os.path.exists(path):
        os.remove(path)


def test_upgrade_adds_the_flags_off_and_downgrade_drops_them(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)
    _run(engine, migration.upgrade)  # twice: nothing more
    assert {"attach_receipts", "attach_bills"} <= _columns(engine, "invoices")
    assert "ask_amount" in _columns(engine, "recurring_project_costs")
    with engine.connect() as conn:
        assert [bool(v) for v in conn.execute(sa.text("SELECT attach_receipts, attach_bills FROM invoices")).one()] == [
            False,
            False,
        ]
        assert not conn.execute(sa.text("SELECT ask_amount FROM recurring_project_costs")).scalar()
        # From its first cost; without costs, from its next run date
        starts = dict(
            conn.execute(sa.text("SELECT id, start_date FROM recurring_project_costs ORDER BY id")).fetchall()
        )
        assert {k: str(v) for k, v in starts.items()} == {1: "2026-09-04", 2: "2027-03-01"}

    _run(engine, migration.downgrade)
    assert not ({"attach_receipts", "attach_bills"} & _columns(engine, "invoices"))
    assert not ({"ask_amount", "start_date"} & _columns(engine, "recurring_project_costs"))
