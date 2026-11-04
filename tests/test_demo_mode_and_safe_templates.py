"""Demo account privileges and sandboxed DB template rendering."""

import os
import tempfile
import uuid

import pytest
from jinja2.sandbox import SecurityError

from app import create_app, db, init_database
from app.models import Settings, User
from app.utils.permissions_seed import seed_permissions, seed_roles
from app.utils.safe_template_render import render_sandboxed_string


@pytest.mark.unit
def test_render_sandboxed_string_allows_invoice_variables():
    from types import SimpleNamespace

    invoice = SimpleNamespace(invoice_number="INV-42", items=[])
    out = render_sandboxed_string(
        "<p>{{ invoice.invoice_number }}</p>",
        autoescape=True,
        invoice=invoice,
    )
    assert "INV-42" in out


@pytest.mark.unit
def test_render_sandboxed_string_blocks_typical_ssti():
    payload = "{{ ().__class__.__bases__[0].__subclasses__() }}"
    with pytest.raises(SecurityError):
        render_sandboxed_string(payload, autoescape=True)


@pytest.mark.unit
def test_demo_mode_init_creates_non_admin_user(app_config):
    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_demo_user_{uuid.uuid4().hex}.sqlite")
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"
    config["DEMO_MODE"] = True
    config["DEMO_USERNAME"] = "pubdemo"
    config["DEMO_PASSWORD"] = "not-the-default"
    app = create_app(config)
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            assert seed_permissions() is True
            assert seed_roles() is True
            if not Settings.query.first():
                db.session.add(Settings())
                db.session.commit()
        # init_database opens its own app context; avoid nesting (breaks SQLAlchemy session).
        init_database(app)
        with app.app_context():
            u = User.query.filter_by(username="pubdemo").first()
            assert u is not None
            assert u.role == "user"
            assert not any(r.name in ("admin", "super_admin") for r in u.roles)
            assert u.has_permission("manage_settings") is False
    finally:
        try:
            os.remove(unique_db_path)
        except OSError:
            pass


@pytest.mark.unit
def test_demo_mode_init_downgrades_legacy_admin_demo_user(app_config):
    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_demo_upgrade_{uuid.uuid4().hex}.sqlite")
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"
    config["DEMO_MODE"] = True
    config["DEMO_USERNAME"] = "legacydemo"
    config["DEMO_PASSWORD"] = "x"
    app = create_app(config)
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            assert seed_permissions() is True
            assert seed_roles() is True
            if not Settings.query.first():
                db.session.add(Settings())
                db.session.commit()
            from app.models import Role

            admin_role = Role.query.filter_by(name="admin").first()
            assert admin_role is not None
            legacy = User(username="legacydemo", role="admin")
            legacy.is_active = True
            legacy.set_password("x")
            legacy.roles.append(admin_role)
            db.session.add(legacy)
            db.session.commit()

        init_database(app)
        with app.app_context():
            u = User.query.filter_by(username="legacydemo").first()
            assert u.role == "user"
            assert not any(r.name in ("admin", "super_admin") for r in u.roles)
            assert u.has_permission("manage_settings") is False
    finally:
        try:
            os.remove(unique_db_path)
        except OSError:
            pass


@pytest.mark.unit
def test_demo_mode_seeds_sample_data_and_skips_setup(app_config, tmp_path, monkeypatch):
    monkeypatch.setenv("INSTALLATION_CONFIG_DIR", str(tmp_path / "install"))
    # Force a fresh InstallationConfig singleton for this path
    import app.utils.installation as installation_mod

    installation_mod._installation_config = None
    installation_mod._installation_config_path = None

    unique_db_path = os.path.join(tempfile.gettempdir(), f"pytest_demo_seed_{uuid.uuid4().hex}.sqlite")
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"
    config["DEMO_MODE"] = True
    config["DEMO_USERNAME"] = "seeddemo"
    config["DEMO_PASSWORD"] = "seedpass"
    app = create_app(config)
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            assert seed_permissions() is True
            assert seed_roles() is True
            if not Settings.query.first():
                db.session.add(Settings())
                db.session.commit()
        init_database(app)
        with app.app_context():
            from app.models import Client, Project, TimeEntry
            from app.utils.installation import get_installation_config
            from app.utils.seed_demo_data import seed_demo_sample_data

            assert get_installation_config().is_setup_complete() is True
            assert Client.query.count() >= 1
            assert Project.query.count() >= 1
            assert TimeEntry.query.count() >= 1
            # Idempotent
            assert seed_demo_sample_data(app) is True
            assert Project.query.count() >= 1

        client = app.test_client()
        # /setup must not trap demo visitors
        resp = client.get("/setup", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/login" in (resp.headers.get("Location") or "")
        # Root must not redirect to setup under DEMO_MODE
        resp_root = client.get("/", follow_redirects=False)
        assert resp_root.status_code in (200, 302, 303)
        assert "/setup" not in (resp_root.headers.get("Location") or "")
    finally:
        installation_mod._installation_config = None
        installation_mod._installation_config_path = None
        try:
            os.remove(unique_db_path)
        except OSError:
            pass
