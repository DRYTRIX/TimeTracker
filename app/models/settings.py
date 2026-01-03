from datetime import datetime
from app import db
from app.config import Config
import os


class Settings(db.Model):
    """Settings model for system configuration"""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    timezone = db.Column(db.String(50), default="Europe/Rome", nullable=False)
    currency = db.Column(db.String(3), default="EUR", nullable=False)
    rounding_minutes = db.Column(db.Integer, default=1, nullable=False)
    single_active_timer = db.Column(db.Boolean, default=True, nullable=False)
    allow_self_register = db.Column(db.Boolean, default=True, nullable=False)
    idle_timeout_minutes = db.Column(db.Integer, default=30, nullable=False)
    backup_retention_days = db.Column(db.Integer, default=30, nullable=False)
    backup_time = db.Column(db.String(5), default="02:00", nullable=False)  # HH:MM format
    export_delimiter = db.Column(db.String(1), default=",", nullable=False)

    # Company branding for invoices
    company_name = db.Column(db.String(200), default="Your Company Name", nullable=False)
    company_address = db.Column(db.Text, default="Your Company Address", nullable=False)
    company_email = db.Column(db.String(200), default="info@yourcompany.com", nullable=False)
    company_phone = db.Column(db.String(50), default="+1 (555) 123-4567", nullable=False)
    company_website = db.Column(db.String(200), default="www.yourcompany.com", nullable=False)
    company_logo_filename = db.Column(db.String(255), default="", nullable=True)  # Changed from company_logo_path
    company_tax_id = db.Column(db.String(100), default="", nullable=True)
    company_bank_info = db.Column(db.Text, default="", nullable=True)

    # PDF template customization
    invoice_pdf_template_html = db.Column(db.Text, default="", nullable=True)
    invoice_pdf_template_css = db.Column(db.Text, default="", nullable=True)
    invoice_pdf_design_json = db.Column(db.Text, default="", nullable=True)  # Konva.js design state

    # Invoice defaults
    invoice_prefix = db.Column(db.String(10), default="INV", nullable=False)
    invoice_start_number = db.Column(db.Integer, default=1000, nullable=False)
    invoice_terms = db.Column(db.Text, default="Payment is due within 30 days of invoice date.", nullable=False)
    invoice_notes = db.Column(db.Text, default="Thank you for your business!", nullable=False)

    # Peppol e-invoicing (optional; can be configured via WebUI or env)
    # peppol_enabled: None => use env var PEPPOL_ENABLED; True/False overrides env.
    peppol_enabled = db.Column(db.Boolean, default=None, nullable=True)
    peppol_sender_endpoint_id = db.Column(db.String(100), default="", nullable=True)
    peppol_sender_scheme_id = db.Column(db.String(20), default="", nullable=True)
    peppol_sender_country = db.Column(db.String(2), default="", nullable=True)
    peppol_access_point_url = db.Column(db.String(500), default="", nullable=True)
    peppol_access_point_token = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    peppol_access_point_timeout = db.Column(db.Integer, default=30, nullable=True)
    peppol_provider = db.Column(db.String(50), default="generic", nullable=True)

    # Privacy and analytics settings
    allow_analytics = db.Column(db.Boolean, default=True, nullable=False)  # Controls system info sharing for analytics

    # Kiosk mode settings
    kiosk_mode_enabled = db.Column(db.Boolean, default=False, nullable=False)
    kiosk_auto_logout_minutes = db.Column(db.Integer, default=15, nullable=False)
    kiosk_allow_camera_scanning = db.Column(db.Boolean, default=True, nullable=False)
    kiosk_require_reason_for_adjustments = db.Column(db.Boolean, default=False, nullable=False)
    kiosk_default_movement_type = db.Column(db.String(20), default="adjustment", nullable=False)

    # Email configuration settings (stored in database, takes precedence over environment variables)
    mail_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Enable database-backed email config
    mail_server = db.Column(db.String(255), default="", nullable=True)
    mail_port = db.Column(db.Integer, default=587, nullable=True)
    mail_use_tls = db.Column(db.Boolean, default=True, nullable=True)
    mail_use_ssl = db.Column(db.Boolean, default=False, nullable=True)
    mail_username = db.Column(db.String(255), default="", nullable=True)
    mail_password = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    mail_default_sender = db.Column(db.String(255), default="", nullable=True)

    # Integration OAuth credentials (stored in database, takes precedence over environment variables)
    # Jira
    jira_client_id = db.Column(db.String(255), default="", nullable=True)
    jira_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # Slack
    slack_client_id = db.Column(db.String(255), default="", nullable=True)
    slack_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # GitHub
    github_client_id = db.Column(db.String(255), default="", nullable=True)
    github_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # Google Calendar
    google_calendar_client_id = db.Column(db.String(255), default="", nullable=True)
    google_calendar_client_secret = db.Column(
        db.String(255), default="", nullable=True
    )  # Store encrypted in production
    # Outlook Calendar
    outlook_calendar_client_id = db.Column(db.String(255), default="", nullable=True)
    outlook_calendar_client_secret = db.Column(
        db.String(255), default="", nullable=True
    )  # Store encrypted in production
    outlook_calendar_tenant_id = db.Column(db.String(255), default="", nullable=True)
    # Microsoft Teams
    microsoft_teams_client_id = db.Column(db.String(255), default="", nullable=True)
    microsoft_teams_client_secret = db.Column(
        db.String(255), default="", nullable=True
    )  # Store encrypted in production
    microsoft_teams_tenant_id = db.Column(db.String(255), default="", nullable=True)
    # Asana
    asana_client_id = db.Column(db.String(255), default="", nullable=True)
    asana_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # Trello
    trello_api_key = db.Column(db.String(255), default="", nullable=True)
    trello_api_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # GitLab
    gitlab_client_id = db.Column(db.String(255), default="", nullable=True)
    gitlab_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    gitlab_instance_url = db.Column(db.String(500), default="", nullable=True)
    # QuickBooks
    quickbooks_client_id = db.Column(db.String(255), default="", nullable=True)
    quickbooks_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production
    # Xero
    xero_client_id = db.Column(db.String(255), default="", nullable=True)
    xero_client_secret = db.Column(db.String(255), default="", nullable=True)  # Store encrypted in production

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        # Set defaults from config
        self.timezone = kwargs.get("timezone", Config.TZ)
        self.currency = kwargs.get("currency", Config.CURRENCY)
        self.rounding_minutes = kwargs.get("rounding_minutes", Config.ROUNDING_MINUTES)
        self.single_active_timer = kwargs.get("single_active_timer", Config.SINGLE_ACTIVE_TIMER)
        self.allow_self_register = kwargs.get("allow_self_register", Config.ALLOW_SELF_REGISTER)
        self.idle_timeout_minutes = kwargs.get("idle_timeout_minutes", Config.IDLE_TIMEOUT_MINUTES)
        self.backup_retention_days = kwargs.get("backup_retention_days", Config.BACKUP_RETENTION_DAYS)
        self.backup_time = kwargs.get("backup_time", Config.BACKUP_TIME)
        self.export_delimiter = kwargs.get("export_delimiter", ",")

        # Set company branding defaults
        self.company_name = kwargs.get("company_name", "Your Company Name")
        self.company_address = kwargs.get("company_address", "Your Company Address")
        self.company_email = kwargs.get("company_email", "info@yourcompany.com")
        self.company_phone = kwargs.get("company_phone", "+1 (555) 123-4567")
        self.company_website = kwargs.get("company_website", "www.yourcompany.com")
        self.company_logo_filename = kwargs.get("company_logo_filename", "")
        self.company_tax_id = kwargs.get("company_tax_id", "")
        self.company_bank_info = kwargs.get("company_bank_info", "")

        # PDF template customization
        self.invoice_pdf_template_html = kwargs.get("invoice_pdf_template_html", "")
        self.invoice_pdf_template_css = kwargs.get("invoice_pdf_template_css", "")
        self.invoice_pdf_design_json = kwargs.get("invoice_pdf_design_json", "")

        # Set invoice defaults
        self.invoice_prefix = kwargs.get("invoice_prefix", "INV")
        self.invoice_start_number = kwargs.get("invoice_start_number", 1000)
        self.invoice_terms = kwargs.get("invoice_terms", "Payment is due within 30 days of invoice date.")
        self.invoice_notes = kwargs.get("invoice_notes", "Thank you for your business!")

        # Peppol defaults (None means "use env var")
        self.peppol_enabled = kwargs.get("peppol_enabled", None)
        self.peppol_sender_endpoint_id = kwargs.get("peppol_sender_endpoint_id", "")
        self.peppol_sender_scheme_id = kwargs.get("peppol_sender_scheme_id", "")
        self.peppol_sender_country = kwargs.get("peppol_sender_country", "")
        self.peppol_access_point_url = kwargs.get("peppol_access_point_url", "")
        self.peppol_access_point_token = kwargs.get("peppol_access_point_token", "")
        self.peppol_access_point_timeout = kwargs.get("peppol_access_point_timeout", 30)
        self.peppol_provider = kwargs.get("peppol_provider", "generic")

        # Kiosk mode defaults
        self.kiosk_mode_enabled = kwargs.get("kiosk_mode_enabled", False)
        self.kiosk_auto_logout_minutes = kwargs.get("kiosk_auto_logout_minutes", 15)
        self.kiosk_allow_camera_scanning = kwargs.get("kiosk_allow_camera_scanning", True)
        self.kiosk_require_reason_for_adjustments = kwargs.get("kiosk_require_reason_for_adjustments", False)
        self.kiosk_default_movement_type = kwargs.get("kiosk_default_movement_type", "adjustment")

        # Email configuration defaults
        self.mail_enabled = kwargs.get("mail_enabled", False)
        self.mail_server = kwargs.get("mail_server", "")
        self.mail_port = kwargs.get("mail_port", 587)
        self.mail_use_tls = kwargs.get("mail_use_tls", True)
        self.mail_use_ssl = kwargs.get("mail_use_ssl", False)
        self.mail_username = kwargs.get("mail_username", "")
        self.mail_password = kwargs.get("mail_password", "")
        self.mail_default_sender = kwargs.get("mail_default_sender", "")

        # Integration OAuth credentials defaults
        self.jira_client_id = kwargs.get("jira_client_id", "")
        self.jira_client_secret = kwargs.get("jira_client_secret", "")
        self.slack_client_id = kwargs.get("slack_client_id", "")
        self.slack_client_secret = kwargs.get("slack_client_secret", "")
        self.github_client_id = kwargs.get("github_client_id", "")
        self.github_client_secret = kwargs.get("github_client_secret", "")
        self.google_calendar_client_id = kwargs.get("google_calendar_client_id", "")
        self.google_calendar_client_secret = kwargs.get("google_calendar_client_secret", "")
        self.outlook_calendar_client_id = kwargs.get("outlook_calendar_client_id", "")
        self.outlook_calendar_client_secret = kwargs.get("outlook_calendar_client_secret", "")
        self.outlook_calendar_tenant_id = kwargs.get("outlook_calendar_tenant_id", "")
        self.microsoft_teams_client_id = kwargs.get("microsoft_teams_client_id", "")
        self.microsoft_teams_client_secret = kwargs.get("microsoft_teams_client_secret", "")
        self.microsoft_teams_tenant_id = kwargs.get("microsoft_teams_tenant_id", "")
        self.asana_client_id = kwargs.get("asana_client_id", "")
        self.asana_client_secret = kwargs.get("asana_client_secret", "")
        self.trello_api_key = kwargs.get("trello_api_key", "")
        self.trello_api_secret = kwargs.get("trello_api_secret", "")
        self.gitlab_client_id = kwargs.get("gitlab_client_id", "")
        self.gitlab_client_secret = kwargs.get("gitlab_client_secret", "")
        self.gitlab_instance_url = kwargs.get("gitlab_instance_url", "")
        self.quickbooks_client_id = kwargs.get("quickbooks_client_id", "")
        self.quickbooks_client_secret = kwargs.get("quickbooks_client_secret", "")
        self.xero_client_id = kwargs.get("xero_client_id", "")
        self.xero_client_secret = kwargs.get("xero_client_secret", "")

    def __repr__(self):
        return f"<Settings {self.id}>"

    def get_logo_url(self):
        """Get the full URL for the company logo"""
        if self.company_logo_filename:
            return f"/uploads/logos/{self.company_logo_filename}"
        return None

    def get_logo_path(self):
        """Get the full file system path for the company logo"""
        if not self.company_logo_filename:
            return None

        try:
            from flask import current_app

            upload_folder = os.path.join(current_app.root_path, "static", "uploads", "logos")
            return os.path.join(upload_folder, self.company_logo_filename)
        except RuntimeError:
            # current_app not available (e.g., during testing or initialization)
            # Fallback to a relative path
            return os.path.join("app", "static", "uploads", "logos", self.company_logo_filename)

    def has_logo(self):
        """Check if company has a logo uploaded"""
        if not self.company_logo_filename:
            return False

        logo_path = self.get_logo_path()
        return logo_path and os.path.exists(logo_path)

    def get_mail_config(self):
        """Get email configuration, preferring database settings over environment variables"""
        if self.mail_enabled and self.mail_server:
            return {
                "MAIL_SERVER": self.mail_server,
                "MAIL_PORT": self.mail_port or 587,
                "MAIL_USE_TLS": self.mail_use_tls if self.mail_use_tls is not None else True,
                "MAIL_USE_SSL": self.mail_use_ssl if self.mail_use_ssl is not None else False,
                "MAIL_USERNAME": self.mail_username or None,
                "MAIL_PASSWORD": self.mail_password or None,
                "MAIL_DEFAULT_SENDER": self.mail_default_sender or "noreply@timetracker.local",
            }
        return None

    def get_integration_credentials(self, provider: str) -> dict:
        """Get integration OAuth credentials, preferring database settings over environment variables.

        Args:
            provider: One of 'jira', 'slack', 'github', 'google_calendar', 'outlook_calendar',
                     'microsoft_teams', 'asana', 'trello', 'gitlab', 'quickbooks', 'xero'

        Returns:
            dict with credentials (varies by provider):
            - Standard OAuth: 'client_id', 'client_secret'
            - Microsoft: 'client_id', 'client_secret', 'tenant_id'
            - Trello: 'api_key', 'api_secret'
            - GitLab: 'client_id', 'client_secret', 'instance_url'
        """
        import os

        if provider == "jira":
            client_id = self.jira_client_id or os.getenv("JIRA_CLIENT_ID", "")
            client_secret = self.jira_client_secret or os.getenv("JIRA_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "slack":
            client_id = self.slack_client_id or os.getenv("SLACK_CLIENT_ID", "")
            client_secret = self.slack_client_secret or os.getenv("SLACK_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "github":
            client_id = self.github_client_id or os.getenv("GITHUB_CLIENT_ID", "")
            client_secret = self.github_client_secret or os.getenv("GITHUB_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "google_calendar":
            client_id = getattr(self, "google_calendar_client_id", "") or os.getenv("GOOGLE_CLIENT_ID", "")
            client_secret = getattr(self, "google_calendar_client_secret", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "outlook_calendar":
            client_id = getattr(self, "outlook_calendar_client_id", "") or os.getenv("OUTLOOK_CLIENT_ID", "")
            client_secret = getattr(self, "outlook_calendar_client_secret", "") or os.getenv(
                "OUTLOOK_CLIENT_SECRET", ""
            )
            tenant_id = getattr(self, "outlook_calendar_tenant_id", "") or os.getenv("OUTLOOK_TENANT_ID", "")
            return {"client_id": client_id, "client_secret": client_secret, "tenant_id": tenant_id}

        elif provider == "microsoft_teams":
            client_id = getattr(self, "microsoft_teams_client_id", "") or os.getenv("MICROSOFT_TEAMS_CLIENT_ID", "")
            client_secret = getattr(self, "microsoft_teams_client_secret", "") or os.getenv(
                "MICROSOFT_TEAMS_CLIENT_SECRET", ""
            )
            tenant_id = getattr(self, "microsoft_teams_tenant_id", "") or os.getenv("MICROSOFT_TEAMS_TENANT_ID", "")
            return {"client_id": client_id, "client_secret": client_secret, "tenant_id": tenant_id}

        elif provider == "asana":
            client_id = getattr(self, "asana_client_id", "") or os.getenv("ASANA_CLIENT_ID", "")
            client_secret = getattr(self, "asana_client_secret", "") or os.getenv("ASANA_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "trello":
            api_key = getattr(self, "trello_api_key", "") or os.getenv("TRELLO_API_KEY", "")
            api_secret = getattr(self, "trello_api_secret", "") or os.getenv("TRELLO_API_SECRET", "")
            return {"api_key": api_key, "api_secret": api_secret}

        elif provider == "gitlab":
            client_id = getattr(self, "gitlab_client_id", "") or os.getenv("GITLAB_CLIENT_ID", "")
            client_secret = getattr(self, "gitlab_client_secret", "") or os.getenv("GITLAB_CLIENT_SECRET", "")
            instance_url = getattr(self, "gitlab_instance_url", "") or os.getenv(
                "GITLAB_INSTANCE_URL", "https://gitlab.com"
            )
            return {"client_id": client_id, "client_secret": client_secret, "instance_url": instance_url}

        elif provider == "quickbooks":
            client_id = getattr(self, "quickbooks_client_id", "") or os.getenv("QUICKBOOKS_CLIENT_ID", "")
            client_secret = getattr(self, "quickbooks_client_secret", "") or os.getenv("QUICKBOOKS_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        elif provider == "xero":
            client_id = getattr(self, "xero_client_id", "") or os.getenv("XERO_CLIENT_ID", "")
            client_secret = getattr(self, "xero_client_secret", "") or os.getenv("XERO_CLIENT_SECRET", "")
            return {"client_id": client_id, "client_secret": client_secret}

        else:
            return {}

    def to_dict(self):
        """Convert settings to dictionary for API responses"""
        return {
            "id": self.id,
            "timezone": self.timezone,
            "currency": self.currency,
            "rounding_minutes": self.rounding_minutes,
            "single_active_timer": self.single_active_timer,
            "allow_self_register": self.allow_self_register,
            "idle_timeout_minutes": self.idle_timeout_minutes,
            "backup_retention_days": self.backup_retention_days,
            "backup_time": self.backup_time,
            "export_delimiter": self.export_delimiter,
            "company_name": self.company_name,
            "company_address": self.company_address,
            "company_email": self.company_email,
            "company_phone": self.company_phone,
            "company_website": self.company_website,
            "company_logo_filename": self.company_logo_filename,
            "company_logo_url": self.get_logo_url(),
            "has_logo": self.has_logo(),
            "company_tax_id": self.company_tax_id,
            "company_bank_info": self.company_bank_info,
            "invoice_prefix": self.invoice_prefix,
            "invoice_start_number": self.invoice_start_number,
            "invoice_terms": self.invoice_terms,
            "invoice_notes": self.invoice_notes,
            "peppol_enabled": self.peppol_enabled,
            "peppol_sender_endpoint_id": getattr(self, "peppol_sender_endpoint_id", "") or "",
            "peppol_sender_scheme_id": getattr(self, "peppol_sender_scheme_id", "") or "",
            "peppol_sender_country": getattr(self, "peppol_sender_country", "") or "",
            "peppol_access_point_url": getattr(self, "peppol_access_point_url", "") or "",
            "peppol_access_point_token_set": bool(getattr(self, "peppol_access_point_token", "")),
            "peppol_access_point_timeout": getattr(self, "peppol_access_point_timeout", None),
            "peppol_provider": getattr(self, "peppol_provider", "") or "",
            "invoice_pdf_template_html": self.invoice_pdf_template_html,
            "invoice_pdf_template_css": self.invoice_pdf_template_css,
            "invoice_pdf_design_json": self.invoice_pdf_design_json,
            "allow_analytics": self.allow_analytics,
            "mail_enabled": self.mail_enabled,
            "mail_server": self.mail_server,
            "mail_port": self.mail_port,
            "mail_use_tls": self.mail_use_tls,
            "mail_use_ssl": self.mail_use_ssl,
            "mail_username": self.mail_username,
            "mail_password_set": bool(self.mail_password),  # Don't expose actual password
            "mail_default_sender": self.mail_default_sender,
            "jira_client_id": self.jira_client_id or "",
            "jira_client_secret_set": bool(self.jira_client_secret),  # Don't expose actual secret
            "slack_client_id": self.slack_client_id or "",
            "slack_client_secret_set": bool(self.slack_client_secret),  # Don't expose actual secret
            "github_client_id": self.github_client_id or "",
            "github_client_secret_set": bool(self.github_client_secret),  # Don't expose actual secret
            "google_calendar_client_id": getattr(self, "google_calendar_client_id", "") or "",
            "google_calendar_client_secret_set": bool(getattr(self, "google_calendar_client_secret", "")),
            "outlook_calendar_client_id": getattr(self, "outlook_calendar_client_id", "") or "",
            "outlook_calendar_client_secret_set": bool(getattr(self, "outlook_calendar_client_secret", "")),
            "outlook_calendar_tenant_id": getattr(self, "outlook_calendar_tenant_id", "") or "",
            "microsoft_teams_client_id": getattr(self, "microsoft_teams_client_id", "") or "",
            "microsoft_teams_client_secret_set": bool(getattr(self, "microsoft_teams_client_secret", "")),
            "microsoft_teams_tenant_id": getattr(self, "microsoft_teams_tenant_id", "") or "",
            "asana_client_id": getattr(self, "asana_client_id", "") or "",
            "asana_client_secret_set": bool(getattr(self, "asana_client_secret", "")),
            "trello_api_key": getattr(self, "trello_api_key", "") or "",
            "trello_api_secret_set": bool(getattr(self, "trello_api_secret", "")),
            "gitlab_client_id": getattr(self, "gitlab_client_id", "") or "",
            "gitlab_client_secret_set": bool(getattr(self, "gitlab_client_secret", "")),
            "gitlab_instance_url": getattr(self, "gitlab_instance_url", "") or "",
            "quickbooks_client_id": getattr(self, "quickbooks_client_id", "") or "",
            "quickbooks_client_secret_set": bool(getattr(self, "quickbooks_client_secret", "")),
            "xero_client_id": getattr(self, "xero_client_id", "") or "",
            "xero_client_secret_set": bool(getattr(self, "xero_client_secret", "")),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_settings(cls):
        """Get the singleton settings instance, creating it if it doesn't exist.

        When creating a new Settings instance, it will be initialized from
        environment variables (.env file) as initial values.
        """
        try:
            settings = cls.query.first()
            if settings:
                return settings
        except Exception as e:
            # Handle case where table or columns don't exist yet (migration not run)
            # Check if it's a table/column error - if so, it's expected during migrations
            error_str = str(e)
            # Also check the underlying exception if it's a SQLAlchemy exception
            underlying_error = ""
            if hasattr(e, 'orig'):
                underlying_error = str(e.orig)
            elif hasattr(e, '__cause__') and e.__cause__:
                underlying_error = str(e.__cause__)
            
            combined_error = f"{error_str} {underlying_error}".lower()
            is_schema_error = (
                "undefinedcolumn" in combined_error
                or "does not exist" in combined_error
                or "no such column" in combined_error
                or "no such table" in combined_error
                or ("relation" in combined_error and "does not exist" in combined_error)
                or "operationalerror" in combined_error and ("no such table" in combined_error or "does not exist" in combined_error)
            )

            import logging

            logger = logging.getLogger(__name__)

            if is_schema_error:
                # This is expected during migrations when schema is incomplete
                # Only log at debug level to avoid cluttering logs
                logger.debug(
                    f"Settings table not available (migration may be pending): {error_str.split('LINE')[0] if 'LINE' in error_str else error_str}"
                )
            else:
                # Other errors should be logged as warnings
                logger.warning(f"Could not query settings: {e}")

            # Rollback the failed transaction
            try:
                db.session.rollback()
            except Exception:
                pass
            # Return fallback instance with defaults
            return cls()

        # Avoid performing session writes during flush/commit phases.
        # When called from default column factories (e.g., created_at=local_now),
        # SQLAlchemy may be in the middle of a flush. Writing here would raise
        # SAWarnings/ResourceClosedError. In that case, return a transient instance
        # with sensible defaults; the persistent row can be created later by
        # initialization code or explicit admin flows.
        try:
            if not getattr(db.session, "_flushing", False):
                # Create new settings instance initialized from environment variables
                settings = cls()
                # Initialize from environment variables (.env file)
                cls._initialize_from_env(settings)
                db.session.add(settings)
                db.session.commit()
                return settings
        except Exception:
            # If anything goes wrong creating the persistent row, rollback and
            # fall back to an in-memory Settings instance.
            try:
                db.session.rollback()
            except Exception:
                # Ignore rollback failures to avoid masking original contexts
                pass

        # Fallback: return a non-persisted Settings instance
        return cls()

    @classmethod
    def update_settings(cls, **kwargs):
        """Update settings with new values"""
        settings = cls.get_settings()

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow()
        db.session.commit()
        return settings

    @classmethod
    def _initialize_from_env(cls, settings_instance):
        """
        Initialize Settings instance from environment variables (.env file).
        This is called when creating a new Settings instance to use .env values
        as initial startup values.

        Args:
            settings_instance: Settings instance to initialize
        """
        # Map environment variable names to Settings model attributes
        env_mapping = {
            "TZ": "timezone",
            "CURRENCY": "currency",
            "ROUNDING_MINUTES": "rounding_minutes",
            "SINGLE_ACTIVE_TIMER": "single_active_timer",
            "ALLOW_SELF_REGISTER": "allow_self_register",
            "IDLE_TIMEOUT_MINUTES": "idle_timeout_minutes",
            "BACKUP_RETENTION_DAYS": "backup_retention_days",
            "BACKUP_TIME": "backup_time",
        }

        for env_var, attr_name in env_mapping.items():
            if hasattr(settings_instance, attr_name):
                env_value = os.getenv(env_var)
                if env_value is not None:
                    # Convert value types based on attribute type
                    current_value = getattr(settings_instance, attr_name)

                    if isinstance(current_value, bool):
                        # Handle boolean values
                        setattr(settings_instance, attr_name, env_value.lower() == "true")
                    elif isinstance(current_value, int):
                        # Handle integer values
                        try:
                            setattr(settings_instance, attr_name, int(env_value))
                        except (ValueError, TypeError):
                            pass  # Keep default if conversion fails
                    else:
                        # Handle string values
                        setattr(settings_instance, attr_name, env_value)

    @classmethod
    def sync_from_env(cls):
        """
        Sync Settings from environment variables (.env file) for fields that haven't
        been customized in the WebUI. This is useful for initializing Settings on startup
        or when new environment variables are added.

        Only updates fields that are still at their default values (not customized via WebUI).
        """
        try:
            settings = cls.get_settings()
            if not settings or not hasattr(settings, "id"):
                # Settings doesn't exist in DB yet, get_settings will create it
                return

            # Only sync if Settings was just created (id is None means it's a new instance)
            # For existing Settings, we don't overwrite WebUI changes
            # This method is mainly for ensuring new Settings get initialized from .env
            if settings.id is None:
                cls._initialize_from_env(settings)
                if hasattr(db.session, "add"):
                    db.session.add(settings)
                db.session.commit()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Could not sync Settings from environment: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
