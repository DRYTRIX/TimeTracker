import json
import pytest
from datetime import date, timedelta

from app import create_app, db
from app.models import User, Client, Project, Invoice, ApiToken


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///test_api_invoices.sqlite",
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
    u = User(username="apiuser", email="apiuser@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id, name="Invoices Token", scopes="read:invoices,write:invoices,read:clients,read:projects"
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def client_model(app):
    c = Client(name="Invoice Client", email="client@example.com", company="ClientCo")
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def project(app, client_model):
    p = Project(name="Invoice Project", client_id=client_model.id, status="active")
    db.session.add(p)
    db.session.commit()
    return p


def _auth_header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_list_invoices_empty(client, api_token):
    r = client.get("/api/v1/invoices", headers=_auth_header(api_token))
    assert r.status_code == 200
    data = r.get_json()
    assert "invoices" in data
    assert isinstance(data["invoices"], list)
    assert data["invoices"] == []


def test_create_get_update_cancel_invoice(client, api_token, user, project, client_model):
    due = (date.today() + timedelta(days=14)).isoformat()
    create_payload = {
        "project_id": project.id,
        "client_id": client_model.id,
        "client_name": client_model.name,
        "client_email": client_model.email,
        "due_date": due,
        "notes": "Test invoice",
        "tax_rate": 20.0,
        "currency_code": "EUR",
    }
    # Create
    r = client.post("/api/v1/invoices", headers=_auth_header(api_token), json=create_payload)
    assert r.status_code == 201
    created = r.get_json()["invoice"]
    assert created["client_name"] == client_model.name
    invoice_id = created["id"]

    # Get
    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=_auth_header(api_token))
    assert r.status_code == 200
    inv = r.get_json()["invoice"]
    assert inv["id"] == invoice_id
    assert inv["status"] in ("draft", "sent", "paid", "overdue", "cancelled")

    # Update
    r = client.patch(f"/api/v1/invoices/{invoice_id}", headers=_auth_header(api_token), json={"notes": "Updated"})
    assert r.status_code == 200
    updated = r.get_json()["invoice"]
    assert updated["notes"] == "Updated"

    # Cancel (soft-delete)
    r = client.delete(f"/api/v1/invoices/{invoice_id}", headers=_auth_header(api_token))
    assert r.status_code == 200

    # Verify cancelled
    db.session.expire_all()
    inv_obj = Invoice.query.get(invoice_id)
    assert inv_obj.status == "cancelled"
