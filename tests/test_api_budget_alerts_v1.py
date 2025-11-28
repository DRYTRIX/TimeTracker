import pytest

from app import create_app, db
from app.models import User, Project, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_budget_alerts.sqlite",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    u = User(username="adminuser", email="admin@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, admin_user):
    token, plain = ApiToken.create_token(
        user_id=admin_user.id, name="Budget Token", scopes="admin:all,read:budget_alerts,write:budget_alerts"
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def project(app):
    p = Project(name="BA Project", status="active")
    db.session.add(p)
    db.session.commit()
    return p


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_budget_alerts(client, api_token, project):
    # create alert
    payload = {
        "project_id": project.id,
        "alert_type": "warning_80",
        "budget_consumed_percent": 80.0,
        "budget_amount": 1000.0,
        "consumed_amount": 800.0,
        "message": "80% consumed",
    }
    r = client.post("/api/v1/budget-alerts", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    alert_id = r.get_json()["alert"]["id"]

    # list
    r = client.get("/api/v1/budget-alerts", headers=_auth(api_token))
    assert r.status_code == 200
    assert len(r.get_json()["alerts"]) >= 1

    # acknowledge
    r = client.post(f"/api/v1/budget-alerts/{alert_id}/ack", headers=_auth(api_token))
    assert r.status_code == 200
