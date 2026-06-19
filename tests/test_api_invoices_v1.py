import json
import uuid
import tempfile
import os
import pytest

pytestmark = [pytest.mark.api, pytest.mark.integration]

from datetime import date, timedelta

from app import create_app, db
from app.models import User, Client, Project, Invoice, ApiToken


@pytest.fixture
def app():
    unique_db_path = os.path.join(tempfile.gettempdir(), f"test_api_invoices_{uuid.uuid4().hex}.sqlite")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{unique_db_path}",
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


@pytest.fixture
def other_user(app):
    u = User(username="otheruser", email="other@example.com", role="user")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def other_token(app, other_user):
    token, plain = ApiToken.create_token(
        user_id=other_user.id, name="Other Token", scopes="read:invoices,write:invoices"
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def admin_user(app):
    u = User(username="adminuser", email="admin@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin_token(app, admin_user):
    token, plain = ApiToken.create_token(
        user_id=admin_user.id, name="Admin Token", scopes="read:invoices,write:invoices"
    )
    db.session.add(token)
    db.session.commit()
    return plain


def _auth_header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _create_draft_invoice(client, token, project, client_model):
    """Create a draft invoice via the API and return its id."""
    due = (date.today() + timedelta(days=14)).isoformat()
    payload = {
        "project_id": project.id,
        "client_id": client_model.id,
        "client_name": client_model.name,
        "client_email": client_model.email,
        "due_date": due,
        "currency_code": "EUR",
    }
    r = client.post("/api/v1/invoices", headers=_auth_header(token), json=payload)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["invoice"]["id"]


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


# --- Access control on invoice detail (regression guard against data leak) ---


def test_get_invoice_forbidden_for_other_user(client, api_token, other_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=_auth_header(other_token))
    assert r.status_code == 403


def test_get_invoice_allowed_for_admin(client, api_token, admin_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=_auth_header(admin_token))
    assert r.status_code == 200
    assert r.get_json()["invoice"]["id"] == invoice_id


def test_get_invoice_not_found(client, api_token):
    r = client.get("/api/v1/invoices/999999", headers=_auth_header(api_token))
    assert r.status_code == 404


# --- PUT /invoices/<id>/items ---


def test_set_invoice_items_happy_path(client, api_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    payload = {
        "items": [
            {"description": "Consulting", "quantity": 2, "unit_price": 100},
            {"description": "Design", "quantity": 1, "unit_price": 50},
        ]
    }
    r = client.put(f"/api/v1/invoices/{invoice_id}/items", headers=_auth_header(api_token), json=payload)
    assert r.status_code == 200, r.get_json()
    detail = r.get_json()["invoice"]
    assert len(detail["items"]) == 2

    # Verify totals were recalculated and persisted
    db.session.expire_all()
    inv = Invoice.query.get(invoice_id)
    assert float(inv.subtotal) == 250.0


def test_set_invoice_items_skips_blank_descriptions(client, api_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    payload = {"items": [{"description": "   ", "quantity": 1, "unit_price": 10}]}
    r = client.put(f"/api/v1/invoices/{invoice_id}/items", headers=_auth_header(api_token), json=payload)
    assert r.status_code == 200
    assert r.get_json()["invoice"]["items"] == []


def test_set_invoice_items_rejects_non_list(client, api_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    r = client.put(
        f"/api/v1/invoices/{invoice_id}/items", headers=_auth_header(api_token), json={"items": "nope"}
    )
    assert r.status_code == 400


def test_set_invoice_items_forbidden_for_other_user(client, api_token, other_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    payload = {"items": [{"description": "X", "quantity": 1, "unit_price": 1}]}
    r = client.put(f"/api/v1/invoices/{invoice_id}/items", headers=_auth_header(other_token), json=payload)
    assert r.status_code == 403


def test_set_invoice_items_not_found(client, api_token):
    payload = {"items": [{"description": "X", "quantity": 1, "unit_price": 1}]}
    r = client.put("/api/v1/invoices/999999/items", headers=_auth_header(api_token), json=payload)
    assert r.status_code == 404


# --- GET /invoices/<id>/pdf (access-control branches; PDF rendering not exercised) ---


def test_export_invoice_pdf_forbidden_for_other_user(client, api_token, other_token, project, client_model):
    invoice_id = _create_draft_invoice(client, api_token, project, client_model)
    r = client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=_auth_header(other_token))
    assert r.status_code == 403


def test_export_invoice_pdf_not_found(client, api_token):
    r = client.get("/api/v1/invoices/999999/pdf", headers=_auth_header(api_token))
    assert r.status_code == 404
