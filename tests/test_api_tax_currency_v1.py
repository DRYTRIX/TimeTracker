import pytest
from datetime import date

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_tax_currency.sqlite",
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
    u = User(username="admin", email="admin@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin_token(app, admin_user):
    token, plain = ApiToken.create_token(user_id=admin_user.id, name="Admin Token", scopes="admin:all,read:invoices")
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_tax_currency_flow(client, admin_token):
    # create currency
    r = client.post(
        "/api/v1/currencies", headers=_auth(admin_token), json={"code": "USD", "name": "US Dollar", "symbol": "$"}
    )
    assert r.status_code == 201

    # list currencies
    r = client.get("/api/v1/currencies", headers=_auth(admin_token))
    assert r.status_code == 200
    assert any(c["code"] == "USD" for c in r.get_json()["currencies"])

    # create exchange rate
    r = client.post(
        "/api/v1/exchange-rates",
        headers=_auth(admin_token),
        json={"base_code": "EUR", "quote_code": "USD", "rate": 1.1, "date": date.today().isoformat(), "source": "test"},
    )
    assert r.status_code == 201

    # list exchange rates
    r = client.get("/api/v1/exchange-rates?base_code=EUR&quote_code=USD", headers=_auth(admin_token))
    assert r.status_code == 200

    # create tax rule
    r = client.post(
        "/api/v1/tax-rules",
        headers=_auth(admin_token),
        json={"name": "VAT DE", "country": "DE", "rate_percent": 19.0, "active": True},
    )
    assert r.status_code == 201

    # list tax rules
    r = client.get("/api/v1/tax-rules", headers=_auth(admin_token))
    assert r.status_code == 200
