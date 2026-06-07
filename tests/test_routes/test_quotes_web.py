"""Web UI tests for quotes (regression: issue #583 create -> view 500)."""

from unittest.mock import patch

from flask import url_for

from app import db
from app.models import Permission, Quote, Role, User


def test_create_quote_redirect_then_view_returns_200(admin_authenticated_client, test_client, app):
    with app.app_context():
        create_url = url_for("quotes.create_quote")

    resp = admin_authenticated_client.post(
        create_url,
        data={
            "client_id": str(test_client.id),
            "title": "Regression Quote 583",
            "tax_rate": "0",
            "currency_code": "EUR",
            # Triggers Valid until block + expired badge on view (issue #583 used undefined now()).
            "valid_until": "2020-01-01",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303), resp.data[:500]
    location = resp.headers.get("Location", "")
    assert "/quotes/" in location

    view_resp = admin_authenticated_client.get(location, follow_redirects=False)
    assert view_resp.status_code == 200, view_resp.data[:500]


def test_edit_quote_by_user_with_edit_quotes_redirect_then_view_returns_200(app, client, admin_user, test_client):
    """Non-admin with edit_quotes must see another user's quote after POST edit (list/detail scope matches edit)."""
    with app.app_context():
        perm = Permission.query.filter_by(name="edit_quotes").first()
        if not perm:
            perm = Permission(name="edit_quotes", description="Edit quotes", category="quotes")
            db.session.add(perm)
            db.session.commit()

        role = Role.query.filter_by(name="test_quote_editor").first()
        if not role:
            role = Role(name="test_quote_editor", description="Quote editor test role")
            db.session.add(role)
            db.session.flush()
        if perm not in role.permissions:
            role.permissions.append(perm)

        editor = User.query.filter_by(username="quote_editor_test").first()
        if not editor:
            editor = User(username="quote_editor_test", email="quote_editor_test@example.com", role="user")
            editor.is_active = True
            editor.set_password("password123")
            db.session.add(editor)
            db.session.flush()
        if role not in editor.roles:
            editor.roles.append(role)
        db.session.commit()

        quote = Quote(
            quote_number=Quote.generate_quote_number(),
            client_id=test_client.id,
            title="Quote by admin",
            created_by=admin_user.id,
        )
        db.session.add(quote)
        db.session.commit()
        quote_id = quote.id
        editor_id = editor.id

        edit_url = url_for("quotes.edit_quote", quote_id=quote_id)

    with client.session_transaction() as sess:
        sess["_user_id"] = str(editor_id)

    resp = client.post(
        edit_url,
        data={
            "title": "Updated by editor",
            "tax_rate": "0",
            "currency_code": "EUR",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303), resp.data[:500]
    location = resp.headers.get("Location", "")
    assert f"/quotes/{quote_id}" in location

    view_resp = client.get(location, follow_redirects=False)
    assert view_resp.status_code == 200, view_resp.data[:500]
    assert b"Updated by editor" in view_resp.data


def test_send_quote_email_accepts_form_recipient_email(admin_authenticated_client, quote, app):
    """Regression #652: form POST must read recipient_email (not discard for non-JSON)."""
    with app.app_context():
        send_url = url_for("quotes.send_quote_email", quote_id=quote.id)

    with patch("app.utils.email.send_quote_email") as mock_send:
        mock_send.return_value = (True, None, "sent")

        resp = admin_authenticated_client.post(
            send_url,
            data={"recipient_email": "typed@example.com"},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 303), resp.data[:500]
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["recipient_email"] == "typed@example.com"


def test_send_quote_email_missing_recipient_redirects_for_form_post(
    admin_authenticated_client, quote, test_client, app
):
    """Regression #652: plain form POST should flash+redirect, not raw JSON error."""
    with app.app_context():
        test_client.email = None
        db.session.commit()
        send_url = url_for("quotes.send_quote_email", quote_id=quote.id)

    resp = admin_authenticated_client.post(
        send_url,
        data={},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 303), resp.data[:500]
    assert f"/quotes/{quote.id}" in (resp.headers.get("Location") or "")
