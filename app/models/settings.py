from datetime import datetime
from app import db
from app.config import Config
import os

class Settings(db.Model):
    """Settings model for system configuration"""
    
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    timezone = db.Column(db.String(50), default='Europe/Rome', nullable=False)
    currency = db.Column(db.String(3), default='EUR', nullable=False)
    rounding_minutes = db.Column(db.Integer, default=1, nullable=False)
    single_active_timer = db.Column(db.Boolean, default=True, nullable=False)
    allow_self_register = db.Column(db.Boolean, default=True, nullable=False)
    idle_timeout_minutes = db.Column(db.Integer, default=30, nullable=False)
    backup_retention_days = db.Column(db.Integer, default=30, nullable=False)
    backup_time = db.Column(db.String(5), default='02:00', nullable=False)  # HH:MM format
    export_delimiter = db.Column(db.String(1), default=',', nullable=False)
    
    # Company branding for invoices
    company_name = db.Column(db.String(200), default='Your Company Name', nullable=False)
    company_address = db.Column(db.Text, default='Your Company Address', nullable=False)
    company_email = db.Column(db.String(200), default='info@yourcompany.com', nullable=False)
    company_phone = db.Column(db.String(50), default='+1 (555) 123-4567', nullable=False)
    company_website = db.Column(db.String(200), default='www.yourcompany.com', nullable=False)
    company_logo_filename = db.Column(db.String(255), default='', nullable=True)  # Changed from company_logo_path
    company_tax_id = db.Column(db.String(100), default='', nullable=True)
    company_bank_info = db.Column(db.Text, default='', nullable=True)
    
    # PDF template customization
    invoice_pdf_template_html = db.Column(db.Text, default='', nullable=True)
    invoice_pdf_template_css = db.Column(db.Text, default='', nullable=True)
    invoice_pdf_design_json = db.Column(db.Text, default='', nullable=True)  # Konva.js design state
    
    # Invoice defaults
    invoice_prefix = db.Column(db.String(10), default='INV', nullable=False)
    invoice_start_number = db.Column(db.Integer, default=1000, nullable=False)
    invoice_terms = db.Column(db.Text, default='Payment is due within 30 days of invoice date.', nullable=False)
    invoice_notes = db.Column(db.Text, default='Thank you for your business!', nullable=False)
    
    # Privacy and analytics settings
    allow_analytics = db.Column(db.Boolean, default=True, nullable=False)  # Controls system info sharing for analytics
    
    # Kiosk mode settings
    kiosk_mode_enabled = db.Column(db.Boolean, default=False, nullable=False)
    kiosk_auto_logout_minutes = db.Column(db.Integer, default=15, nullable=False)
    kiosk_allow_camera_scanning = db.Column(db.Boolean, default=True, nullable=False)
    kiosk_require_reason_for_adjustments = db.Column(db.Boolean, default=False, nullable=False)
    kiosk_default_movement_type = db.Column(db.String(20), default='adjustment', nullable=False)
    
    # Email configuration settings (stored in database, takes precedence over environment variables)
    mail_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Enable database-backed email config
    mail_server = db.Column(db.String(255), default='', nullable=True)
    mail_port = db.Column(db.Integer, default=587, nullable=True)
    mail_use_tls = db.Column(db.Boolean, default=True, nullable=True)
    mail_use_ssl = db.Column(db.Boolean, default=False, nullable=True)
    mail_username = db.Column(db.String(255), default='', nullable=True)
    mail_password = db.Column(db.String(255), default='', nullable=True)  # Store encrypted in production
    mail_default_sender = db.Column(db.String(255), default='', nullable=True)
    
    # Integration OAuth credentials (stored in database, takes precedence over environment variables)
    # Jira
    jira_client_id = db.Column(db.String(255), default='', nullable=True)
    jira_client_secret = db.Column(db.String(255), default='', nullable=True)  # Store encrypted in production
    # Slack
    slack_client_id = db.Column(db.String(255), default='', nullable=True)
    slack_client_secret = db.Column(db.String(255), default='', nullable=True)  # Store encrypted in production
    # GitHub
    github_client_id = db.Column(db.String(255), default='', nullable=True)
    github_client_secret = db.Column(db.String(255), default='', nullable=True)  # Store encrypted in production
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, **kwargs):
        # Set defaults from config
        self.timezone = kwargs.get('timezone', Config.TZ)
        self.currency = kwargs.get('currency', Config.CURRENCY)
        self.rounding_minutes = kwargs.get('rounding_minutes', Config.ROUNDING_MINUTES)
        self.single_active_timer = kwargs.get('single_active_timer', Config.SINGLE_ACTIVE_TIMER)
        self.allow_self_register = kwargs.get('allow_self_register', Config.ALLOW_SELF_REGISTER)
        self.idle_timeout_minutes = kwargs.get('idle_timeout_minutes', Config.IDLE_TIMEOUT_MINUTES)
        self.backup_retention_days = kwargs.get('backup_retention_days', Config.BACKUP_RETENTION_DAYS)
        self.backup_time = kwargs.get('backup_time', Config.BACKUP_TIME)
        self.export_delimiter = kwargs.get('export_delimiter', ',')
        
        # Set company branding defaults
        self.company_name = kwargs.get('company_name', 'Your Company Name')
        self.company_address = kwargs.get('company_address', 'Your Company Address')
        self.company_email = kwargs.get('company_email', 'info@yourcompany.com')
        self.company_phone = kwargs.get('company_phone', '+1 (555) 123-4567')
        self.company_website = kwargs.get('company_website', 'www.yourcompany.com')
        self.company_logo_filename = kwargs.get('company_logo_filename', '')
        self.company_tax_id = kwargs.get('company_tax_id', '')
        self.company_bank_info = kwargs.get('company_bank_info', '')
        
        # PDF template customization
        self.invoice_pdf_template_html = kwargs.get('invoice_pdf_template_html', '')
        self.invoice_pdf_template_css = kwargs.get('invoice_pdf_template_css', '')
        self.invoice_pdf_design_json = kwargs.get('invoice_pdf_design_json', '')
        
        # Set invoice defaults
        self.invoice_prefix = kwargs.get('invoice_prefix', 'INV')
        self.invoice_start_number = kwargs.get('invoice_start_number', 1000)
        self.invoice_terms = kwargs.get('invoice_terms', 'Payment is due within 30 days of invoice date.')
        self.invoice_notes = kwargs.get('invoice_notes', 'Thank you for your business!')
        
        # Kiosk mode defaults
        self.kiosk_mode_enabled = kwargs.get('kiosk_mode_enabled', False)
        self.kiosk_auto_logout_minutes = kwargs.get('kiosk_auto_logout_minutes', 15)
        self.kiosk_allow_camera_scanning = kwargs.get('kiosk_allow_camera_scanning', True)
        self.kiosk_require_reason_for_adjustments = kwargs.get('kiosk_require_reason_for_adjustments', False)
        self.kiosk_default_movement_type = kwargs.get('kiosk_default_movement_type', 'adjustment')
        
        # Email configuration defaults
        self.mail_enabled = kwargs.get('mail_enabled', False)
        self.mail_server = kwargs.get('mail_server', '')
        self.mail_port = kwargs.get('mail_port', 587)
        self.mail_use_tls = kwargs.get('mail_use_tls', True)
        self.mail_use_ssl = kwargs.get('mail_use_ssl', False)
        self.mail_username = kwargs.get('mail_username', '')
        self.mail_password = kwargs.get('mail_password', '')
        self.mail_default_sender = kwargs.get('mail_default_sender', '')
        
        # Integration OAuth credentials defaults
        self.jira_client_id = kwargs.get('jira_client_id', '')
        self.jira_client_secret = kwargs.get('jira_client_secret', '')
        self.slack_client_id = kwargs.get('slack_client_id', '')
        self.slack_client_secret = kwargs.get('slack_client_secret', '')
        self.github_client_id = kwargs.get('github_client_id', '')
        self.github_client_secret = kwargs.get('github_client_secret', '')
    
    def __repr__(self):
        return f'<Settings {self.id}>'
    
    def get_logo_url(self):
        """Get the full URL for the company logo"""
        if self.company_logo_filename:
            return f'/uploads/logos/{self.company_logo_filename}'
        return None
    
    def get_logo_path(self):
        """Get the full file system path for the company logo"""
        if not self.company_logo_filename:
            return None
            
        try:
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            return os.path.join(upload_folder, self.company_logo_filename)
        except RuntimeError:
            # current_app not available (e.g., during testing or initialization)
            # Fallback to a relative path
            return os.path.join('app', 'static', 'uploads', 'logos', self.company_logo_filename)
    
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
                'MAIL_SERVER': self.mail_server,
                'MAIL_PORT': self.mail_port or 587,
                'MAIL_USE_TLS': self.mail_use_tls if self.mail_use_tls is not None else True,
                'MAIL_USE_SSL': self.mail_use_ssl if self.mail_use_ssl is not None else False,
                'MAIL_USERNAME': self.mail_username or None,
                'MAIL_PASSWORD': self.mail_password or None,
                'MAIL_DEFAULT_SENDER': self.mail_default_sender or 'noreply@timetracker.local',
            }
        return None
    
    def get_integration_credentials(self, provider: str) -> dict:
        """Get integration OAuth credentials, preferring database settings over environment variables.
        
        Args:
            provider: One of 'jira', 'slack', or 'github'
            
        Returns:
            dict with 'client_id' and 'client_secret' keys, or empty dict if not configured
        """
        import os
        
        if provider == 'jira':
            client_id = self.jira_client_id or os.getenv('JIRA_CLIENT_ID', '')
            client_secret = self.jira_client_secret or os.getenv('JIRA_CLIENT_SECRET', '')
        elif provider == 'slack':
            client_id = self.slack_client_id or os.getenv('SLACK_CLIENT_ID', '')
            client_secret = self.slack_client_secret or os.getenv('SLACK_CLIENT_SECRET', '')
        elif provider == 'github':
            client_id = self.github_client_id or os.getenv('GITHUB_CLIENT_ID', '')
            client_secret = self.github_client_secret or os.getenv('GITHUB_CLIENT_SECRET', '')
        else:
            return {}
        
        return {
            'client_id': client_id,
            'client_secret': client_secret
        }
    
    def to_dict(self):
        """Convert settings to dictionary for API responses"""
        return {
            'id': self.id,
            'timezone': self.timezone,
            'currency': self.currency,
            'rounding_minutes': self.rounding_minutes,
            'single_active_timer': self.single_active_timer,
            'allow_self_register': self.allow_self_register,
            'idle_timeout_minutes': self.idle_timeout_minutes,
            'backup_retention_days': self.backup_retention_days,
            'backup_time': self.backup_time,
            'export_delimiter': self.export_delimiter,
            'company_name': self.company_name,
            'company_address': self.company_address,
            'company_email': self.company_email,
            'company_phone': self.company_phone,
            'company_website': self.company_website,
            'company_logo_filename': self.company_logo_filename,
            'company_logo_url': self.get_logo_url(),
            'has_logo': self.has_logo(),
            'company_tax_id': self.company_tax_id,
            'company_bank_info': self.company_bank_info,
            'invoice_prefix': self.invoice_prefix,
            'invoice_start_number': self.invoice_start_number,
            'invoice_terms': self.invoice_terms,
            'invoice_notes': self.invoice_notes,
            'invoice_pdf_template_html': self.invoice_pdf_template_html,
            'invoice_pdf_template_css': self.invoice_pdf_template_css,
            'invoice_pdf_design_json': self.invoice_pdf_design_json,
            'allow_analytics': self.allow_analytics,
            'mail_enabled': self.mail_enabled,
            'mail_server': self.mail_server,
            'mail_port': self.mail_port,
            'mail_use_tls': self.mail_use_tls,
            'mail_use_ssl': self.mail_use_ssl,
            'mail_username': self.mail_username,
            'mail_password_set': bool(self.mail_password),  # Don't expose actual password
            'mail_default_sender': self.mail_default_sender,
            'jira_client_id': self.jira_client_id or '',
            'jira_client_secret_set': bool(self.jira_client_secret),  # Don't expose actual secret
            'slack_client_id': self.slack_client_id or '',
            'slack_client_secret_set': bool(self.slack_client_secret),  # Don't expose actual secret
            'github_client_id': self.github_client_id or '',
            'github_client_secret_set': bool(self.github_client_secret),  # Don't expose actual secret
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
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
            # Handle case where columns don't exist yet (migration not run)
            # Log but don't fail - return fallback instance
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not query settings (migration may not be run): {e}")
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
            'TZ': 'timezone',
            'CURRENCY': 'currency',
            'ROUNDING_MINUTES': 'rounding_minutes',
            'SINGLE_ACTIVE_TIMER': 'single_active_timer',
            'ALLOW_SELF_REGISTER': 'allow_self_register',
            'IDLE_TIMEOUT_MINUTES': 'idle_timeout_minutes',
            'BACKUP_RETENTION_DAYS': 'backup_retention_days',
            'BACKUP_TIME': 'backup_time',
        }
        
        for env_var, attr_name in env_mapping.items():
            if hasattr(settings_instance, attr_name):
                env_value = os.getenv(env_var)
                if env_value is not None:
                    # Convert value types based on attribute type
                    current_value = getattr(settings_instance, attr_name)
                    
                    if isinstance(current_value, bool):
                        # Handle boolean values
                        setattr(settings_instance, attr_name, env_value.lower() == 'true')
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
            if not settings or not hasattr(settings, 'id'):
                # Settings doesn't exist in DB yet, get_settings will create it
                return
            
            # Only sync if Settings was just created (id is None means it's a new instance)
            # For existing Settings, we don't overwrite WebUI changes
            # This method is mainly for ensuring new Settings get initialized from .env
            if settings.id is None:
                cls._initialize_from_env(settings)
                if hasattr(db.session, 'add'):
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
