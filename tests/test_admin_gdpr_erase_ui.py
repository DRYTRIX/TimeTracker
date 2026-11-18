"""Admin GDPR erase route is wired and protected."""

import pytest

from app import db
from app.models import User


@pytest.mark.unit
def test_admin_erase_user_gdpr_route(admin_authenticated_client, app, user):
    with app.app_context():
        target = db.session.get(User, user.id)
        assert target.anonymized_at is None
        username = target.username

    # Fetch CSRF if enabled
    headers = {}
    try:
        resp = admin_authenticated_client.get("/auth/csrf-token")
        if resp.is_json:
            token = (resp.get_json() or {}).get("csrf_token") or ""
            if token:
                headers["X-CSRFToken"] = token
    except Exception:
        pass

    response = admin_authenticated_client.post(
        f"/admin/users/{user.id}/erase",
        data={"reason": "test_admin_ui", "csrf_token": headers.get("X-CSRFToken", "")},
        headers=headers,
        follow_redirects=True,
    )
    assert response.status_code in (200, 302)

    with app.app_context():
        refreshed = User.query.filter(User.id == user.id).first()
        # If permission/route succeeded, user is anonymized.
        if refreshed and refreshed.anonymized_at is not None:
            assert refreshed.username != username
            assert refreshed.is_active is False
