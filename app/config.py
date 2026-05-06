import os
from datetime import timedelta


class Config:
    """Base configuration class"""

    # Flask settings
    # In production, SECRET_KEY MUST be set via the SECRET_KEY environment variable.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    _SECRET_KEY_IS_DEFAULT = SECRET_KEY == "dev-secret-key-change-in-production"
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Database settings (default to PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@localhost:5432/timetracker"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Session settings
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv("PERMANENT_SESSION_LIFETIME", 86400)))

    # Flask-Login remember cookie settings
    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.getenv("REMEMBER_COOKIE_DAYS", 365)))
    REMEMBER_COOKIE_SECURE = os.getenv("REMEMBER_COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.getenv("REMEMBER_COOKIE_SAMESITE", "Lax")

    # Application settings
    TZ = os.getenv("TZ", "Europe/Rome")
    CURRENCY = os.getenv("CURRENCY", "EUR")
    ROUNDING_MINUTES = int(os.getenv("ROUNDING_MINUTES", 1))
    SINGLE_ACTIVE_TIMER = os.getenv("SINGLE_ACTIVE_TIMER", "true").lower() == "true"
    IDLE_TIMEOUT_MINUTES = int(os.getenv("IDLE_TIMEOUT_MINUTES", 30))

    # User management (default false for production-safe deployments)
    ALLOW_SELF_REGISTER = os.getenv("ALLOW_SELF_REGISTER", "false").lower() == "true"
    ADMIN_USERNAMES = [u.strip() for u in os.getenv("ADMIN_USERNAMES", "admin").split(",") if u.strip()]

    # Demo mode: single fixed user, credentials shown on login, no other account creation
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    DEMO_USERNAME = (os.getenv("DEMO_USERNAME", "demo") or "demo").strip().lower()
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo")

    # API token default expiry (days); 0 or empty = never expire (not recommended for production)
    API_TOKEN_DEFAULT_EXPIRY_DAYS = int(os.getenv("API_TOKEN_DEFAULT_EXPIRY_DAYS", "90"))

    # Per-token REST API rate limits (enforced in require_api_token when Redis or local fallback is used)
    API_TOKEN_RATE_LIMIT_PER_MINUTE = int(os.getenv("API_TOKEN_RATE_LIMIT_PER_MINUTE", "100"))
    API_TOKEN_RATE_LIMIT_PER_HOUR = int(os.getenv("API_TOKEN_RATE_LIMIT_PER_HOUR", "1000"))

    # Authentication method: 'none' | 'local' | 'oidc' | 'ldap' | 'both' | 'all'
    # 'none' = no password authentication (username only)
    # 'local' = password authentication required
    # 'oidc' = OIDC/Single Sign-On only
    # 'ldap' = LDAP bind only
    # 'both' = OIDC + local password (backwards compatible)
    # 'all' = local + OIDC + LDAP
    _auth_method_raw = os.getenv("AUTH_METHOD", "local").strip().lower()
    _auth_method_valid = frozenset({"none", "local", "oidc", "ldap", "both", "all"})
    AUTH_METHOD = _auth_method_raw if _auth_method_raw in _auth_method_valid else "local"

    # LDAP settings (used when AUTH_METHOD is 'ldap' or 'all')
    LDAP_ENABLED = AUTH_METHOD in ("ldap", "all")
    LDAP_HOST = os.environ.get("LDAP_HOST", "localhost")
    LDAP_PORT = int(os.environ.get("LDAP_PORT", "389"))
    LDAP_USE_SSL = os.environ.get("LDAP_USE_SSL", "false").lower() == "true"
    LDAP_USE_TLS = os.environ.get("LDAP_USE_TLS", "false").lower() == "true"
    LDAP_BIND_DN = os.environ.get("LDAP_BIND_DN", "")
    LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "")
    LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "dc=example,dc=com")
    LDAP_USER_DN = os.environ.get("LDAP_USER_DN", "ou=users")
    LDAP_USER_OBJECT_CLASS = os.environ.get("LDAP_USER_OBJECT_CLASS", "inetOrgPerson")
    LDAP_USER_LOGIN_ATTR = os.environ.get("LDAP_USER_LOGIN_ATTR", "uid")
    LDAP_USER_EMAIL_ATTR = os.environ.get("LDAP_USER_EMAIL_ATTR", "mail")
    LDAP_USER_FNAME_ATTR = os.environ.get("LDAP_USER_FNAME_ATTR", "givenName")
    LDAP_USER_LNAME_ATTR = os.environ.get("LDAP_USER_LNAME_ATTR", "sn")
    LDAP_GROUP_DN = os.environ.get("LDAP_GROUP_DN", "ou=groups")
    LDAP_GROUP_OBJECT_CLASS = os.environ.get("LDAP_GROUP_OBJECT_CLASS", "groupOfNames")
    LDAP_ADMIN_GROUP = os.environ.get("LDAP_ADMIN_GROUP", "")
    LDAP_REQUIRED_GROUP = os.environ.get("LDAP_REQUIRED_GROUP", "")
    LDAP_TLS_CA_CERT_FILE = os.environ.get("LDAP_TLS_CA_CERT_FILE", "")
    LDAP_TIMEOUT = int(os.environ.get("LDAP_TIMEOUT", "10"))

    # OIDC settings (used when AUTH_METHOD is 'oidc', 'both', or 'all')
    OIDC_ISSUER = os.getenv("OIDC_ISSUER")  # e.g., https://login.microsoftonline.com/<tenant>/v2.0
    OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
    OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI")  # e.g., https://app.example.com/auth/oidc/callback
    OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid profile email")
    OIDC_USERNAME_CLAIM = os.getenv("OIDC_USERNAME_CLAIM", "preferred_username")
    OIDC_FULL_NAME_CLAIM = os.getenv("OIDC_FULL_NAME_CLAIM", "name")
    OIDC_EMAIL_CLAIM = os.getenv("OIDC_EMAIL_CLAIM", "email")
    OIDC_GROUPS_CLAIM = os.getenv("OIDC_GROUPS_CLAIM", "groups")
    OIDC_ADMIN_GROUP = os.getenv("OIDC_ADMIN_GROUP")  # optional
    OIDC_ADMIN_EMAILS = [e.strip().lower() for e in os.getenv("OIDC_ADMIN_EMAILS", "").split(",") if e.strip()]
    OIDC_POST_LOGOUT_REDIRECT_URI = os.getenv("OIDC_POST_LOGOUT_REDIRECT_URI")

    # OIDC group -> RBAC Role name mapping (JSON object).
    # Example:
    #   OIDC_ROLE_GROUP_MAP='{"timetracker-super-admin":"super_admin","timetracker-admin":"admin","timetracker-manager":"manager","timetracker-viewer":"viewer"}'
    # Empty/invalid JSON disables the feature; the legacy OIDC_ADMIN_GROUP path keeps working.
    _oidc_role_map_raw = os.getenv("OIDC_ROLE_GROUP_MAP", "").strip()
    OIDC_ROLE_GROUP_MAP: dict = {}
    if _oidc_role_map_raw:
        try:
            import json as _json

            _parsed = _json.loads(_oidc_role_map_raw)
            if isinstance(_parsed, dict):
                # Ensure values are strings (Role names)
                OIDC_ROLE_GROUP_MAP = {str(k): str(v) for k, v in _parsed.items() if k and v}
        except Exception:
            # Defer the warning to first OIDC callback so it lands in the app log,
            # but don't crash the app. OIDC_ROLE_GROUP_MAP stays {} = no-op.
            pass

    # Sync mode for OIDC role assignment:
    #   "additive" (default, safe) — only ADD roles matching groups; never revoke.
    #   "sync"                     — also REMOVE mapped roles when the group is gone.
    # Council recommendation: ship additive first, flip to sync only after observing one
    # full re-login cycle for every active user.
    OIDC_ROLE_SYNC_MODE = os.getenv("OIDC_ROLE_SYNC_MODE", "additive").strip().lower()
    if OIDC_ROLE_SYNC_MODE not in ("additive", "sync"):
        OIDC_ROLE_SYNC_MODE = "additive"

    # Escape hatch: user IDs that must NEVER have roles revoked by OIDC sync,
    # regardless of OIDC_ROLE_SYNC_MODE. Comma-separated integers.
    # Strongly recommended for the bootstrap super_admin user (id 1) so a
    # misconfigured OIDC_ROLE_GROUP_MAP cannot lock you out of your own instance.
    OIDC_NEVER_REVOKE_USER_IDS: set = set()
    _never_revoke_raw = os.getenv("OIDC_NEVER_REVOKE_USER_IDS", "").strip()
    if _never_revoke_raw:
        for _x in _never_revoke_raw.split(","):
            _x = _x.strip()
            if _x.isdigit():
                OIDC_NEVER_REVOKE_USER_IDS.add(int(_x))

    # OIDC metadata fetch configuration (for DNS resolution issues)
    OIDC_METADATA_FETCH_TIMEOUT = int(os.getenv("OIDC_METADATA_FETCH_TIMEOUT", 10))  # seconds
    OIDC_METADATA_RETRY_ATTEMPTS = int(os.getenv("OIDC_METADATA_RETRY_ATTEMPTS", 3))  # number of retries
    OIDC_METADATA_RETRY_DELAY = int(os.getenv("OIDC_METADATA_RETRY_DELAY", 2))  # seconds between retries
    # DNS resolution strategy: "auto" (try socket then getaddrinfo), "socket", "getaddrinfo", or "both"
    OIDC_DNS_RESOLUTION_STRATEGY = os.getenv("OIDC_DNS_RESOLUTION_STRATEGY", "auto")
    # TTL for IP address cache in seconds (default: 5 minutes)
    OIDC_IP_CACHE_TTL = int(os.getenv("OIDC_IP_CACHE_TTL", 300))
    # Background metadata refresh interval in seconds (default: 1 hour, 0 to disable)
    OIDC_METADATA_REFRESH_INTERVAL = int(os.getenv("OIDC_METADATA_REFRESH_INTERVAL", 3600))
    # Use IP address directly if DNS resolution succeeds via socket (default: true)
    OIDC_USE_IP_DIRECTLY = os.getenv("OIDC_USE_IP_DIRECTLY", "true").lower() == "true"
    # Try Docker internal service names if external DNS fails (default: true)
    OIDC_USE_DOCKER_INTERNAL = os.getenv("OIDC_USE_DOCKER_INTERNAL", "true").lower() == "true"

    # Donate UI: unlock code verification. Two options (public key preferred; no secret on server).
    #
    # Option A - Ed25519 (recommended): Server only has the PUBLIC key. You keep the private key
    # and sign the system_id to generate codes. Set DONATE_HIDE_PUBLIC_KEY (PEM string) or
    # DONATE_HIDE_PUBLIC_KEY_FILE (path to PEM file). If unset, a file named donate_hide_public.pem
    # in the project root is used when present (local builds and Docker when copied into image).
    _donate_public_key = os.getenv("DONATE_HIDE_PUBLIC_KEY", "").strip()
    if not _donate_public_key:
        _pk_file = os.getenv("DONATE_HIDE_PUBLIC_KEY_FILE", "").strip()
        if not _pk_file:
            # Default: project root (parent of app/) for local builds and Docker (/app)
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _default_pk = os.path.join(_project_root, "donate_hide_public.pem")
            if os.path.isfile(_default_pk):
                _pk_file = _default_pk
        if _pk_file and os.path.isfile(_pk_file):
            try:
                with open(_pk_file, "r", encoding="utf-8") as f:
                    _donate_public_key = f.read().strip()
                # Refuse to load a private key on the server
                if "PRIVATE KEY" in _donate_public_key and "PUBLIC KEY" not in _donate_public_key:
                    _donate_public_key = ""
            except OSError:
                _donate_public_key = ""
    DONATE_HIDE_PUBLIC_KEY_PEM = _donate_public_key
    #
    # Option B - HMAC: Code = HMAC-SHA256(secret, system_id). Requires secret on server.
    # Use DONATE_HIDE_UNLOCK_SECRET or DONATE_HIDE_UNLOCK_SECRET_FILE (path, first line = secret).
    _donate_secret = os.getenv("DONATE_HIDE_UNLOCK_SECRET", "").strip()
    if not _donate_secret:
        _secret_file = os.getenv("DONATE_HIDE_UNLOCK_SECRET_FILE", "").strip()
        if _secret_file and os.path.isfile(_secret_file):
            try:
                with open(_secret_file, "r", encoding="utf-8") as f:
                    _donate_secret = (f.read().strip().split("\n")[0] or "").strip()
            except OSError:
                _donate_secret = ""
    DONATE_HIDE_UNLOCK_SECRET = _donate_secret

    # Support & Purchase Key page URL (for links to purchase a key to hide donate UI)
    SUPPORT_PURCHASE_URL = os.getenv("SUPPORT_PURCHASE_URL", "https://timetracker.drytrix.com/support.html").strip()
    SUPPORT_PORTAL_BASE = os.getenv("SUPPORT_PORTAL_BASE", "https://timetracker.drytrix.com").strip()
    # Optional one-line social proof for support modal (empty = omit block)
    SUPPORT_SOCIAL_PROOF_TEXT = os.getenv("SUPPORT_SOCIAL_PROOF_TEXT", "").strip()

    # Backup settings
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", 30))
    BACKUP_TIME = os.getenv("BACKUP_TIME", "02:00")
    # Optional override for where backup archives are stored.
    # If unset, backups default to: <UPLOAD_FOLDER>/backups
    BACKUP_FOLDER = os.getenv("BACKUP_FOLDER", os.getenv("BACKUP_DIR"))

    # Pagination
    ENTRIES_PER_PAGE = 50
    PROJECTS_PER_PAGE = 20

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    # UPLOAD_FOLDER should be an absolute path (default: /data/uploads)
    # This path is used for storing uploaded files like receipts, avatars, logos, etc.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/data/uploads")

    # CSRF protection
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", 3600))  # Default: 1 hour
    # If true, rejects requests considered insecure for CSRF; keep strict in prod, relaxed in dev
    WTF_CSRF_SSL_STRICT = os.getenv("WTF_CSRF_SSL_STRICT", "true").lower() == "true"
    # Allow trusted cross-origin posts (behind proxies or when Referer/Origin host differs)
    # Comma-separated list of origins, e.g. "https://track.example.com,https://admin.example.com"
    WTF_CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in os.getenv("WTF_CSRF_TRUSTED_ORIGINS", "https://track.example.com").split(",") if o.strip()
    ]
    # CSRF cookie settings (for double-submit cookie pattern and SPA helpers)
    CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "XSRF-TOKEN")
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "").lower()
    # default secure flag: inherit from SESSION_COOKIE_SECURE if unset
    CSRF_COOKIE_SECURE = (
        (CSRF_COOKIE_SECURE == "true") if CSRF_COOKIE_SECURE in ("true", "false") else SESSION_COOKIE_SECURE
    )
    CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "false").lower() == "true"
    CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
    CSRF_COOKIE_DOMAIN = os.getenv("CSRF_COOKIE_DOMAIN")
    CSRF_COOKIE_PATH = os.getenv("CSRF_COOKIE_PATH", "/")

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        # Allow same-origin Referer on HTTPS so CSRF checks that rely on Referer can pass
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    # Performance instrumentation (optional; no production overhead when disabled)
    # Log a single line when request duration exceeds this many milliseconds (0 = disabled)
    PERF_LOG_SLOW_REQUESTS_MS = int(os.getenv("PERF_LOG_SLOW_REQUESTS_MS", "0"))
    # When true, track DB query count per request and include in slow-request logs
    PERF_QUERY_PROFILE = os.getenv("PERF_QUERY_PROFILE", "false").lower() == "true"

    # Rate limiting
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "")  # e.g., "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # Redis configuration
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_DEFAULT_TTL = int(os.getenv("REDIS_DEFAULT_TTL", 3600))  # 1 hour default

    # Internationalization
    LANGUAGES = {
        "en": "English",
        "nl": "Nederlands",
        "de": "Deutsch",
        "fr": "Français",
        "it": "Italiano",
        "fi": "Suomi",
        "es": "Español",
        "pt": "Português",
        "no": "Norsk",
        "ar": "العربية",
        "he": "עברית",
    }
    # RTL languages
    RTL_LANGUAGES = {"ar", "he"}
    BABEL_DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en")
    # Comma-separated list of translation directories relative to instance root
    BABEL_TRANSLATION_DIRECTORIES = os.getenv("BABEL_TRANSLATION_DIRECTORIES", "translations")

    # Versioning
    # Prefer explicit app version from environment (e.g., Git tag)
    APP_VERSION = os.getenv("APP_VERSION", os.getenv("GITHUB_TAG", None))
    if not APP_VERSION:
        # If no tag provided, create a dev-build identifier if available
        github_run_number = os.getenv("GITHUB_RUN_NUMBER")
        APP_VERSION = f"dev-{github_run_number}" if github_run_number else "3.1.0"

    # GitHub release check (admin update notification). GITHUB_RELEASES_TOKEN is optional; never log it.
    VERSION_CHECK_GITHUB_REPO = os.getenv("VERSION_CHECK_GITHUB_REPO", "DRYTRIX/TimeTracker").strip()
    VERSION_CHECK_GITHUB_CACHE_TTL = int(os.getenv("VERSION_CHECK_GITHUB_CACHE_TTL", "43200"))  # 12h
    VERSION_CHECK_GITHUB_STALE_TTL = int(os.getenv("VERSION_CHECK_GITHUB_STALE_TTL", "604800"))  # 7d
    VERSION_CHECK_HTTP_TIMEOUT = int(os.getenv("VERSION_CHECK_HTTP_TIMEOUT", "10"))
    GITHUB_RELEASES_TOKEN = os.getenv("GITHUB_RELEASES_TOKEN", "").strip() or None
    ENABLE_PRE_RELEASE_NOTIFICATIONS = os.getenv("ENABLE_PRE_RELEASE_NOTIFICATIONS", "false").lower() == "true"

    # Settings secrets encryption (recommended for production).
    # Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SETTINGS_ENCRYPTION_KEY = (os.getenv("SETTINGS_ENCRYPTION_KEY") or "").strip() or None
    SETTINGS_ENCRYPTION_KEY_FILE = (os.getenv("SETTINGS_ENCRYPTION_KEY_FILE") or "").strip() or None

    # Smart in-app notifications (GET /api/notifications); times are HH:MM 24h in user's timezone.
    SMART_NOTIFY_MAX_PER_DAY = max(1, min(10, int(os.getenv("SMART_NOTIFY_MAX_PER_DAY", "2"))))
    SMART_NOTIFY_NO_TRACKING_AFTER = os.getenv("SMART_NOTIFY_NO_TRACKING_AFTER", "16:00").strip()
    SMART_NOTIFY_SUMMARY_AT = os.getenv("SMART_NOTIFY_SUMMARY_AT", "18:00").strip()
    SMART_NOTIFY_LONG_TIMER_HOURS = float(os.getenv("SMART_NOTIFY_LONG_TIMER_HOURS", "4"))
    # Fire time-based kinds only during the first N minutes of the configured hour (same idea as email remind-to-log).
    SMART_NOTIFY_SCHEDULER_SLOT_MINUTES = max(1, min(59, int(os.getenv("SMART_NOTIFY_SCHEDULER_SLOT_MINUTES", "30"))))

    # AI helper (server-side provider configuration; keys are never sent to clients)
    AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    AI_BASE_URL = os.getenv("AI_BASE_URL", "http://127.0.0.1:11434").strip()
    AI_MODEL = os.getenv("AI_MODEL", "llama3.1").strip()
    AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
    AI_TIMEOUT_SECONDS = max(1, int(os.getenv("AI_TIMEOUT_SECONDS", "30")))
    AI_CONTEXT_LIMIT = max(5, int(os.getenv("AI_CONTEXT_LIMIT", "40")))
    AI_SYSTEM_PROMPT = os.getenv(
        "AI_SYSTEM_PROMPT",
        "You are TimeTracker's AI helper. Be concise, explain assumptions, and return suggested actions only when the user asks for changes.",
    ).strip()

    # Password reset
    PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS = max(300, int(os.getenv("PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS", "3600")))

    # Two-factor authentication (TOTP)
    REQUIRE_2FA_FOR_ADMINS = os.getenv("REQUIRE_2FA_FOR_ADMINS", "false").lower() == "true"


class DevelopmentConfig(Config):
    """Development configuration"""

    FLASK_DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@localhost:5432/timetracker"
    )
    # CSRF can be overridden via env var, defaults to False for dev convenience
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "false").lower() == "true"
    # Relax SSL strictness by default in dev to avoid false negatives on http
    WTF_CSRF_SSL_STRICT = os.getenv("WTF_CSRF_SSL_STRICT", "false").lower() == "true"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    # Allow DATABASE_URL override for CI/CD PostgreSQL testing
    # Default to in-memory SQLite for local unit tests
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_SSL_STRICT = False

    def __init__(self):
        # Ensure SQLALCHEMY_DATABASE_URI reflects the current environment at instantiation time,
        # not only at module import time. This keeps parity with tests that mutate env vars.
        self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(Config):
    """Production configuration"""

    FLASK_DEBUG = False
    # Honor environment with secure-by-default values in production
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    REMEMBER_COOKIE_SECURE = os.getenv("REMEMBER_COOKIE_SECURE", "true").lower() == "true"
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
    WTF_CSRF_SSL_STRICT = os.getenv("WTF_CSRF_SSL_STRICT", "true").lower() == "true"

    def __init__(self):
        # Enforce that SECRET_KEY is set via environment in production
        if self._SECRET_KEY_IS_DEFAULT:
            import warnings

            warnings.warn(
                "SECURITY WARNING: SECRET_KEY is using the default development value. "
                "Set the SECRET_KEY environment variable to a secure random value in production.",
                RuntimeWarning,
                stacklevel=2,
            )
        if len(self.SECRET_KEY) < 32:
            import warnings

            warnings.warn(
                "SECURITY WARNING: SECRET_KEY is too short. " "Use a key of at least 32 characters for production.",
                RuntimeWarning,
                stacklevel=2,
            )


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
