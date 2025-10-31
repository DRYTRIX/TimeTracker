import os
import logging
import uuid
import time
from datetime import timedelta
from flask import Flask, request, session, redirect, url_for, flash, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from dotenv import load_dotenv
from flask_babel import Babel, _
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
import re
from jinja2 import ChoiceLoader, FileSystemLoader
from urllib.parse import urlparse
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.http import parse_options_header
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import posthog

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO()
babel = Babel()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
oauth = OAuth()

# Initialize Mail (will be configured in create_app)
from flask_mail import Mail
mail = Mail()

# Initialize APScheduler for background tasks
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()

# Initialize Prometheus metrics
REQUEST_COUNT = Counter('tt_requests_total', 'Total requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('tt_request_latency_seconds', 'Request latency seconds', ['endpoint'])

# Initialize JSON logger for structured logging
json_logger = logging.getLogger("timetracker")
json_logger.setLevel(logging.INFO)


def log_event(name: str, **kwargs):
    """Log an event with structured JSON format including request context"""
    try:
        extra = {"request_id": getattr(g, "request_id", None), "event": name, **kwargs}
        json_logger.info(name, extra=extra)
    except Exception:
        # Don't let logging errors break the application
        pass


def identify_user(user_id, properties=None):
    """
    Identify a user in PostHog with person properties.
    
    Sets properties on the user for better segmentation, cohort analysis,
    and personalization in PostHog.
    
    Args:
        user_id: The user ID (internal ID, not PII)
        properties: Dict of properties to set (use $set and $set_once)
    """
    try:
        posthog_api_key = os.getenv("POSTHOG_API_KEY", "")
        if not posthog_api_key:
            return
        
        posthog.identify(
            distinct_id=str(user_id),
            properties=properties or {}
        )
    except Exception:
        # Don't let analytics errors break the application
        pass


def track_event(user_id, event_name, properties=None):
    """
    Track a product analytics event via PostHog.
    
    Enhanced to include contextual properties like user agent, referrer,
    and deployment info for better analysis.
    
    Args:
        user_id: The user ID (internal ID, not PII)
        event_name: Name of the event (use resource.action format)
        properties: Dict of event properties (no PII)
    """
    try:
        # Get PostHog API key - must be explicitly set to enable tracking
        posthog_api_key = os.getenv("POSTHOG_API_KEY", "")
        if not posthog_api_key:
            return
        
        # Enhance properties with context
        enhanced_properties = properties or {}
        
        # Add request context if available
        try:
            if request:
                enhanced_properties.update({
                    "$current_url": request.url,
                    "$host": request.host,
                    "$pathname": request.path,
                    "$browser": request.user_agent.browser,
                    "$device_type": "mobile" if request.user_agent.platform in ["android", "iphone"] else "desktop",
                    "$os": request.user_agent.platform,
                })
        except Exception:
            pass
        
        # Add deployment context
        # Get app version from analytics config
        from app.config.analytics_defaults import get_analytics_config
        analytics_config = get_analytics_config()
        
        enhanced_properties.update({
            "environment": os.getenv("FLASK_ENV", "production"),
            "app_version": analytics_config.get("app_version"),
            "deployment_method": "docker" if os.path.exists("/.dockerenv") else "native",
        })
        
        posthog.capture(
            distinct_id=str(user_id), 
            event=event_name, 
            properties=enhanced_properties
        )
    except Exception:
        # Don't let analytics errors break the application
        pass


def track_page_view(page_name, user_id=None, properties=None):
    """
    Track a page view event.
    
    Args:
        page_name: Name of the page (e.g., 'dashboard', 'projects_list')
        user_id: User ID (optional, will use current_user if not provided)
        properties: Additional properties for the page view
    """
    try:
        # Get user ID if not provided
        if user_id is None:
            from flask_login import current_user
            if current_user.is_authenticated:
                user_id = current_user.id
            else:
                return  # Don't track anonymous page views
        
        # Build page view properties
        page_properties = {
            "page_name": page_name,
            "$pathname": request.path if request else None,
            "$current_url": request.url if request else None,
        }
        
        # Add custom properties if provided
        if properties:
            page_properties.update(properties)
        
        # Track the page view
        track_event(user_id, "$pageview", page_properties)
    except Exception:
        # Don't let analytics errors break the application
        pass


def create_app(config=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Make app aware of reverse proxy (scheme/host/port) for correct URL generation & cookies
    # Trust a single proxy by default; adjust via env if needed
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # Configuration
    # Load env-specific config class
    try:
        env_name = os.getenv("FLASK_ENV", "production")
        cfg_map = {
            "development": "app.config.DevelopmentConfig",
            "testing": "app.config.TestingConfig",
            "production": "app.config.ProductionConfig",
        }
        app.config.from_object(cfg_map.get(env_name, "app.config.Config"))
    except Exception:
        app.config.from_object("app.config.Config")
    if config:
        app.config.update(config)

    # Add top-level templates directory in addition to app/templates
    extra_templates_path = os.path.abspath(
        os.path.join(app.root_path, "..", "templates")
    )
    app.jinja_loader = ChoiceLoader(
        [app.jinja_loader, FileSystemLoader(extra_templates_path)]
    )

    # Prefer Postgres if POSTGRES_* envs are present but URL points to SQLite
    current_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if (
        not app.config.get("TESTING")
        and isinstance(current_url, str)
        and current_url.startswith("sqlite")
        and (
            os.getenv("POSTGRES_DB")
            or os.getenv("POSTGRES_USER")
            or os.getenv("POSTGRES_PASSWORD")
        )
    ):
        pg_user = os.getenv("POSTGRES_USER", "timetracker")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "timetracker")
        pg_db = os.getenv("POSTGRES_DB", "timetracker")
        pg_host = os.getenv("POSTGRES_HOST", "db")
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:5432/{pg_db}"
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    oauth.init_app(app)
    
    # Initialize Flask-Mail
    from app.utils.email import init_mail
    init_mail(app)
    
    # Initialize and start background scheduler
    if not scheduler.running:
        from app.utils.scheduled_tasks import register_scheduled_tasks
        scheduler.start()
        # Register tasks after app context is available
        with app.app_context():
            register_scheduled_tasks(scheduler)
    
    # Only initialize CSRF protection if enabled
    if app.config.get('WTF_CSRF_ENABLED'):
        csrf.init_app(app)
    try:
        # Configure limiter defaults from config if provided
        default_limits = []
        raw = app.config.get("RATELIMIT_DEFAULT")
        if raw:
            # support semicolon or comma separated limits
            parts = [
                p.strip() for p in str(raw).replace(",", ";").split(";") if p.strip()
            ]
            if parts:
                default_limits = parts
        limiter._default_limits = default_limits  # set after init
        limiter.init_app(app)
    except Exception:
        limiter.init_app(app)

    # Ensure translations exist and configure absolute translation directories before Babel init
    try:
        translations_dirs = (
            app.config.get("BABEL_TRANSLATION_DIRECTORIES") or "translations"
        ).split(",")
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        abs_dirs = []
        for d in translations_dirs:
            d = d.strip()
            if not d:
                continue
            abs_dirs.append(
                d if os.path.isabs(d) else os.path.abspath(os.path.join(base_path, d))
            )
        if abs_dirs:
            app.config["BABEL_TRANSLATION_DIRECTORIES"] = os.pathsep.join(abs_dirs)
        # Best-effort compile with Babel CLI if available, else Python fallback
        try:
            import subprocess

            subprocess.run(["pybabel", "compile", "-d", abs_dirs[0]], check=False)
        except Exception:
            pass
        from app.utils.i18n import ensure_translations_compiled

        for d in abs_dirs:
            ensure_translations_compiled(d)
    except Exception:
        pass

    # Internationalization: locale selector compatible with Flask-Babel v4+
    def _select_locale():
        try:
            # 1) User preference from DB
            from flask_login import current_user

            if current_user and getattr(current_user, "is_authenticated", False):
                pref = getattr(current_user, "preferred_language", None)
                if pref:
                    return pref
            # 2) Session override (set-language route)
            if "preferred_language" in session:
                return session.get("preferred_language")
            # 3) Best match with Accept-Language
            supported = list(app.config.get("LANGUAGES", {}).keys()) or ["en"]
            return request.accept_languages.best_match(supported) or app.config.get(
                "BABEL_DEFAULT_LOCALE", "en"
            )
        except Exception:
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")

    babel.init_app(
        app,
        default_locale=app.config.get("BABEL_DEFAULT_LOCALE", "en"),
        default_timezone=app.config.get("TZ", "Europe/Rome"),
        locale_selector=_select_locale,
    )

    # Ensure gettext helpers available in Jinja
    try:
        from flask_babel import gettext as _gettext, ngettext as _ngettext

        app.jinja_env.globals.update(_=_gettext, ngettext=_ngettext)
    except Exception:
        pass

    # Log effective database URL (mask password)
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    try:
        masked_db_url = re.sub(r"//([^:]+):[^@]+@", r"//\\1:***@", db_url)
    except Exception:
        masked_db_url = db_url
    app.logger.info(f"Using database URL: {masked_db_url}")

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Internationalization selector handled via babel.init_app(locale_selector=...)

    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        """Load user for Flask-Login"""
        from app.models import User

        return User.query.get(int(user_id))

    # Check if initial setup is required (skip for certain routes)
    @app.before_request
    def check_setup_required():
        try:
            # Skip setup check in testing mode
            if app.config.get('TESTING'):
                return
            
            # Skip setup check for these routes
            skip_routes = ['setup.initial_setup', 'static', 'auth.login', 'auth.logout', 'main.health_check', 'main.readiness_check']
            if request.endpoint in skip_routes:
                return
            
            # Skip for assets and health checks
            if request.path.startswith('/static/') or request.path.startswith('/_'):
                return
            
            # Check if setup is complete
            from app.utils.installation import get_installation_config
            installation_config = get_installation_config()
            
            if not installation_config.is_setup_complete():
                return redirect(url_for('setup.initial_setup'))
        except Exception:
            pass
    
    # Attach request ID for tracing
    @app.before_request
    def attach_request_id():
        try:
            g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        except Exception:
            pass

    # Start timer for Prometheus metrics
    @app.before_request
    def prom_start_timer():
        try:
            g._start_time = time.time()
        except Exception:
            pass

    # Request logging for /login to trace POSTs reaching the app
    @app.before_request
    def log_login_requests():
        try:
            if request.path == "/login":
                app.logger.info(
                    "%s %s from %s UA=%s",
                    request.method,
                    request.path,
                    request.headers.get("X-Forwarded-For") or request.remote_addr,
                    request.headers.get("User-Agent"),
                )
        except Exception:
            pass

    # Record Prometheus metrics and log write operations
    @app.after_request
    def record_metrics_and_log(response):
        try:
            # Record Prometheus metrics
            latency = time.time() - getattr(g, '_start_time', time.time())
            endpoint = request.endpoint or "unknown"
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
            REQUEST_COUNT.labels(
                method=request.method, 
                endpoint=endpoint, 
                http_status=response.status_code
            ).inc()
        except Exception:
            pass
        
        try:
            # Log write operations
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                app.logger.info(
                    "%s %s -> %s from %s",
                    request.method,
                    request.path,
                    response.status_code,
                    request.headers.get("X-Forwarded-For") or request.remote_addr,
                )
        except Exception:
            pass
        return response

    # Configure session
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        seconds=int(os.getenv("PERMANENT_SESSION_LIFETIME", 86400))
    )

    # Setup logging (including JSON logging)
    setup_logging(app)

    # Load analytics configuration (embedded at build time)
    from app.config.analytics_defaults import get_analytics_config, has_analytics_configured
    analytics_config = get_analytics_config()
    
    # Log analytics status (for transparency)
    if has_analytics_configured():
        app.logger.info("TimeTracker with analytics configured (telemetry opt-in via admin dashboard)")
    else:
        app.logger.info("TimeTracker build without analytics configuration")
    
    # Initialize Sentry for error monitoring
    # Priority: Env var > Built-in default > Disabled
    sentry_dsn = analytics_config.get("sentry_dsn", "")
    if sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=analytics_config.get("sentry_traces_rate", 0.0),
                environment=os.getenv("FLASK_ENV", "production"),
                release=analytics_config.get("app_version")
            )
            app.logger.info("Sentry error monitoring initialized")
        except Exception as e:
            app.logger.warning(f"Failed to initialize Sentry: {e}")

    # Initialize PostHog for product analytics
    # Priority: Env var > Built-in default > Disabled
    posthog_api_key = analytics_config.get("posthog_api_key", "")
    posthog_host = analytics_config.get("posthog_host", "https://app.posthog.com")
    if posthog_api_key:
        try:
            posthog.project_api_key = posthog_api_key
            posthog.host = posthog_host
            app.logger.info(f"PostHog product analytics initialized (host: {posthog_host})")
        except Exception as e:
            app.logger.warning(f"Failed to initialize PostHog: {e}")

    # Fail-fast on weak/missing secret in production
    if not app.debug and app.config.get("FLASK_ENV", "production") == "production":
        secret = app.config.get("SECRET_KEY")
        placeholder_values = {"dev-secret-key-change-in-production", "your-secret-key-change-this", "your-secret-key-here"}
        if (not secret) or (secret in placeholder_values) or (isinstance(secret, str) and len(secret) < 32):
            app.logger.error("Invalid SECRET_KEY configured in production; refusing to start")
            raise RuntimeError("Invalid SECRET_KEY in production")

    # Apply security headers and a basic CSP
    @app.after_request
    def apply_security_headers(response):
        try:
            headers = app.config.get("SECURITY_HEADERS", {}) or {}
            for k, v in headers.items():
                # do not overwrite existing header if already present
                if not response.headers.get(k):
                    response.headers[k] = v
            # Minimal CSP allowing our own resources and common CDNs used in templates
            if not response.headers.get("Content-Security-Policy"):
                csp = (
                    "default-src 'self'; "
                    "img-src 'self' data: https:; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.datatables.net https://uicdn.toast.com; "
                    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
                    "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.datatables.net https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://esm.sh https://uicdn.toast.com; "
                    "connect-src 'self' ws: wss:; "
                    "frame-ancestors 'none'"
                )
                response.headers["Content-Security-Policy"] = csp
            # Additional privacy headers
            if not response.headers.get("Referrer-Policy"):
                response.headers["Referrer-Policy"] = "no-referrer"
            if not response.headers.get("Permissions-Policy"):
                response.headers["Permissions-Policy"] = (
                    "geolocation=(), microphone=(), camera=()"
                )
        except Exception:
            pass

        # CSRF cookie/token handling
        # If CSRF is enabled, ensure CSRF cookie exists for HTML GET responses
        # If CSRF is disabled, explicitly clear any existing CSRF cookie to avoid confusion
        if app.config.get('WTF_CSRF_ENABLED'):
            try:
                # Only for safe, HTML page responses
                if request.method == "GET":
                    content_type = response.headers.get("Content-Type", "")
                    if isinstance(content_type, str) and content_type.startswith("text/html"):
                        cookie_name = app.config.get("CSRF_COOKIE_NAME", "XSRF-TOKEN")
                        has_cookie = bool(request.cookies.get(cookie_name))
                        if not has_cookie:
                            # Generate a CSRF token and set cookie using same settings as /auth/csrf-token
                            try:
                                from flask_wtf.csrf import generate_csrf
                                token = generate_csrf()
                            except Exception:
                                token = ""
                            cookie_secure = bool(
                                app.config.get(
                                    "CSRF_COOKIE_SECURE",
                                    app.config.get("SESSION_COOKIE_SECURE", False),
                                )
                            )
                            cookie_httponly = bool(app.config.get("CSRF_COOKIE_HTTPONLY", False))
                            cookie_samesite = app.config.get("CSRF_COOKIE_SAMESITE", "Lax")
                            cookie_domain = app.config.get("CSRF_COOKIE_DOMAIN") or None
                            cookie_path = app.config.get("CSRF_COOKIE_PATH", "/")
                            try:
                                max_age = int(app.config.get("WTF_CSRF_TIME_LIMIT", 3600))
                            except Exception:
                                max_age = 3600
                            response.set_cookie(
                                cookie_name,
                                token or "",
                                max_age=max_age,
                                secure=cookie_secure,
                                httponly=cookie_httponly,
                                samesite=cookie_samesite,
                                domain=cookie_domain,
                                path=cookie_path,
                            )
            except Exception:
                pass
        else:
            try:
                cookie_name = app.config.get("CSRF_COOKIE_NAME", "XSRF-TOKEN")
                if request.cookies.get(cookie_name):
                    # Clear the cookie by setting it expired
                    response.set_cookie(
                        cookie_name,
                        "",
                        max_age=0,
                        expires=0,
                        path=app.config.get("CSRF_COOKIE_PATH", "/"),
                        domain=app.config.get("CSRF_COOKIE_DOMAIN") or None,
                        secure=bool(app.config.get("CSRF_COOKIE_SECURE", app.config.get("SESSION_COOKIE_SECURE", False))),
                        httponly=bool(app.config.get("CSRF_COOKIE_HTTPONLY", False)),
                        samesite=app.config.get("CSRF_COOKIE_SAMESITE", "Lax"),
                    )
            except Exception:
                pass
        return response

    # CSRF error handler with HTML-friendly fallback
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Prefer HTML flow for classic form posts regardless of Accept header quirks
        try:
            mimetype, _ = parse_options_header(request.headers.get("Content-Type", ""))
            is_classic_form = mimetype in ("application/x-www-form-urlencoded", "multipart/form-data")
        except Exception:
            is_classic_form = False

        # Log details for diagnostics
        try:
            try:
                from flask_login import current_user as _cu
                user_id = getattr(_cu, "id", None) if getattr(_cu, "is_authenticated", False) else None
            except Exception:
                user_id = None
            app.logger.warning(
                "CSRF failure: path=%s method=%s form=%s json=%s ref=%s user=%s reason=%s",
                request.path,
                request.method,
                bool(request.form),
                request.is_json,
                request.referrer,
                user_id,
                getattr(e, "description", "")
            )
        except Exception:
            pass

        if request.method == "POST" and (is_classic_form or (request.form and not request.is_json)):
            try:
                flash(_("Your session expired or the page was open too long. Please try again."), "warning")
            except Exception:
                flash("Your session expired or the page was open too long. Please try again.", "warning")

            # Redirect back to a safe same-origin referrer if available, else to dashboard
            dest = url_for("main.dashboard")
            try:
                ref = request.referrer
                if ref:
                    ref_host = urlparse(ref).netloc
                    cur_host = urlparse(request.host_url).netloc
                    if ref_host and ref_host == cur_host:
                        dest = ref
            except Exception:
                pass
            return redirect(dest)

        # JSON/XHR fall-through
        try:
            wants_json = (
                request.is_json
                or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.accept_mimetypes["application/json"]
                >= request.accept_mimetypes["text/html"]
            )
        except Exception:
            wants_json = False

        if wants_json:
            return jsonify(error="csrf_token_missing_or_invalid"), 400

        # Default to HTML-friendly behavior
        try:
            flash(_("Your session expired or the page was open too long. Please try again."), "warning")
        except Exception:
            flash("Your session expired or the page was open too long. Please try again.", "warning")
        dest = url_for("main.dashboard")
        try:
            ref = request.referrer
            if ref:
                ref_host = urlparse(ref).netloc
                cur_host = urlparse(request.host_url).netloc
                if ref_host and ref_host == cur_host:
                    dest = ref
        except Exception:
            pass
        return redirect(dest)

    # Expose csrf_token() in Jinja templates even without FlaskForm
    # Always inject the function, but return empty string when CSRF is disabled
    @app.context_processor
    def inject_csrf_token():
        def get_csrf_token():
            # Return empty string if CSRF is disabled
            if not app.config.get('WTF_CSRF_ENABLED'):
                return ""
            try:
                from flask_wtf.csrf import generate_csrf
                return generate_csrf()
            except Exception:
                return ""
        return dict(csrf_token=get_csrf_token)

    # CSRF token refresh endpoint (GET)
    @app.route("/auth/csrf-token", methods=["GET"])
    def get_csrf_token():
        # If CSRF is disabled, return empty token
        if not app.config.get('WTF_CSRF_ENABLED'):
            resp = jsonify(csrf_token="", csrf_enabled=False)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            return resp
        
        try:
            from flask_wtf.csrf import generate_csrf

            token = generate_csrf()
        except Exception:
            token = ""
        resp = jsonify(csrf_token=token, csrf_enabled=True)
        try:
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        except Exception:
            pass
        # Also set/update a CSRF cookie for double-submit pattern and SPA helpers
        try:
            cookie_name = app.config.get("CSRF_COOKIE_NAME", "XSRF-TOKEN")
            # Derive defaults from session cookie flags if not explicitly set
            cookie_secure = bool(
                app.config.get(
                    "CSRF_COOKIE_SECURE",
                    app.config.get("SESSION_COOKIE_SECURE", False),
                )
            )
            cookie_httponly = bool(app.config.get("CSRF_COOKIE_HTTPONLY", False))
            cookie_samesite = app.config.get("CSRF_COOKIE_SAMESITE", "Lax")
            cookie_domain = app.config.get("CSRF_COOKIE_DOMAIN") or None
            cookie_path = app.config.get("CSRF_COOKIE_PATH", "/")
            try:
                max_age = int(app.config.get("WTF_CSRF_TIME_LIMIT", 3600))
            except Exception:
                max_age = 3600
            resp.set_cookie(
                cookie_name,
                token or "",
                max_age=max_age,
                secure=cookie_secure,
                httponly=cookie_httponly,
                samesite=cookie_samesite,
                domain=cookie_domain,
                path=cookie_path,
            )
        except Exception:
            pass
        return resp

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.projects import projects_bp
    from app.routes.timer import timer_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.api_v1 import api_v1_bp
    from app.routes.api_docs import api_docs_bp, swaggerui_blueprint
    from app.routes.analytics import analytics_bp
    from app.routes.tasks import tasks_bp
    from app.routes.invoices import invoices_bp
    from app.routes.payments import payments_bp
    from app.routes.clients import clients_bp
    from app.routes.client_notes import client_notes_bp
    from app.routes.comments import comments_bp
    from app.routes.kanban import kanban_bp
    from app.routes.setup import setup_bp
    from app.routes.user import user_bp
    from app.routes.time_entry_templates import time_entry_templates_bp
    from app.routes.saved_filters import saved_filters_bp
    from app.routes.settings import settings_bp
    from app.routes.weekly_goals import weekly_goals_bp
    from app.routes.expenses import expenses_bp
    from app.routes.permissions import permissions_bp
    from app.routes.calendar import calendar_bp
    from app.routes.expense_categories import expense_categories_bp
    from app.routes.mileage import mileage_bp
    from app.routes.per_diem import per_diem_bp
    from app.routes.budget_alerts import budget_alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(timer_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(swaggerui_blueprint)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(client_notes_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(kanban_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(time_entry_templates_bp)
    app.register_blueprint(saved_filters_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(weekly_goals_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(expense_categories_bp)
    app.register_blueprint(mileage_bp)
    app.register_blueprint(per_diem_bp)
    app.register_blueprint(budget_alerts_bp)

    # Exempt API blueprints from CSRF protection (JSON API uses token authentication, not CSRF tokens)
    # Only if CSRF is enabled
    if app.config.get('WTF_CSRF_ENABLED'):
        csrf.exempt(api_bp)
        csrf.exempt(api_v1_bp)
        csrf.exempt(api_docs_bp)

    # Register OAuth OIDC client if enabled
    try:
        auth_method = (app.config.get("AUTH_METHOD") or "local").strip().lower()
    except Exception:
        auth_method = "local"

    if auth_method in ("oidc", "both"):
        issuer = app.config.get("OIDC_ISSUER")
        client_id = app.config.get("OIDC_CLIENT_ID")
        client_secret = app.config.get("OIDC_CLIENT_SECRET")
        scopes = app.config.get("OIDC_SCOPES", "openid profile email")
        if issuer and client_id and client_secret:
            try:
                oauth.register(
                    name="oidc",
                    client_id=client_id,
                    client_secret=client_secret,
                    server_metadata_url=f"{issuer.rstrip('/')}/.well-known/openid-configuration",
                    client_kwargs={
                        "scope": scopes,
                        "code_challenge_method": "S256",
                    },
                )
                app.logger.info("OIDC client registered with issuer %s", issuer)
            except Exception as e:
                app.logger.error("Failed to register OIDC client: %s", e)
        else:
            app.logger.warning(
                "AUTH_METHOD is %s but OIDC envs are incomplete; OIDC login will not work",
                auth_method,
            )

    # Prometheus metrics endpoint
    @app.route('/metrics')
    def metrics():
        """Expose Prometheus metrics"""
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    # Register error handlers
    from app.utils.error_handlers import register_error_handlers

    register_error_handlers(app)

    # Register context processors
    from app.utils.context_processors import register_context_processors

    register_context_processors(app)

    # (translations compiled and directories set before Babel init)

    # Register template filters
    from app.utils.template_filters import register_template_filters

    register_template_filters(app)

    # Register CLI commands
    from app.utils.cli import register_cli_commands

    register_cli_commands(app)

    # Promote configured admin usernames automatically on each request (idempotent)
    @app.before_request
    def _promote_admin_users_on_request():
        try:
            from flask_login import current_user

            if not current_user or not getattr(current_user, "is_authenticated", False):
                return
            admin_usernames = [
                u.strip().lower() for u in app.config.get("ADMIN_USERNAMES", ["admin"])
            ]
            if (
                current_user.username
                and current_user.username.lower() in admin_usernames
                and current_user.role != "admin"
            ):
                current_user.role = "admin"
                db.session.commit()
        except Exception:
            # Non-fatal; avoid breaking requests if this fails
            try:
                db.session.rollback()
            except Exception:
                pass

    # Initialize database on first request
    def initialize_database():
        try:
            # Import models to ensure they are registered
            from app.models import (
                User,
                Project,
                TimeEntry,
                Task,
                Settings,
                TaskActivity,
                Comment,
            )

            # Create database tables
            db.create_all()

            # Check and migrate Task Management tables if needed
            migrate_task_management_tables()

            # Create default admin user if it doesn't exist
            admin_username = app.config.get("ADMIN_USERNAMES", ["admin"])[0]
            if not User.query.filter_by(username=admin_username).first():
                admin_user = User(username=admin_username, role="admin")
                admin_user.is_active = True
                db.session.add(admin_user)
                db.session.commit()
                print(f"Created default admin user: {admin_username}")

            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            # Don't raise the exception, just log it

    # Store the initialization function for later use
    app.initialize_database = initialize_database

    return app


def setup_logging(app):
    """Setup application logging including JSON logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    # Default to a file in the project logs directory if not provided
    default_log_path = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs", "timetracker.log"
        )
    )
    log_file = os.getenv("LOG_FILE", default_log_path)
    
    # JSON log file path
    json_log_path = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs", "app.jsonl"
        )
    )

    # Prepare handlers
    handlers = [logging.StreamHandler()]

    # Add file handler (default or specified)
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create log file '{log_file}': {e}")
        print("Logging to console only")
        # Don't add file handler, just use console logging

    # Configure Flask app logger directly (works well under gunicorn)
    for handler in handlers:
        handler.setLevel(getattr(logging, log_level.upper()))
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )

    # Clear existing handlers to avoid duplicate logs
    app.logger.handlers.clear()
    app.logger.propagate = False
    app.logger.setLevel(getattr(logging, log_level.upper()))
    for handler in handlers:
        app.logger.addHandler(handler)

    # Also configure root logger so modules using logging.getLogger() are captured
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    # Avoid duplicating handlers if already attached
    root_logger.handlers = []
    for handler in handlers:
        root_logger.addHandler(handler)

    # Setup JSON logging for structured events
    try:
        json_log_dir = os.path.dirname(json_log_path)
        if json_log_dir and not os.path.exists(json_log_dir):
            os.makedirs(json_log_dir, exist_ok=True)
        
        json_handler = logging.FileHandler(json_log_path)
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        json_handler.setFormatter(json_formatter)
        json_handler.setLevel(logging.INFO)
        
        # Add JSON handler to the timetracker logger
        json_logger.handlers.clear()
        json_logger.addHandler(json_handler)
        json_logger.propagate = False
        
        app.logger.info(f"JSON logging initialized: {json_log_path}")
    except (PermissionError, OSError) as e:
        app.logger.warning(f"Could not initialize JSON logging: {e}")

    # Suppress noisy logs in production
    if not app.debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)


def migrate_task_management_tables():
    """Check and migrate Task Management tables if they don't exist"""
    try:
        from sqlalchemy import inspect, text

        # Check if tasks table exists
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "tasks" not in existing_tables:
            print("Task Management: Creating tasks table...")
            # Create the tasks table
            db.create_all()
            print("✓ Tasks table created successfully")
        else:
            print("Task Management: Tasks table already exists")

        # Check if task_id column exists in time_entries table
        if "time_entries" in existing_tables:
            time_entries_columns = [
                col["name"] for col in inspector.get_columns("time_entries")
            ]
            if "task_id" not in time_entries_columns:
                print("Task Management: Adding task_id column to time_entries table...")
                try:
                    # Add task_id column to time_entries table
                    db.engine.execute(
                        text(
                            "ALTER TABLE time_entries ADD COLUMN task_id INTEGER REFERENCES tasks(id)"
                        )
                    )
                    print("✓ task_id column added to time_entries table")
                except Exception as e:
                    print(f"⚠ Warning: Could not add task_id column: {e}")
                    print(
                        "  You may need to manually add this column or recreate the database"
                    )
            else:
                print(
                    "Task Management: task_id column already exists in time_entries table"
                )

        print("Task Management migration check completed")

    except Exception as e:
        print(f"⚠ Warning: Task Management migration check failed: {e}")
        print(
            "  The application will continue, but Task Management features may not work properly"
        )


def init_database(app):
    """Initialize database tables and create default admin user"""
    with app.app_context():
        try:
            # Import models to ensure they are registered
            from app.models import (
                User,
                Project,
                TimeEntry,
                Task,
                Settings,
                TaskActivity,
                Comment,
            )

            # Create database tables
            db.create_all()

            # Check and migrate Task Management tables if needed
            migrate_task_management_tables()

            # Create default admin user if it doesn't exist
            admin_username = app.config.get("ADMIN_USERNAMES", ["admin"])[0]
            if not User.query.filter_by(username=admin_username).first():
                admin_user = User(username=admin_username, role="admin")
                admin_user.is_active = True
                db.session.add(admin_user)
                db.session.commit()
                print(f"Created default admin user: {admin_username}")

            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
