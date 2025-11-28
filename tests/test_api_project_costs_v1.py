import pytest
from datetime import date

from app import create_app, db
from app.models import User, Project, Client, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_project_costs.sqlite",
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
    u = User(username="pcuser", email="pc@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id, name="ProjectCosts Token", scopes="read:projects,write:projects"
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def project(app):
    c = Client(name="PC Client")
    db.session.add(c)
    db.session.commit()
    p = Project(name="PC Project", client_id=c.id, status="active")
    db.session.add(p)
    db.session.commit()
    return p


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_project_costs_crud(client, api_token, project):
    # list empty
    r = client.get(f"/api/v1/projects/{project.id}/costs", headers=_auth(api_token))
    assert r.status_code == 200
    body = r.get_json()
    assert "costs" in body and "pagination" in body
    assert body["costs"] == []

    # create
    payload = {
        "description": "Laptop",
        "category": "equipment",
        "amount": 1200.0,
        "cost_date": date.today().isoformat(),
        "billable": True,
    }
    r = client.post(f"/api/v1/projects/{project.id}/costs", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    cost_id = r.get_json()["cost"]["id"]

    # get
    r = client.get(f"/api/v1/project-costs/{cost_id}", headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f"/api/v1/project-costs/{cost_id}", headers=_auth(api_token), json={"notes": "Purchased"})
    assert r.status_code == 200

    # delete
    r = client.delete(f"/api/v1/project-costs/{cost_id}", headers=_auth(api_token))
    assert r.status_code == 200
