"""
LDAP authentication: service-account search, optional group checks, user bind, DB sync.
"""

from __future__ import annotations

import logging
import re
import secrets
from typing import Any, Mapping, MutableMapping, Optional

from flask import current_app

from app import db
from app.models import User
from app.utils.db import safe_commit
from app.utils.deleted_usernames import is_username_reserved

logger = logging.getLogger(__name__)

# LDAP attribute / objectClass names: letters, digits, hyphen, semicolon (OID option)
_LDAP_ATTR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9;-]*$")
# Conservative DN shape: one or more RDN components attr=value
_LDAP_DN_RE = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9;-]*=(?:\\.|[^,\\+<>;#\"=])+)"
    r"(?:,(?:[A-Za-z][A-Za-z0-9;-]*=(?:\\.|[^,\\+<>;#\"=])+))*$"
)

try:
    from ldap3 import SIMPLE, SUBTREE, Connection, Server, Tls
    from ldap3.core.exceptions import LDAPException
    from ldap3.utils.conv import escape_filter_chars
except ImportError:  # pragma: no cover - exercised when ldap3 missing
    Connection = None  # type: ignore[misc, assignment]
    Server = None  # type: ignore[misc, assignment]
    LDAPException = Exception  # type: ignore[misc, assignment]
    escape_filter_chars = None  # type: ignore[misc, assignment]


def _config() -> MutableMapping[str, Any]:
    return current_app.config


def _safe_ldap_attr(name: str, default: str) -> str:
    """Return attr/objectClass name if charset-safe, else default."""
    candidate = (name or "").strip() or default
    if _LDAP_ATTR_RE.match(candidate):
        return candidate
    return default


def _validate_dn(dn: str) -> str:
    """
    Validate a DN string used as search_base.

    Rejects empty/malformed values so admin wizard input cannot inject filter
    metacharacters via the base DN. Values are not filter-escaped (DNs are not
    filter strings); they must match a conservative DN pattern.
    """
    cleaned = (dn or "").strip().strip(",")
    if not cleaned:
        return ""
    if len(cleaned) > 1024:
        raise ValueError("LDAP DN too long")
    if not _LDAP_DN_RE.match(cleaned):
        raise ValueError("Invalid LDAP DN")
    return cleaned


def _group_search_base(cfg: Mapping[str, Any]) -> str:
    gdn = _validate_dn(cfg.get("LDAP_GROUP_DN") or "")
    bdn = _validate_dn(cfg.get("LDAP_BASE_DN") or "")
    if not gdn:
        return bdn
    if not bdn:
        return gdn
    return f"{gdn},{bdn}"


def _user_search_base(cfg: Mapping[str, Any]) -> str:
    udn = _validate_dn(cfg.get("LDAP_USER_DN") or "")
    bdn = _validate_dn(cfg.get("LDAP_BASE_DN") or "")
    if not udn:
        return bdn
    if not bdn:
        return udn
    return f"{udn},{bdn}"


def _make_server(cfg: Mapping[str, Any]) -> Any:
    host = (cfg.get("LDAP_HOST") or "localhost").strip()
    port = int(cfg.get("LDAP_PORT") or 389)
    use_ssl = bool(cfg.get("LDAP_USE_SSL"))
    timeout = int(cfg.get("LDAP_TIMEOUT") or 10)
    ca_file = (cfg.get("LDAP_TLS_CA_CERT_FILE") or "").strip()
    tls = None
    if ca_file:
        tls = Tls(ca_certs_file=ca_file)
    return Server(
        host,
        port=port,
        use_ssl=use_ssl,
        get_info=None,
        connect_timeout=timeout,
        tls=tls,
    )


def _service_connection(cfg: Mapping[str, Any]) -> Optional[Any]:
    if Connection is None or Server is None:
        return None
    server = _make_server(cfg)
    bind_dn = (cfg.get("LDAP_BIND_DN") or "").strip()
    bind_pw = cfg.get("LDAP_BIND_PASSWORD") or ""
    timeout = int(cfg.get("LDAP_TIMEOUT") or 10)
    conn = Connection(
        server,
        user=bind_dn,
        password=bind_pw,
        authentication=SIMPLE,
        receive_timeout=timeout,
        auto_bind=False,
    )
    conn.open()
    if cfg.get("LDAP_USE_TLS") and not cfg.get("LDAP_USE_SSL"):
        conn.start_tls(read_server_info=False)
    conn.bind()
    return conn


def _user_dn_member_of_group(
    conn: Any,
    cfg: Mapping[str, Any],
    group_cn: str,
    user_dn: str,
) -> bool:
    group_cn = (group_cn or "").strip()
    if not group_cn or not user_dn:
        return False
    try:
        base = _group_search_base(cfg)
    except ValueError:
        return False
    if not base:
        return False
    oc = escape_filter_chars(_safe_ldap_attr(cfg.get("LDAP_GROUP_OBJECT_CLASS") or "groupOfNames", "groupOfNames"))
    cn_esc = escape_filter_chars(group_cn)
    ud_esc = escape_filter_chars(user_dn)
    filt = f"(&(objectClass={oc})(cn={cn_esc})(member={ud_esc}))"
    conn.search(search_base=base, search_filter=filt, search_scope=SUBTREE, size_limit=1, attributes=["1.1"])
    return bool(conn.entries)


class LDAPService:
    """LDAP bind-authenticate and sync users to the local User model."""

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[User]:
        """
        Validate credentials against LDAP and return the linked User, or None.

        Never raises LDAP errors to callers; failures are logged at WARNING without passwords.
        """
        if Connection is None:
            logger.warning("LDAP authenticate skipped: ldap3 is not installed")
            return None

        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            return None

        cfg = _config()
        svc_conn = None
        try:
            try:
                svc_conn = _service_connection(cfg)
            except LDAPException:
                logger.warning("LDAP service bind failed")
                return None
            except Exception:
                logger.warning("LDAP service connection error")
                return None

            if not svc_conn:
                return None

            try:
                user_base = _user_search_base(cfg)
            except ValueError:
                logger.warning("LDAP user search base invalid")
                return None
            if not user_base:
                logger.warning("LDAP user search base empty")
                return None
            login_attr = _safe_ldap_attr(cfg.get("LDAP_USER_LOGIN_ATTR") or "uid", "uid")
            user_oc = _safe_ldap_attr(cfg.get("LDAP_USER_OBJECT_CLASS") or "inetOrgPerson", "inetOrgPerson")
            u_esc = escape_filter_chars(username.lower())
            la_esc = escape_filter_chars(login_attr)
            oc_esc = escape_filter_chars(user_oc)
            filt = f"(&(objectClass={oc_esc})({la_esc}={u_esc}))"
            fetch_attrs = {
                _safe_ldap_attr(cfg.get("LDAP_USER_LOGIN_ATTR") or "uid", "uid"),
                _safe_ldap_attr(cfg.get("LDAP_USER_EMAIL_ATTR") or "mail", "mail"),
                _safe_ldap_attr(cfg.get("LDAP_USER_FNAME_ATTR") or "givenName", "givenName"),
                _safe_ldap_attr(cfg.get("LDAP_USER_LNAME_ATTR") or "sn", "sn"),
            }
            svc_conn.search(
                search_base=user_base,
                search_filter=filt,
                search_scope=SUBTREE,
                size_limit=2,
                attributes=list(fetch_attrs),
            )

            if not svc_conn.entries:
                logger.warning("LDAP user not found for login attribute match")
                return None
            if len(svc_conn.entries) > 1:
                logger.warning("LDAP search returned multiple entries; refusing login")
                return None

            entry = svc_conn.entries[0]
            user_dn = entry.entry_dn
            attrs = entry.entry_attributes_as_dict

            req_group = (cfg.get("LDAP_REQUIRED_GROUP") or "").strip()
            if req_group and not _user_dn_member_of_group(svc_conn, cfg, req_group, user_dn):
                logger.warning("LDAP user not in required group")
                return None

            try:
                if svc_conn.bound:
                    svc_conn.unbind()
            except Exception:
                pass
            svc_conn = None

            try:
                user_conn = Connection(
                    _make_server(cfg),
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    receive_timeout=int(cfg.get("LDAP_TIMEOUT") or 10),
                    auto_bind=True,
                )
                user_conn.unbind()
            except LDAPException:
                logger.warning("LDAP user bind failed")
                return None
            except Exception:
                logger.warning("LDAP user bind error")
                return None

            ldap_attrs = LDAPService._entry_to_attrs(cfg, attrs, username.lower())
            if not ldap_attrs.get("email"):
                logger.warning("LDAP user has no email; cannot provision local user")
                return None

            admin_group = (cfg.get("LDAP_ADMIN_GROUP") or "").strip()
            is_admin = False
            if admin_group:
                try:
                    c2 = _service_connection(cfg)
                    if c2:
                        is_admin = _user_dn_member_of_group(c2, cfg, admin_group, user_dn)
                        c2.unbind()
                except LDAPException:
                    pass

            synced = LDAPService._get_or_create_user(cfg, ldap_attrs, is_admin_member=is_admin)
            if not synced:
                logger.warning("LDAP user could not be persisted to the database")
                return None
            return synced
        except LDAPException:
            logger.warning("LDAP authenticate failed")
            return None
        except Exception:
            logger.warning("LDAP authenticate unexpected error")
            return None
        finally:
            if svc_conn is not None:
                try:
                    if svc_conn.bound:
                        svc_conn.unbind()
                except Exception:
                    pass

    @staticmethod
    def _entry_to_attrs(
        cfg: Mapping[str, Any],
        raw_attrs: Mapping[str, Any],
        username_lower: str,
    ) -> dict[str, Optional[str]]:
        def first(attr: str) -> Optional[str]:
            if not attr:
                return None
            vals = raw_attrs.get(attr) or []
            if not vals:
                return None
            v = vals[0]
            if hasattr(v, "value"):
                v = v.value
            s = str(v).strip()
            return s or None

        login_attr = (cfg.get("LDAP_USER_LOGIN_ATTR") or "uid").strip()
        email_attr = (cfg.get("LDAP_USER_EMAIL_ATTR") or "mail").strip()
        fn_attr = (cfg.get("LDAP_USER_FNAME_ATTR") or "givenName").strip()
        ln_attr = (cfg.get("LDAP_USER_LNAME_ATTR") or "sn").strip()

        email = first(email_attr)
        if email:
            email = email.lower()
        fn = first(fn_attr) or ""
        ln = first(ln_attr) or ""
        parts = [p for p in (fn.strip(), ln.strip()) if p]
        full_name = " ".join(parts).strip() or None

        un = first(login_attr) or username_lower
        if un:
            un = un.lower().strip()

        return {
            "username": un or username_lower,
            "email": email,
            "full_name": full_name,
        }

    @staticmethod
    def _get_or_create_user(
        cfg: Mapping[str, Any],
        ldap_attrs: Mapping[str, Any],
        *,
        is_admin_member: bool,
    ) -> Optional[User]:
        """Create or update a User from LDAP attributes; commit and return user, or None on DB failure."""
        email = ldap_attrs.get("email")
        username = ldap_attrs.get("username") or ""
        full_name = ldap_attrs.get("full_name")

        user = User.query.filter_by(email=email).first() if email else None
        if not user:
            if is_username_reserved(username):
                logger.warning("LDAP user create blocked: username reserved after deletion")
                return None
            role_name = "admin" if is_admin_member else "user"
            user = User(username=username, role=role_name, email=email, full_name=full_name)
            user.auth_provider = "ldap"
            user.set_password(secrets.token_urlsafe(48))
            user.is_active = True
            try:
                from app.models import Role

                role_obj = Role.query.filter_by(name=role_name).first()
                if role_obj:
                    user.roles.append(role_obj)
            except Exception:
                pass
            try:
                from app.models import Settings

                settings = Settings.get_settings()
                user.standard_hours_per_day = float(getattr(settings, "default_daily_working_hours", 8.0) or 8.0)
            except Exception:
                pass
            db.session.add(user)
        else:
            user.auth_provider = "ldap"
            if username and user.username != username:
                user.username = username
            if full_name is not None:
                user.full_name = full_name
            if email and user.email != email:
                user.email = email

        if is_admin_member:
            if user.role != "admin":
                user.role = "admin"
        else:
            if user.role == "admin" and getattr(user, "auth_provider", None) == "ldap":
                user.role = "user"

        if not safe_commit("ldap_sync_user", {"user_id": getattr(user, "id", None), "email": email}):
            db.session.rollback()
            logger.warning("LDAP user DB commit failed")
            return None

        return User.query.filter_by(email=email).first() or user

    @staticmethod
    def test_connection(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """
        Verify service bind and count users under the user subtree.

        If ``cfg`` is None, uses ``current_app.config`` (e.g. admin settings test).
        If ``cfg`` is a mapping, uses only those keys (e.g. setup wizard draft).

        Returns dict: success (bool), message (str), user_count (int|None).
        Never raises.
        """
        if Connection is None:
            return {"success": False, "message": "ldap3 is not installed", "user_count": None}
        conn = None
        effective_cfg: Mapping[str, Any] = cfg if cfg is not None else _config()
        try:
            conn = _service_connection(effective_cfg)
            if not conn:
                return {"success": False, "message": "Could not create LDAP connection", "user_count": None}
        except LDAPException as e:
            return {"success": False, "message": f"LDAP error: {type(e).__name__}", "user_count": None}
        except Exception as e:
            return {"success": False, "message": f"Error: {type(e).__name__}", "user_count": None}

        try:
            try:
                user_base = _user_search_base(effective_cfg)
            except ValueError as e:
                return {"success": False, "message": str(e), "user_count": None}
            if not user_base:
                return {"success": False, "message": "LDAP base DN is required", "user_count": None}
            user_oc_raw = _safe_ldap_attr(
                effective_cfg.get("LDAP_USER_OBJECT_CLASS") or "inetOrgPerson",
                "inetOrgPerson",
            )
            user_oc = escape_filter_chars(user_oc_raw)
            filt = f"(objectClass={user_oc})"
            conn.search(
                search_base=user_base,
                search_filter=filt,
                search_scope=SUBTREE,
                attributes=["1.1"],
                size_limit=2001,
            )
            n = len(conn.entries)
            if n > 2000:
                return {
                    "success": True,
                    "message": "Connected; user count exceeds 2000 (showing as 2000+)",
                    "user_count": n,
                }
            return {"success": True, "message": "Connected successfully", "user_count": n}
        except LDAPException as e:
            return {"success": False, "message": f"LDAP search failed: {type(e).__name__}", "user_count": None}
        except Exception as e:
            return {"success": False, "message": f"Search error: {type(e).__name__}", "user_count": None}
        finally:
            try:
                conn.unbind()
            except Exception:
                pass
