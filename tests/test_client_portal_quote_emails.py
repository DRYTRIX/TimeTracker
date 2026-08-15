"""Regression: client portal quote accept/reject must send admin emails via send_template_email."""

from unittest.mock import patch

from flask import url_for

from app import db
from app.models import Client, Quote, User


def _make_visible_quote(app, admin_user, test_client):
    with app.app_context():
        admin = db.session.get(User, admin_user.id)
        admin.role = "admin"
        admin.is_active = True
        if not admin.email:
            admin.email = "admin@example.com"

        quote = Quote(
            quote_number=Quote.generate_quote_number(),
            client_id=test_client.id,
            title="Portal Quote",
            created_by=admin_user.id,
            status="sent",
            visible_to_client=True,
        )
        db.session.add(quote)
        db.session.commit()
        return quote.id


def test_client_portal_accept_quote_sends_template_email(client, admin_user, test_client, app):
    quote_id = _make_visible_quote(app, admin_user, test_client)

    with app.app_context():
        url = url_for("client_portal.accept_quote", quote_id=quote_id)
        portal_client = db.session.get(Client, test_client.id)

    with (
        patch("app.routes.client_portal.check_client_portal_access", return_value=portal_client),
        patch("app.utils.email.send_template_email") as mock_send,
    ):
        resp = client.post(url, follow_redirects=False)
        assert resp.status_code in (302, 303), resp.data[:500]
        assert mock_send.called, "send_template_email should be called for admins"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["template"] == "email/quote_accepted.html"
        assert "Accepted by Client" in kwargs["subject"]

    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        assert quote.status == "accepted"


def test_client_portal_reject_quote_sends_template_email(client, admin_user, test_client, app):
    quote_id = _make_visible_quote(app, admin_user, test_client)

    with app.app_context():
        url = url_for("client_portal.reject_quote", quote_id=quote_id)
        portal_client = db.session.get(Client, test_client.id)

    with (
        patch("app.routes.client_portal.check_client_portal_access", return_value=portal_client),
        patch("app.utils.email.send_template_email") as mock_send,
    ):
        resp = client.post(url, data={"reason": "Too expensive"}, follow_redirects=False)
        assert resp.status_code in (302, 303), resp.data[:500]
        assert mock_send.called
        kwargs = mock_send.call_args.kwargs
        assert kwargs["template"] == "email/quote_rejected.html"
        assert "Rejected by Client" in kwargs["subject"]

    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        assert quote.status == "rejected"
