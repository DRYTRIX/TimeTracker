"""API v1 CRM coverage: leads, deals, contacts, activities, conversion, forecast."""

import os
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import create_app, db
from app.models import ApiToken, CalendarEvent, Client, Contact, Deal, LeadActivity, User
from app.services.email_sync_service import EmailSyncService

pytestmark = [pytest.mark.api, pytest.mark.integration]


@pytest.fixture
def app():
    unique_db_path = os.path.join(tempfile.gettempdir(), f"test_api_crm_{uuid.uuid4().hex}.sqlite")
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
    u = User(username="crmuser", email="crm@example.com", role="admin")
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    scopes = ",".join(
        [
            "read:leads",
            "write:leads",
            "read:deals",
            "write:deals",
            "read:contacts",
            "write:contacts",
            "read:clients",
            "write:clients",
        ]
    )
    token, plain = ApiToken.create_token(user_id=user.id, name="CRM Token", scopes=scopes)
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def test_lead_crud_activity_conversion_and_score_history(client, api_token, user):
    r = client.post(
        "/api/v1/leads",
        headers=_auth(api_token),
        json={"first_name": "Ada", "last_name": "Lovelace", "company_name": "Analytical", "score": 10},
    )
    assert r.status_code == 201
    lead_id = r.get_json()["lead"]["id"]

    r = client.post(
        f"/api/v1/leads/{lead_id}/activities",
        headers=_auth(api_token),
        json={"type": "call", "subject": "Intro call", "status": "completed"},
    )
    assert r.status_code == 201

    r = client.patch(f"/api/v1/leads/{lead_id}", headers=_auth(api_token), json={"score": 55})
    assert r.status_code == 200
    assert r.get_json()["lead"]["score"] == 55

    acts = LeadActivity.query.filter_by(lead_id=lead_id, type="score_change").all()
    assert len(acts) == 1

    r = client.get(f"/api/v1/leads/{lead_id}/activities", headers=_auth(api_token))
    assert r.status_code == 200
    assert len(r.get_json()["activities"]) >= 2

    r = client.post(f"/api/v1/leads/{lead_id}/convert-to-client", headers=_auth(api_token), json={})
    assert r.status_code == 200
    body = r.get_json()
    assert body["lead"]["status"] == "converted"
    assert body["client"]["id"]
    assert body["contact"]["first_name"] == "Ada"


def test_deal_stage_forecast_and_activity_calendar(client, api_token, user):
    r = client.post(
        "/api/v1/deals",
        headers=_auth(api_token),
        json={"name": "Big Deal", "value": 1000, "probability": 50, "stage": "prospecting"},
    )
    assert r.status_code == 201
    deal_id = r.get_json()["deal"]["id"]

    due = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    r = client.post(
        f"/api/v1/deals/{deal_id}/activities",
        headers=_auth(api_token),
        json={"type": "meeting", "subject": "Demo", "due_date": due},
    )
    assert r.status_code == 201
    assert CalendarEvent.query.filter_by(user_id=user.id).count() >= 1

    r = client.patch(f"/api/v1/deals/{deal_id}/stage", headers=_auth(api_token), json={"stage": "proposal"})
    assert r.status_code == 200
    assert r.get_json()["deal"]["stage"] == "proposal"

    r = client.get("/api/v1/deals/forecast", headers=_auth(api_token))
    assert r.status_code == 200
    forecast = r.get_json()["forecast"]
    assert forecast["open_deal_count"] >= 1
    assert "by_stage" in forecast


def test_contact_communications(client, api_token, user):
    c = Client(name="CRM Client", email="crm-client@example.com")
    db.session.add(c)
    db.session.commit()

    r = client.post(
        f"/api/v1/clients/{c.id}/contacts",
        headers=_auth(api_token),
        json={"first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com"},
    )
    assert r.status_code == 201
    contact_id = r.get_json()["contact"]["id"]

    r = client.post(
        f"/api/v1/contacts/{contact_id}/communications",
        headers=_auth(api_token),
        json={"type": "email", "subject": "Hello", "content": "Hi", "direction": "outbound"},
    )
    assert r.status_code == 201

    r = client.get(f"/api/v1/contacts/{contact_id}/communications", headers=_auth(api_token))
    assert r.status_code == 200
    assert len(r.get_json()["communications"]) == 1


def test_email_match_crm_via_deal_contact(app, user):
    client_obj = Client(name="Match Co", email="office@match.co")
    db.session.add(client_obj)
    db.session.flush()
    contact = Contact(
        client_id=client_obj.id,
        first_name="Pat",
        last_name="Lee",
        created_by=user.id,
        email="pat@match.co",
    )
    db.session.add(contact)
    db.session.flush()
    deal = Deal(
        name="Match Deal", created_by=user.id, client_id=client_obj.id, contact_id=contact.id, value=Decimal("100")
    )
    db.session.add(deal)
    db.session.commit()

    service = EmailSyncService()
    client_id, lead_id, deal_id = service.match_crm(["pat@match.co"])
    assert client_id == client_obj.id
    assert deal_id == deal.id
    assert lead_id is None


def test_lead_source_analytics(client, api_token):
    client.post(
        "/api/v1/leads",
        headers=_auth(api_token),
        json={"first_name": "A", "last_name": "One", "source": "web", "estimated_value": 100},
    )
    client.post(
        "/api/v1/leads",
        headers=_auth(api_token),
        json={"first_name": "B", "last_name": "Two", "source": "web", "estimated_value": 50},
    )
    client.post(
        "/api/v1/leads",
        headers=_auth(api_token),
        json={"first_name": "C", "last_name": "Three", "source": "referral"},
    )
    r = client.get("/api/v1/leads/analytics/sources", headers=_auth(api_token))
    assert r.status_code == 200
    sources = {s["source"]: s for s in r.get_json()["sources"]}
    assert sources["web"]["count"] == 2
    assert sources["referral"]["count"] == 1


def test_convert_lead_to_deal(client, api_token):
    r = client.post(
        "/api/v1/leads",
        headers=_auth(api_token),
        json={"first_name": "Sam", "last_name": "Deal", "estimated_value": 250},
    )
    lead_id = r.get_json()["lead"]["id"]
    r = client.post(
        f"/api/v1/leads/{lead_id}/convert-to-deal",
        headers=_auth(api_token),
        json={"name": "From Lead", "stage": "qualification", "probability": 40},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["lead"]["status"] == "converted"
    assert body["deal"]["name"] == "From Lead"
    assert Deal.query.get(body["deal"]["id"]).lead_id == lead_id
