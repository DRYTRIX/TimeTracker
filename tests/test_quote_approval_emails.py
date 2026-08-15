"""Regression: quote approval routes must not 500 on missing email helpers."""

from unittest.mock import patch

from flask import url_for

from app import db
from app.models import Quote


def _make_quote_requiring_approval(app, admin_user, test_client):
    with app.app_context():
        quote = Quote(
            quote_number=Quote.generate_quote_number(),
            client_id=test_client.id,
            title="Approval Flow Quote",
            created_by=admin_user.id,
            requires_approval=True,
        )
        db.session.add(quote)
        db.session.commit()
        return quote.id


def test_request_approval_does_not_500(admin_authenticated_client, admin_user, test_client, app):
    quote_id = _make_quote_requiring_approval(app, admin_user, test_client)
    with app.app_context():
        url = url_for("quotes.request_approval", quote_id=quote_id)

    with patch("app.utils.email.send_email") as mock_send:
        resp = admin_authenticated_client.post(url, follow_redirects=False)
        assert resp.status_code in (302, 303), resp.data[:500]
        assert mock_send.called

    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        assert quote.approval_status == "pending"


def test_approve_quote_does_not_500(admin_authenticated_client, admin_user, test_client, app):
    quote_id = _make_quote_requiring_approval(app, admin_user, test_client)
    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        quote.request_approval()
        db.session.commit()
        url = url_for("quotes.approve_quote", quote_id=quote_id)

    with patch("app.utils.email.send_email") as mock_send:
        resp = admin_authenticated_client.post(url, data={"notes": "LGTM"}, follow_redirects=False)
        assert resp.status_code in (302, 303), resp.data[:500]
        assert mock_send.called

    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        assert quote.approval_status == "approved"


def test_reject_approval_does_not_500(admin_authenticated_client, admin_user, test_client, app):
    quote_id = _make_quote_requiring_approval(app, admin_user, test_client)
    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        quote.request_approval()
        db.session.commit()
        url = url_for("quotes.reject_approval", quote_id=quote_id)

    with patch("app.utils.email.send_email") as mock_send:
        resp = admin_authenticated_client.post(
            url, data={"reason": "Needs revision"}, follow_redirects=False
        )
        assert resp.status_code in (302, 303), resp.data[:500]
        assert mock_send.called

    with app.app_context():
        quote = db.session.get(Quote, quote_id)
        assert quote.approval_status == "rejected"
