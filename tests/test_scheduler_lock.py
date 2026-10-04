"""Unit tests for scheduler leadership lock helper."""

from types import SimpleNamespace

import pytest

from app.utils.scheduler_lock import try_acquire_scheduler_leadership

pytestmark = [pytest.mark.unit]


def test_try_acquire_scheduler_leadership_testing_returns_false():
    app = SimpleNamespace(
        config={"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///unused.db"},
        extensions={},
    )
    assert try_acquire_scheduler_leadership(app) is False


def test_try_acquire_scheduler_leadership_sqlite_returns_true():
    app = SimpleNamespace(
        config={"TESTING": False, "SQLALCHEMY_DATABASE_URI": "sqlite:///tmp/pytest.db"},
        extensions={},
    )
    assert try_acquire_scheduler_leadership(app) is True


def test_try_acquire_scheduler_leadership_sqlite_memory_returns_true():
    app = SimpleNamespace(
        config={"TESTING": False, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"},
        extensions={},
    )
    assert try_acquire_scheduler_leadership(app) is True
