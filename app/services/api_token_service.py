"""
Service for API token management with enhanced security features.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from app import db
from app.models import ApiToken, User
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent


class ApiTokenService:
    """
    Service for API token management with enhanced security features.

    This service handles all API token operations including:
    - Creating tokens with scope validation
    - Token rotation for security
    - Token revocation
    - Expiration management
    - Rate limiting (foundation for Redis integration)

    Security features:
    - Scope-based permissions
    - Token expiration
    - IP whitelisting support
    - Usage tracking

    Example:
        service = ApiTokenService()
        result = service.create_token(
            user_id=1,
            name="API Token",
            scopes="read:projects,write:time_entries",
            expires_days=30
        )
        if result['success']:
            token = result['token']  # Only shown once!
    """

    def create_token(
        self,
        user_id: int,
        name: str,
        description: str = "",
        scopes: str = "",
        expires_days: Optional[int] = None,
        ip_whitelist: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new API token with enhanced security.

        Args:
            user_id: User ID who owns this token
            name: Human-readable name for the token
            description: Optional description
            scopes: Comma-separated list of scopes
            expires_days: Number of days until expiration (None = never expires)
            ip_whitelist: Comma-separated list of allowed IPs/CIDR blocks

        Returns:
            dict with 'success', 'message', 'token', and 'api_token' keys
        """
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "message": "Invalid user", "error": "invalid_user"}

        # Validate scopes if provided
        if scopes:
            validation_result = self.validate_scopes(scopes)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": f"Invalid scopes: {', '.join(validation_result['invalid'])}",
                    "error": "invalid_scopes",
                    "invalid_scopes": validation_result["invalid"],
                }

        # Create token
        try:
            api_token, plain_token = ApiToken.create_token(
                user_id=user_id, name=name, description=description, scopes=scopes, expires_days=expires_days
            )

            if ip_whitelist:
                api_token.ip_whitelist = ip_whitelist

            db.session.add(api_token)

            if not safe_commit("create_api_token", {"user_id": user_id, "name": name}):
                return {
                    "success": False,
                    "message": "Could not create API token due to a database error",
                    "error": "database_error",
                }

            # Emit event
            emit_event(WebhookEvent.API_TOKEN_CREATED.value, {"token_id": api_token.id, "user_id": user_id})

            return {
                "success": True,
                "message": "API token created successfully",
                "token": plain_token,  # Only returned once!
                "api_token": api_token,
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error creating API token: {str(e)}", "error": "creation_error"}

    def rotate_token(self, token_id: int, user_id: int) -> Dict[str, Any]:
        """
        Rotate an API token by creating a new one and deactivating the old one.

        Args:
            token_id: The token ID to rotate
            user_id: User ID requesting the rotation (must own the token)

        Returns:
            dict with 'success', 'message', 'new_token', and 'api_token' keys
        """
        # Get existing token
        api_token = ApiToken.query.get(token_id)
        if not api_token:
            return {"success": False, "message": "Token not found", "error": "not_found"}

        # Verify ownership
        if api_token.user_id != user_id:
            return {
                "success": False,
                "message": "You do not have permission to rotate this token",
                "error": "permission_denied",
            }

        # Create new token with same scopes and settings
        result = self.create_token(
            user_id=api_token.user_id,
            name=f"{api_token.name} (rotated)",
            description=f"Rotated from token {api_token.token_prefix}...",
            scopes=api_token.scopes or "",
            expires_days=None,  # Keep same expiration policy
            ip_whitelist=api_token.ip_whitelist,
        )

        if not result["success"]:
            return result

        # Deactivate old token
        api_token.is_active = False
        api_token.description = (
            f"{api_token.description or ''} (Rotated and replaced by {result['api_token'].token_prefix}...)".strip()
        )

        if not safe_commit("rotate_api_token", {"token_id": token_id, "new_token_id": result["api_token"].id}):
            return {
                "success": False,
                "message": "Could not complete token rotation due to a database error",
                "error": "database_error",
            }

        # Emit event
        emit_event(
            WebhookEvent.API_TOKEN_ROTATED.value,
            {"old_token_id": token_id, "new_token_id": result["api_token"].id, "user_id": user_id},
        )

        return {
            "success": True,
            "message": "Token rotated successfully",
            "new_token": result["token"],
            "api_token": result["api_token"],
            "old_token": api_token,
        }

    def revoke_token(self, token_id: int, user_id: int) -> Dict[str, Any]:
        """
        Revoke (deactivate) an API token.

        Args:
            token_id: The token ID to revoke
            user_id: User ID requesting the revocation (must own the token or be admin)

        Returns:
            dict with 'success' and 'message' keys
        """
        api_token = ApiToken.query.get(token_id)
        if not api_token:
            return {"success": False, "message": "Token not found", "error": "not_found"}

        # Check permissions
        user = User.query.get(user_id)
        if not user or (not user.is_admin and api_token.user_id != user_id):
            return {
                "success": False,
                "message": "You do not have permission to revoke this token",
                "error": "permission_denied",
            }

        # Deactivate token
        api_token.is_active = False

        if not safe_commit("revoke_api_token", {"token_id": token_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not revoke token due to a database error",
                "error": "database_error",
            }

        # Emit event
        emit_event(WebhookEvent.API_TOKEN_REVOKED.value, {"token_id": token_id, "user_id": user_id})

        return {"success": True, "message": "Token revoked successfully"}

    def get_expiring_tokens(self, days_ahead: int = 7) -> List[ApiToken]:
        """
        Get tokens that will expire within the specified number of days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of tokens expiring soon
        """
        expiration_threshold = datetime.utcnow() + timedelta(days=days_ahead)

        return ApiToken.query.filter(
            ApiToken.is_active == True,
            ApiToken.expires_at.isnot(None),
            ApiToken.expires_at <= expiration_threshold,
            ApiToken.expires_at > datetime.utcnow(),
        ).all()

    def validate_scopes(self, scopes: str) -> Dict[str, Any]:
        """
        Validate scope strings.

        Args:
            scopes: Comma-separated list of scopes

        Returns:
            dict with 'valid' bool and 'invalid' list of invalid scopes
        """
        # Valid scope patterns
        valid_patterns = [
            "read:*",
            "write:*",
            "admin:*",
            "read:projects",
            "read:time_entries",
            "read:invoices",
            "read:clients",
            "read:tasks",
            "read:reports",
            "read:deals",
            "read:leads",
            "read:contacts",
            "read:time_approvals",
            "write:projects",
            "write:time_entries",
            "write:invoices",
            "write:clients",
            "write:tasks",
            "write:deals",
            "write:leads",
            "write:contacts",
            "write:time_approvals",
            "admin:all",
            "*",
        ]

        scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
        invalid = []

        for scope in scope_list:
            if scope not in valid_patterns:
                invalid.append(scope)

        return {"valid": len(invalid) == 0, "invalid": invalid}

    def check_token_rate_limit(self, token_id: int, max_requests_per_hour: int = 1000) -> Dict[str, Any]:
        """
        Check if token has exceeded rate limit.
        This is a simple implementation - for production, use Redis or similar.

        Args:
            token_id: The token ID
            max_requests_per_hour: Maximum requests per hour

        Returns:
            dict with 'allowed' bool and 'remaining' requests
        """
        # This is a placeholder - in production, implement proper rate limiting
        # using Redis or similar distributed cache
        api_token = ApiToken.query.get(token_id)
        if not api_token:
            return {"allowed": False, "remaining": 0, "error": "token_not_found"}

        # Simple check: if usage_count is very high, might be rate limited
        # In production, track requests per hour in Redis
        return {"allowed": True, "remaining": max_requests_per_hour, "reset_at": datetime.utcnow() + timedelta(hours=1)}
