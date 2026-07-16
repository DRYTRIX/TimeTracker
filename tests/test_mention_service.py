"""Tests for @mention detection and notification (app/services/mention_service.py)."""

from app import db
from app.models import Comment, User
from app.services import mention_service

# ---------------------------------------------------------------------------
# extract_mention_usernames
# ---------------------------------------------------------------------------


def test_extract_single_mention():
    assert mention_service.extract_mention_usernames("hey @alice") == {"alice"}


def test_extract_multiple_mentions():
    handles = mention_service.extract_mention_usernames("@alice and @bob, also @Carol")
    assert handles == {"alice", "bob", "carol"}


def test_extract_lowercases_handles():
    assert mention_service.extract_mention_usernames("ping @AliceBob") == {"alicebob"}


def test_extract_trims_trailing_punctuation():
    # A handle at the end of a sentence should not keep the period.
    assert mention_service.extract_mention_usernames("thanks @dave.") == {"dave"}


def test_extract_ignores_email_addresses():
    # The "@" in an email is preceded by a word char and must not match.
    assert mention_service.extract_mention_usernames("mail me at bob@example.com") == set()


def test_extract_handles_dotted_and_hyphenated_names():
    handles = mention_service.extract_mention_usernames("@jane.doe and @mary-sue")
    assert handles == {"jane.doe", "mary-sue"}


def test_extract_empty_content():
    assert mention_service.extract_mention_usernames("") == set()
    assert mention_service.extract_mention_usernames(None) == set()


# ---------------------------------------------------------------------------
# resolve_mentioned_users
# ---------------------------------------------------------------------------


def test_resolve_matches_active_user(app, user):
    resolved = mention_service.resolve_mentioned_users(f"hi @{user.username}")
    assert [u.id for u in resolved] == [user.id]


def test_resolve_is_case_insensitive(app, user):
    resolved = mention_service.resolve_mentioned_users(f"hi @{user.username.upper()}")
    assert [u.id for u in resolved] == [user.id]


def test_resolve_excludes_author(app, user):
    resolved = mention_service.resolve_mentioned_users(f"@{user.username}", exclude_user_id=user.id)
    assert resolved == []


def test_resolve_skips_inactive_users(app):
    ghost = User(username="ghost_mention", role="user", email="ghost@example.com")
    ghost.is_active = False
    db.session.add(ghost)
    db.session.commit()
    resolved = mention_service.resolve_mentioned_users("@ghost_mention")
    assert resolved == []


def test_resolve_no_handles_returns_empty(app, user):
    assert mention_service.resolve_mentioned_users("no mentions here") == []


# ---------------------------------------------------------------------------
# notify_mentioned_users (best-effort, never raises)
# ---------------------------------------------------------------------------


def test_notify_returns_mentioned_ids(app, user, project):
    actor = User(username="mention_actor", role="user", email="actor@example.com")
    actor.is_active = True
    db.session.add(actor)
    db.session.commit()

    comment = Comment(content=f"cc @{user.username}", user_id=actor.id, project_id=project.id)
    db.session.add(comment)
    db.session.commit()

    notified = mention_service.notify_mentioned_users(comment, actor)
    assert notified == [user.id]


def test_notify_excludes_the_actor(app, user, project):
    comment = Comment(
        content=f"note to self @{user.username}",
        user_id=user.id,
        project_id=project.id,
    )
    db.session.add(comment)
    db.session.commit()

    notified = mention_service.notify_mentioned_users(comment, user)
    assert notified == []


def test_notify_never_raises_on_bad_comment(app, user):
    # Passing a bare object with no content must not blow up the caller.
    class _Broken:
        content = None
        task_id = None
        project_id = None
        quote_id = None
        id = None
        target_type = None

    assert mention_service.notify_mentioned_users(_Broken(), user) == []


# ---------------------------------------------------------------------------
# /api/users/search endpoint
# ---------------------------------------------------------------------------


def test_search_users_endpoint_requires_login(client):
    resp = client.get("/api/users/search")
    # Unauthenticated request is redirected to login or rejected.
    assert resp.status_code in (301, 302, 401, 403)


def test_search_users_endpoint_filters_by_query(authenticated_client, user):
    resp = authenticated_client.get(f"/api/users/search?q={user.username}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "users" in data
    usernames = [u["username"] for u in data["users"]]
    assert user.username in usernames


def test_search_users_endpoint_returns_display_name(authenticated_client, user):
    resp = authenticated_client.get("/api/users/search")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["users"], list)
    if data["users"]:
        assert {"id", "username", "display_name"} <= set(data["users"][0].keys())
