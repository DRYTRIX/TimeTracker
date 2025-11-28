import pytest

from app import create_app, db
from app.models import User, Project, Client, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_favorites.sqlite",
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
    u = User(username="favuser", email="fav@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Favorites Token", scopes="read:projects,write:projects")
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def project(app):
    c = Client(name="Fav Client")
    db.session.add(c)
    db.session.commit()
    p = Project(name="Fav Project", client_id=c.id, status="active")
    db.session.add(p)
    db.session.commit()
    return p


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_favorites_flow(client, api_token, project):
    # list empty
    r = client.get("/api/v1/users/me/favorites/projects", headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()["favorites"] == []

    # add
    r = client.post("/api/v1/users/me/favorites/projects", headers=_auth(api_token), json={"project_id": project.id})
    assert r.status_code in (200, 201)

    # list
    r = client.get("/api/v1/users/me/favorites/projects", headers=_auth(api_token))
    assert r.status_code == 200
    assert any(f["project_id"] == project.id for f in r.get_json()["favorites"])

    # remove
    r = client.delete(f"/api/v1/users/me/favorites/projects/{project.id}", headers=_auth(api_token))
    assert r.status_code == 200
