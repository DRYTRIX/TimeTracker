"""OAuth 2.0 API application models (authorization server scaffolding).

Full Authlib integration is described in docs/design/OAUTH2_API_APPS.md.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import relationship

from app import db


class OAuthApplication(db.Model):
    """Registered third-party OAuth client (confidential or public)."""

    __tablename__ = "oauth_applications"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_secret_hash = db.Column(db.String(128), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", backref="oauth_applications")

    redirect_uris = db.Column(db.JSON, nullable=False, default=list)
    allowed_scopes = db.Column(db.Text, default="", nullable=False)
    grant_types = db.Column(db.JSON, nullable=False, default=lambda: ["authorization_code"])

    is_confidential = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    authorization_codes = relationship(
        "OAuthAuthorizationCode",
        back_populates="application",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<OAuthApplication {self.name} ({self.client_id})>"

    @staticmethod
    def generate_client_id() -> str:
        return f"tt_app_{secrets.token_urlsafe(16)[:24]}"

    @staticmethod
    def generate_client_secret() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_secret(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @classmethod
    def create_application(
        cls,
        owner_user_id: int,
        name: str,
        redirect_uris: list,
        *,
        description: str = "",
        allowed_scopes: str = "",
        is_confidential: bool = True,
    ) -> tuple[OAuthApplication, str | None]:
        """Create a new OAuth application. Returns (instance, plain_client_secret)."""
        client_id = cls.generate_client_id()
        plain_secret = cls.generate_client_secret() if is_confidential else None
        app_record = cls(
            client_id=client_id,
            client_secret_hash=cls.hash_secret(plain_secret) if plain_secret else None,
            name=name,
            description=description or None,
            owner_user_id=owner_user_id,
            redirect_uris=list(redirect_uris or []),
            allowed_scopes=allowed_scopes or "",
            is_confidential=is_confidential,
        )
        return app_record, plain_secret

    def scope_list(self) -> list[str]:
        if not self.allowed_scopes:
            return []
        return [s.strip() for s in self.allowed_scopes.split(",") if s.strip()]

    def redirect_uri_list(self) -> list[str]:
        if isinstance(self.redirect_uris, list):
            return self.redirect_uris
        if isinstance(self.redirect_uris, str):
            try:
                parsed = json.loads(self.redirect_uris)
                return parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError):
                return []
        return []

    def to_dict(self, include_secret: bool = False) -> dict:
        data = {
            "id": self.id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "redirect_uris": self.redirect_uri_list(),
            "allowed_scopes": self.scope_list(),
            "grant_types": self.grant_types or ["authorization_code"],
            "is_confidential": self.is_confidential,
            "is_active": self.is_active,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret:
            data["client_secret"] = "***"
        return data


class OAuthAuthorizationCode(db.Model):
    """Short-lived authorization code (PKCE-ready stub)."""

    __tablename__ = "oauth_authorization_codes"

    id = db.Column(db.Integer, primary_key=True)
    code_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)

    application_id = db.Column(db.Integer, db.ForeignKey("oauth_applications.id"), nullable=False, index=True)
    application = relationship("OAuthApplication", back_populates="authorization_codes")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", backref="oauth_authorization_codes")

    redirect_uri = db.Column(db.String(500), nullable=False)
    scope = db.Column(db.Text, default="", nullable=False)

    code_challenge = db.Column(db.String(128), nullable=True)
    code_challenge_method = db.Column(db.String(10), nullable=True)

    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<OAuthAuthorizationCode app={self.application_id} user={self.user_id}>"

    @staticmethod
    def generate_code() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def create_code(
        cls,
        application_id: int,
        user_id: int,
        redirect_uri: str,
        scope: str = "",
        *,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        ttl_seconds: int = 600,
    ) -> tuple[OAuthAuthorizationCode, str]:
        plain_code = cls.generate_code()
        record = cls(
            code_hash=cls.hash_code(plain_code),
            application_id=application_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope or "",
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )
        return record, plain_code

    def is_valid(self) -> bool:
        if self.used_at is not None:
            return False
        return self.expires_at >= datetime.utcnow()
