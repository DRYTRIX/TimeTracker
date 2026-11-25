"""Migration 218: project costs get category_id linked to expense categories."""

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
    "218_project_cost_expense_categories.py",
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_218", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine, fn):
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            fn()


@pytest.fixture
def engine():
    url = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    path = None
    if not url:
        path = os.path.join(tempfile.gettempdir(), f"migration_218_{uuid.uuid4().hex}.sqlite")
        url = f"sqlite:///{path}"
    engine = sa.create_engine(url)
    meta = sa.MetaData()
    sa.Table(
        "expense_categories",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("code", sa.String(20), nullable=True, unique=True),
        sa.Column("budget_threshold_percent", sa.Integer, nullable=False),
        sa.Column("requires_receipt", sa.Boolean, nullable=False),
        sa.Column("requires_approval", sa.Boolean, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    for table in ("project_costs", "recurring_project_costs"):
        sa.Table(
            table,
            meta,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
        )
    meta.drop_all(engine)
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO expense_categories (name, code, budget_threshold_percent, requires_receipt, "
                "requires_approval, is_active, created_at, updated_at) "
                "VALUES ('Travel', 'TRAVEL', 80, :true, :true, :true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"true": True},
        )
        conn.execute(
            sa.text(
                "INSERT INTO project_costs (description, category) "
                "VALUES ('Train', 'travel'), ('Wood', 'Materials'), ('Odd one', 'custom-thing')"
            )
        )
        conn.execute(sa.text("INSERT INTO recurring_project_costs (description, category) VALUES ('Fees', 'travel')"))
    yield engine
    meta.drop_all(engine)
    engine.dispose()
    if path and os.path.exists(path):
        os.remove(path)


def _categories(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, name, code, requires_receipt, requires_approval FROM expense_categories")
        ).fetchall()
    return {row.name: row for row in rows}


def _cost_links(engine, table="project_costs"):
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"SELECT category, category_id FROM {table} ORDER BY id")).fetchall()
    return [(row.category, row.category_id) for row in rows]


def test_upgrade_links_costs_and_creates_missing_categories(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)

    categories = _categories(engine)
    # Found by code (case-insensitive), not duplicated
    assert [name for name in categories if name.lower() == "travel"] == ["Travel"]
    # Created from strings in use
    # A string from the standard set keeps the lowercase code
    assert categories["Materials"].code == "materials"
    assert categories["Custom-thing"].code == "custom-thing"
    created = categories["Custom-thing"]
    assert not created.requires_receipt
    assert not created.requires_approval
    # The standard set exists even when unused
    for name in ("Services", "Equipment", "Software", "Other"):
        assert name in categories

    assert _cost_links(engine) == [
        ("travel", categories["Travel"].id),
        ("Materials", categories["Materials"].id),
        ("custom-thing", categories["Custom-thing"].id),
    ]
    assert _cost_links(engine, "recurring_project_costs") == [("travel", categories["Travel"].id)]


def test_upgrade_downgrade_upgrade_is_clean(engine):
    migration = _load_migration()
    _run(engine, migration.upgrade)
    first = _categories(engine)

    _run(engine, migration.downgrade)
    inspector = sa.inspect(engine)
    for table in ("project_costs", "recurring_project_costs"):
        assert "category_id" not in {c["name"] for c in inspector.get_columns(table)}
    assert _cost_links_legacy(engine) == ["travel", "Materials", "custom-thing"]

    _run(engine, migration.upgrade)
    second = _categories(engine)
    assert {name: row.id for name, row in second.items()} == {name: row.id for name, row in first.items()}
    assert [cid for _, cid in _cost_links(engine)] == [
        first["Travel"].id,
        first["Materials"].id,
        first["Custom-thing"].id,
    ]

    # Running upgrade again on an upgraded schema changes nothing
    _run(engine, migration.upgrade)
    assert len(_categories(engine)) == len(first)


def _cost_links_legacy(engine):
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(sa.text("SELECT category FROM project_costs ORDER BY id"))]
