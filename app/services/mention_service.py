"""Detect @username mentions in comments and notify the mentioned users.

A comment author can reference a teammate with ``@their_username``. When a
comment is saved we parse those handles, resolve them to active users (never
the author themselves), and deliver a notification through the same web-push
channel the app already uses for reminders, plus a per-user Socket.IO event
for any client that is listening in real time.

Delivery degrades gracefully: if pywebpush / VAPID keys are not configured, no
push is sent but mention resolution and the Socket.IO emit still work.
"""

import re

from app import db

# @handle: letters, digits, underscore, dot, hyphen. The negative lookbehind
# keeps us from matching the "@" inside an email address (e.g. a@b.com) since
# it would be preceded by a word character.
_MENTION_RE = re.compile(r"(?<![\w.@-])@([A-Za-z0-9][A-Za-z0-9._-]*)")


def extract_mention_usernames(content):
    """Return the set of lowercased usernames referenced with @ in content."""
    if not content:
        return set()
    handles = set()
    for raw in _MENTION_RE.findall(content):
        # Trim trailing punctuation that commonly follows a handle in prose.
        handle = raw.rstrip(".-_")
        if handle:
            handles.add(handle.lower())
    return handles


def resolve_mentioned_users(content, exclude_user_id=None):
    """Resolve @handles in content to active User rows (excluding the author)."""
    handles = extract_mention_usernames(content)
    if not handles:
        return []

    from app.models import User

    query = User.query.filter(db.func.lower(User.username).in_(handles), User.is_active.is_(True))
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.all()


def _mention_target(comment):
    """Return (label, url) describing where the comment lives, for the note."""
    from flask import url_for

    if comment.task_id:
        try:
            url = url_for("tasks.view_task", task_id=comment.task_id)
        except Exception:
            url = None
        return (comment.target_name, url)
    if comment.project_id:
        try:
            url = url_for("projects.view_project", project_id=comment.project_id)
        except Exception:
            url = None
        return (comment.target_name, url)
    if comment.quote_id:
        try:
            url = url_for("quotes.view_quote", quote_id=comment.quote_id)
        except Exception:
            url = None
        return (comment.target_name, url)
    return (comment.target_name, None)


def _build_note(comment, actor):
    """Build the push/socket payload for a mention notification."""
    actor_name = getattr(actor, "display_name", None) or getattr(actor, "username", None) or "Someone"
    label, url = _mention_target(comment)
    snippet = (comment.content or "").strip()
    if len(snippet) > 140:
        snippet = snippet[:137] + "…"
    where = f" in {label}" if label and label != "Unknown" else ""
    return {
        "kind": "mention",
        "title": f"{actor_name} mentioned you",
        "message": f"{actor_name} mentioned you{where}: {snippet}",
        "type": "info",
        "action": url,
        "comment_id": comment.id,
        "target_type": comment.target_type,
    }


def notify_mentioned_users(comment, actor):
    """Notify every user mentioned in the comment (excluding the actor).

    Returns the list of notified user ids. Never raises: notification is a
    best-effort side effect of saving a comment and must not break the request.
    """
    try:
        actor_id = getattr(actor, "id", None)
        users = resolve_mentioned_users(comment.content, exclude_user_id=actor_id)
        if not users:
            return []

        note = _build_note(comment, actor)
        notified = []
        for user in users:
            _deliver_web_push(user, note)
            _emit_socket(user, note)
            notified.append(user.id)
        return notified
    except Exception:
        # Best-effort: log at debug via app logger if available, else swallow.
        try:
            from flask import current_app

            current_app.logger.debug("mention notification failed", exc_info=True)
        except Exception:
            pass
        return []


def _deliver_web_push(user, note):
    """Send the mention as a web-push to the user's subscriptions, if any."""
    try:
        from app.models import PushSubscription
        from app.utils.scheduled_tasks import _deliver_push_to_subscriptions

        subscriptions = PushSubscription.get_user_subscriptions(user.id)
        if subscriptions:
            _deliver_push_to_subscriptions(user, subscriptions, note)
    except Exception:
        pass


def _emit_socket(user, note):
    """Emit a real-time mention event to the user's Socket.IO room."""
    try:
        from app import socketio

        socketio.emit("user_mentioned", note, room=f"user_{user.id}")
    except Exception:
        pass
