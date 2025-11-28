import pytest
from datetime import date, timedelta

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_per_diem.sqlite",
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
    u = User(username="pduser", email="pduser@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(user_id=user.id, name="PerDiem Token", scopes="read:per_diem,write:per_diem")
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_per_diem_crud(client, api_token):
    # list empty
    r = client.get("/api/v1/per-diems", headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()["per_diems"] == []

    # create
    payload = {
        "trip_purpose": "Conference",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=2)).isoformat(),
        "country": "Germany",
        "full_day_rate": 30.0,
        "half_day_rate": 15.0,
        "full_days": 2,
        "half_days": 0,
    }
    r = client.post("/api/v1/per-diems", headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    pd = r.get_json()["per_diem"]
    pd_id = pd["id"]

    # get
    r = client.get(f"/api/v1/per-diems/{pd_id}", headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f"/api/v1/per-diems/{pd_id}", headers=_auth(api_token), json={"notes": "OK"})
    assert r.status_code == 200
    assert r.get_json()["per_diem"]["notes"] == "OK"

    # delete (reject)
    r = client.delete(f"/api/v1/per-diems/{pd_id}", headers=_auth(api_token))
    assert r.status_code == 200
