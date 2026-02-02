import pytest

from app import db
from app.models import Role, Settings, User
from app.utils.module_registry import ModuleRegistry


@pytest.mark.unit
def test_module_registry_hides_module_if_all_roles_hide(app, user):
    """If all assigned roles hide a module, ModuleRegistry should disable it."""
    ModuleRegistry.initialize_defaults()
    settings = Settings.get_settings()

    r = Role(name="hide_analytics_role", hidden_module_ids=["analytics"])
    db.session.add(r)
    db.session.commit()

    user.add_role(r)
    db.session.commit()

    assert ModuleRegistry.is_enabled("analytics", settings, user) is False


@pytest.mark.unit
def test_module_registry_allows_module_if_any_role_allows(app, user):
    """If any assigned role allows a module, ModuleRegistry should keep it enabled."""
    ModuleRegistry.initialize_defaults()
    settings = Settings.get_settings()

    r_hide = Role(name="hide_analytics_role", hidden_module_ids=["analytics"])
    r_allow = Role(name="allow_all_role", hidden_module_ids=[])
    db.session.add_all([r_hide, r_allow])
    db.session.commit()

    user.add_role(r_hide)
    user.add_role(r_allow)
    db.session.commit()

    assert ModuleRegistry.is_enabled("analytics", settings, user) is True


@pytest.mark.integration
def test_module_enabled_decorator_blocks_hidden_module_route(app, user):
    """A hidden module should return 403 for an authenticated user (route decorator)."""
    r = Role(name="hide_analytics_role", hidden_module_ids=["analytics"])
    db.session.add(r)
    db.session.commit()

    user.add_role(r)
    db.session.commit()

    from flask_login import login_user
    from werkzeug.exceptions import Forbidden
    from app.routes.analytics import analytics_dashboard

    with app.test_request_context("/analytics"):
        login_user(user, remember=True)
        with pytest.raises(Forbidden):
            analytics_dashboard()

