import pytest

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_kanban.sqlite",
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
    u = User(username="kbuser", email="kb@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Kanban Token", scopes="read:tasks,write:tasks")
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_kanban_columns(client, api_token):
    # list (may be empty)
    r = client.get("/api/v1/kanban/columns", headers=_auth(api_token))
    assert r.status_code == 200

    # create
    payload = {"key": "custom", "label": "Custom", "is_system": False}
    r = client.post("/api/v1/kanban/columns", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    col_id = r.get_json()["column"]["id"]

    # reorder
    r = client.post("/api/v1/kanban/columns/reorder", headers=_auth(api_token), json={"column_ids": [col_id]})
    assert r.status_code == 200

    # delete
    r = client.delete(f"/api/v1/kanban/columns/{col_id}", headers=_auth(api_token))
    assert r.status_code == 200
