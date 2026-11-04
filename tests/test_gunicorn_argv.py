"""Gunicorn argv helpers used by docker/start-fixed.py (copied to /app/start.py)."""

import importlib.util
from pathlib import Path

import pytest

_START_FIXED = Path(__file__).resolve().parents[1] / "docker" / "start-fixed.py"


@pytest.fixture(scope="module")
def gunicorn_helpers():
    spec = importlib.util.spec_from_file_location("start_fixed_gunicorn", _START_FIXED)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_max_requests_disabled_when_port_set(gunicorn_helpers):
    assert gunicorn_helpers.resolve_gunicorn_max_requests({"PORT": "10000"}) == 0
    argv = gunicorn_helpers.build_gunicorn_argv("10000", max_requests=0)
    assert "--max-requests" not in argv
    assert "--max-requests-jitter" not in argv
    assert "0.0.0.0:10000" in argv


def test_max_requests_default_when_port_unset(gunicorn_helpers):
    assert gunicorn_helpers.resolve_gunicorn_max_requests({}) == 1000
    argv = gunicorn_helpers.build_gunicorn_argv("8080", max_requests=1000, max_requests_jitter=100)
    assert argv[argv.index("--max-requests") + 1] == "1000"
    assert argv[argv.index("--max-requests-jitter") + 1] == "100"


def test_explicit_gunicorn_max_requests_overrides_port(gunicorn_helpers):
    env = {"PORT": "10000", "GUNICORN_MAX_REQUESTS": "5000", "GUNICORN_MAX_REQUESTS_JITTER": "50"}
    assert gunicorn_helpers.resolve_gunicorn_max_requests(env) == 5000
    jitter = gunicorn_helpers.resolve_gunicorn_max_requests_jitter(env, max_requests=5000)
    assert jitter == 50
