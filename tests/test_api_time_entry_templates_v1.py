import pytest

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_templates.sqlite",
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
def user(app):
    u = User(username="tpluser", email="tpl@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id, name="Templates Token", scopes="read:time_entries,write:time_entries"
    )
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_templates_crud(client, api_token):
    # list empty
    r = client.get("/api/v1/time-entry-templates", headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()["templates"] == []

    # create
    payload = {"name": "Quick dev", "default_duration_minutes": 120, "default_notes": "dev"}
    r = client.post("/api/v1/time-entry-templates", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    t_id = r.get_json()["template"]["id"]

    # get
    r = client.get(f"/api/v1/time-entry-templates/{t_id}", headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(
        f"/api/v1/time-entry-templates/{t_id}", headers=_auth(api_token), json={"default_notes": "updated"}
    )
    assert r.status_code == 200
    assert r.get_json()["template"]["default_notes"] == "updated"

    # delete
    r = client.delete(f"/api/v1/time-entry-templates/{t_id}", headers=_auth(api_token))
    assert r.status_code == 200
