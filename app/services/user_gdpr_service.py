"""GDPR right-to-erasure: anonymize user records while preserving FK integrity."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app import db
from app.models import ApiToken, AuditLog, User
from app.utils.db import safe_commit
from app.utils.deleted_usernames import reserve_deleted_username


ANONYMOUS_USERNAME_PREFIX = "deleted_user_"
ANONYMOUS_DISPLAY_SUFFIX = " (anonymized)"


class UserGdprService:
    """Anonymize a user account per GDPR erasure requests."""

    def anonymize_user(
        self,
        user_id: int,
        actor_id: Optional[int],
        *,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "message": "User not found", "error": "not_found"}

        if getattr(user, "anonymized_at", None):
            return {"success": False, "message": "User is already anonymized", "error": "already_anonymized"}

        if user.is_admin:
            admin_count = User.query.filter(User.role == "admin", User.is_active == True).count()  # noqa: E712
            other_admins = admin_count - (1 if user.is_active else 0)
            if user.is_active and other_admins < 1:
                return {
                    "success": False,
                    "message": "Cannot anonymize the last active administrator",
                    "error": "last_admin",
                }

        original_username = user.username
        reserve_deleted_username(original_username, deleted_by_user_id=actor_id)

        new_username = f"{ANONYMOUS_USERNAME_PREFIX}{user.id}"
        # Ensure unique username if re-run edge case
        if User.query.filter(User.username == new_username, User.id != user.id).first():
            new_username = f"{ANONYMOUS_USERNAME_PREFIX}{user.id}_{user.id}"

        user.username = new_username
        user.email = None
        user.full_name = f"Anonymized User #{user.id}"
        user.password_hash = None
        user.password_change_required = False
        user.oidc_sub = None
        user.oidc_issuer = None
        user.auth_provider = "local"
        user.avatar_filename = None
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_confirmed_at = None
        user.github_username = None
        user.slack_user_id = None
        user.other_employers_note = None
        user.client_portal_enabled = False
        user.client_id = None
        user.portal_only = False
        user.is_active = False
        user.anonymized_at = datetime.utcnow()

        ApiToken.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        AuditLog.log_change(
            user_id=actor_id,
            action="anonymized",
            entity_type="user",
            entity_id=user.id,
            entity_name=original_username,
            change_description="GDPR erasure: user PII cleared; historical time entries retained",
            reason=reason,
            entity_metadata={"original_username": original_username},
        )

        if not safe_commit("gdpr_anonymize_user", {"user_id": user_id, "actor_id": actor_id}):
            return {
                "success": False,
                "message": "Could not anonymize user due to a database error",
                "error": "database_error",
            }

        return {
            "success": True,
            "message": "User anonymized successfully",
            "user_id": user.id,
            "username": user.username,
        }
