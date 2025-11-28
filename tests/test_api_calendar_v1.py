import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_calendar.sqlite",
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
    u = User(username="caluser", email="cal@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Calendar Token", scopes="read:calendar,write:calendar")
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_calendar_crud(client, api_token):
    start = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"

    # create
    payload = {"title": "Meeting", "start_time": start, "end_time": end, "location": "Office"}
    r = client.post("/api/v1/calendar/events", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    ev_id = r.get_json()["event"]["id"]

    # list
    r = client.get("/api/v1/calendar/events", headers=_auth(api_token))
    assert r.status_code == 200

    # get
    r = client.get(f"/api/v1/calendar/events/{ev_id}", headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f"/api/v1/calendar/events/{ev_id}", headers=_auth(api_token), json={"title": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["event"]["title"] == "Updated"

    # delete
    r = client.delete(f"/api/v1/calendar/events/{ev_id}", headers=_auth(api_token))
    assert r.status_code == 200
