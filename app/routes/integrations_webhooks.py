"""
Routes for the new opt-in connectors (GitHub PAT, Google Calendar
OAuth, Slack bot). Registered as an optional blueprint from
``app.blueprint_registry``.

Endpoint groups
---------------

GitHub
    POST  /api/integrations/github/webhook   (M2M, signature-verified)
    POST  /api/integrations/github/sync      (admin)
    POST  /api/integrations/github/config    (login_required)
    POST  /api/integrations/github/test      (login_required)
    GET   /api/integrations/github/status    (login_required)

Google Calendar
    GET   /integrations/google/connect       (login_required, OAuth start)
    GET   /integrations/google/callback      (login_required, OAuth finish)
    POST  /integrations/google/disconnect    (login_required)
    POST  /api/integrations/google/sync      (login_required)
    POST  /api/integrations/google/config    (login_required)
    GET   /api/integrations/google/status    (login_required)

Slack
    POST  /api/integrations/slack/events     (M2M, signature-verified)
    POST  /api/integrations/slack/config     (login_required)
    POST  /api/integrations/slack/test       (login_required)
    GET   /api/integrations/slack/status     (login_required)
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, flash, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_required

from app import csrf, db
from app.integrations.github_connector import PROVIDER_KEY as GH_PROVIDER
from app.integrations.github_connector import GitHubConnector
from app.integrations.google_calendar_connector import PROVIDER_KEY as GCAL_PROVIDER
from app.integrations.google_calendar_connector import GoogleCalendarConnector
from app.integrations.slack_connector import PROVIDER_KEY as SLACK_PROVIDER
from app.integrations.slack_connector import SlackConnector
from app.models import Integration
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)

integrations_webhooks_bp = Blueprint("integrations_webhooks", __name__)


def _ensure_integration(provider: str, *, user_id: Optional[int] = None) -> Integration:
    """Get-or-create an Integration row keyed by ``(provider, user_id)``.

    User-scoped integrations are per-user; ``user_id`` is required.
    """
    integration = Integration.query.filter_by(provider=provider, user_id=user_id).first()
    if integration:
        return integration
    integration = Integration(
        name={
            GH_PROVIDER: "GitHub",
            GCAL_PROVIDER: "Google Calendar",
            SLACK_PROVIDER: "Slack",
        }.get(provider, provider),
        provider=provider,
        user_id=user_id,
        is_global=False,
        is_active=False,
        config={},
    )
    db.session.add(integration)
    safe_commit("connector_create_integration", {"provider": provider, "user_id": user_id})
    return integration


def _admin_required() -> bool:
    return bool(getattr(current_user, "is_authenticated", False) and getattr(current_user, "is_admin", False))


# =====================================================================
# GitHub
# =====================================================================
@integrations_webhooks_bp.route("/api/integrations/github/webhook", methods=["POST"])
@csrf.exempt
def github_webhook():
    """Receive a GitHub webhook delivery (machine-to-machine, no login)."""
    raw_body = request.get_data() or b""
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Malformed payload"}), 400

    headers = {k: v for k, v in request.headers.items()}

    # Try every active GitHub integration; first one whose signature
    # matches wins. Avoids leaking which integration the secret belongs to.
    for connector in GitHubConnector.for_any_active():
        result = connector.handle_webhook(payload, headers, raw_body=raw_body)
        status = int(result.get("status") or 200)
        body = result.get("body") or {}
        if status == 401:
            # Signature mismatch for THIS integration — try the next one.
            continue
        return jsonify(body), status

    # No integration matched the signature.
    return jsonify({"ok": False, "error": "No matching GitHub integration"}), 401


@integrations_webhooks_bp.route("/api/integrations/github/sync", methods=["POST"])
@login_required
def github_sync():
    if not _admin_required():
        return jsonify({"ok": False, "error": "Admin only"}), 403
    connector = GitHubConnector.for_user(current_user)
    if not connector:
        return jsonify({"ok": False, "error": "Integration not configured"}), 404
    return jsonify(connector.sync())


@integrations_webhooks_bp.route("/api/integrations/github/config", methods=["POST"])
@login_required
def github_save_config():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    integration = _ensure_integration(GH_PROVIDER, user_id=current_user.id)

    # Auto-generate a webhook secret if the caller didn't supply one and
    # the integration row doesn't have one yet.
    if not payload.get("webhook_secret") and not (integration.config or {}).get("webhook_secret"):
        payload["webhook_secret"] = secrets.token_urlsafe(32)

    result = GitHubConnector.save_config(integration, payload)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@integrations_webhooks_bp.route("/api/integrations/github/test", methods=["POST"])
@login_required
def github_test():
    connector = GitHubConnector.for_user(current_user)
    if not connector:
        return jsonify({"ok": False, "error": "Integration not configured"}), 404
    return jsonify(connector.test_connection())


@integrations_webhooks_bp.route("/api/integrations/github/status", methods=["GET"])
@login_required
def github_status():
    integration = Integration.query.filter_by(provider=GH_PROVIDER, user_id=current_user.id).first()
    if not integration:
        return jsonify({"ok": True, "connected": False})
    cfg = integration.config or {}
    return jsonify(
        {
            "ok": True,
            "connected": bool(cfg.get("github_token") and integration.is_active),
            "repo_owner": cfg.get("repo_owner"),
            "repo_name": cfg.get("repo_name"),
            "default_project_id": cfg.get("default_project_id"),
            "auto_start_timer": bool(cfg.get("auto_start_timer")),
            "label_filter": cfg.get("label_filter"),
            "has_webhook_secret": bool(cfg.get("webhook_secret")),
            "webhook_url": url_for("integrations_webhooks.github_webhook", _external=True),
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        }
    )


# =====================================================================
# Google Calendar (OAuth + sync)
# =====================================================================
_GOOGLE_STATE_KEY = "_google_oauth_state"


def _google_redirect_uri() -> str:
    return url_for("integrations_webhooks.google_callback", _external=True)


@integrations_webhooks_bp.route("/integrations/google/connect")
@login_required
def google_connect():
    integration = GoogleCalendarConnector.get_or_create_for_user(current_user)
    connector = GoogleCalendarConnector(integration=integration, credentials=None)
    state = secrets.token_urlsafe(24)
    session[_GOOGLE_STATE_KEY] = state
    try:
        url = connector.get_authorization_url(_google_redirect_uri(), state=state)
    except Exception as exc:
        logger.warning("Google OAuth start failed: %s", exc)
        flash(str(exc), "error")
        return redirect(url_for("integrations.list_integrations"))
    return redirect(url)


@integrations_webhooks_bp.route("/integrations/google/callback")
@login_required
def google_callback():
    state = request.args.get("state")
    expected = session.pop(_GOOGLE_STATE_KEY, None)
    if not state or state != expected:
        flash("OAuth state mismatch — please retry connecting Google Calendar.", "error")
        return redirect(url_for("integrations.list_integrations"))
    error = request.args.get("error")
    if error:
        flash(f"Google Calendar authorization failed: {error}", "error")
        return redirect(url_for("integrations.list_integrations"))
    code = request.args.get("code")
    if not code:
        flash("Google Calendar authorization missing code.", "error")
        return redirect(url_for("integrations.list_integrations"))

    integration = GoogleCalendarConnector.get_or_create_for_user(current_user)
    connector = GoogleCalendarConnector(integration=integration, credentials=None)
    try:
        tokens = connector.exchange_code_for_tokens(code, _google_redirect_uri())
    except Exception as exc:
        logger.warning("Google OAuth callback failed: %s", exc)
        flash(f"Google Calendar connection failed: {exc}", "error")
        return redirect(url_for("integrations.list_integrations"))

    save_result = GoogleCalendarConnector.save_tokens(integration, tokens)
    if not save_result.get("ok"):
        flash(save_result.get("error") or "Could not save Google credentials.", "error")
    else:
        flash("Google Calendar connected.", "success")
    return redirect(url_for("integrations.list_integrations"))


@integrations_webhooks_bp.route("/integrations/google/disconnect", methods=["POST"])
@login_required
def google_disconnect():
    connector = GoogleCalendarConnector.for_user(current_user)
    if connector:
        connector.revoke()
        flash("Google Calendar disconnected.", "success")
    return redirect(url_for("integrations.list_integrations"))


@integrations_webhooks_bp.route("/api/integrations/google/sync", methods=["POST"])
@login_required
def google_sync():
    connector = GoogleCalendarConnector.for_user(current_user)
    if not connector:
        return jsonify({"ok": False, "error": "Integration not configured"}), 404
    return jsonify(connector.sync())


@integrations_webhooks_bp.route("/api/integrations/google/config", methods=["POST"])
@login_required
def google_save_config():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    integration = GoogleCalendarConnector.get_or_create_for_user(current_user)
    result = GoogleCalendarConnector.save_settings(integration, payload)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@integrations_webhooks_bp.route("/api/integrations/google/status", methods=["GET"])
@login_required
def google_status():
    integration = Integration.query.filter_by(provider=GCAL_PROVIDER, user_id=current_user.id).first()
    if not integration:
        return jsonify({"ok": True, "connected": False})
    connector = GoogleCalendarConnector(integration=integration, credentials=None)
    return jsonify(connector.get_status())


# =====================================================================
# Slack
# =====================================================================
@integrations_webhooks_bp.route("/api/integrations/slack/events", methods=["POST"])
@csrf.exempt
def slack_events():
    """Single endpoint for Events API URL verification and slash commands."""
    raw_body = request.get_data() or b""
    signature = request.headers.get("X-Slack-Signature")
    timestamp = request.headers.get("X-Slack-Request-Timestamp")

    # URL verification challenge arrives as JSON; still must verify.
    if request.is_json:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        connector = SlackConnector.find_by_signing_secret_match(signature, timestamp, raw_body)
        if not connector:
            return jsonify({"ok": False, "error": "Invalid signature"}), 401
        if payload.get("type") == "url_verification" and payload.get("challenge"):
            return jsonify({"challenge": payload["challenge"]})
        return jsonify(connector.handle_webhook(payload, dict(request.headers), raw_body=raw_body).get("body") or {})

    # Slash command — form-encoded.
    form = request.form.to_dict()
    connector = SlackConnector.find_by_signing_secret_match(signature, timestamp, raw_body)
    if not connector:
        return jsonify({"ok": False, "error": "Invalid signature"}), 401

    result = connector.handle_slash_command(form)
    status = int(result.get("status") or 200)
    body = result.get("body") or {}
    return jsonify(body), status


@integrations_webhooks_bp.route("/api/integrations/slack/config", methods=["POST"])
@login_required
def slack_save_config():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    integration = _ensure_integration(SLACK_PROVIDER, user_id=current_user.id)
    result = SlackConnector.save_config(integration, payload)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@integrations_webhooks_bp.route("/api/integrations/slack/test", methods=["POST"])
@login_required
def slack_test():
    connector = SlackConnector.for_user(current_user)
    if not connector:
        return jsonify({"ok": False, "error": "Integration not configured"}), 404
    return jsonify(connector.send_test_message())


@integrations_webhooks_bp.route("/api/integrations/slack/status", methods=["GET"])
@login_required
def slack_status():
    integration = Integration.query.filter_by(provider=SLACK_PROVIDER, user_id=current_user.id).first()
    if not integration:
        return jsonify({"ok": True, "connected": False})
    cfg = integration.config or {}
    return jsonify(
        {
            "ok": True,
            "connected": bool(cfg.get("bot_token") and integration.is_active),
            "channel_id": cfg.get("channel_id"),
            "notify_on_start": bool(cfg.get("notify_on_start")),
            "notify_on_stop": bool(cfg.get("notify_on_stop")),
            "daily_summary": bool(cfg.get("daily_summary")),
            "daily_summary_time": cfg.get("daily_summary_time") or "18:00",
            "linked_slack_user_id": cfg.get("linked_slack_user_id"),
            "has_signing_secret": bool(cfg.get("signing_secret")),
            "events_url": url_for("integrations_webhooks.slack_events", _external=True),
        }
    )
