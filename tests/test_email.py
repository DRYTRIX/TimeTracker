"""
Tests for email functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import current_app
from app.utils.email import (
    send_email, 
    test_email_configuration, 
    send_test_email,
    init_mail
)


class TestEmailConfiguration:
    """Tests for email configuration"""
    
    def test_init_mail(self, app):
        """Test email initialization"""
        with app.app_context():
            mail = init_mail(app)
            assert mail is not None
            assert 'MAIL_SERVER' in app.config
            assert 'MAIL_PORT' in app.config
            assert 'MAIL_DEFAULT_SENDER' in app.config
    
    def test_email_config_status_not_configured(self, app):
        """Test email configuration status when not configured"""
        with app.app_context():
            # Reset mail server to simulate unconfigured state
            app.config['MAIL_SERVER'] = 'localhost'
            
            status = test_email_configuration()
            
            assert status is not None
            assert 'configured' in status
            assert 'settings' in status
            assert 'errors' in status
            assert 'warnings' in status
            assert status['configured'] is False
            assert len(status['errors']) > 0
    
    def test_email_config_status_configured(self, app):
        """Test email configuration status when properly configured"""
        with app.app_context():
            # Set up proper configuration
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['MAIL_PORT'] = 587
            app.config['MAIL_USE_TLS'] = True
            app.config['MAIL_USE_SSL'] = False
            app.config['MAIL_USERNAME'] = 'test@example.com'
            app.config['MAIL_PASSWORD'] = 'test_password'
            app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'
            
            status = test_email_configuration()
            
            assert status is not None
            assert status['configured'] is True
            assert len(status['errors']) == 0
            assert status['settings']['server'] == 'smtp.gmail.com'
            assert status['settings']['port'] == 587
            assert status['settings']['password_set'] is True
    
    def test_email_config_warns_about_default_sender(self, app):
        """Test that configuration warns about default sender"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['MAIL_DEFAULT_SENDER'] = 'noreply@timetracker.local'
            
            status = test_email_configuration()
            
            assert len(status['warnings']) > 0
            assert any('Default sender' in w for w in status['warnings'])
    
    def test_email_config_errors_on_both_tls_and_ssl(self, app):
        """Test that configuration errors when both TLS and SSL are enabled"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['MAIL_USE_TLS'] = True
            app.config['MAIL_USE_SSL'] = True
            
            status = test_email_configuration()
            
            assert len(status['errors']) > 0
            assert any('TLS and SSL' in e for e in status['errors'])


class TestSendEmail:
    """Tests for sending emails"""
    
    @patch('app.utils.email.mail.send')
    @patch('app.utils.email.Thread')
    def test_send_email_success(self, mock_thread, mock_send, app):
        """Test sending email successfully"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            
            send_email(
                subject='Test Subject',
                recipients=['test@example.com'],
                text_body='Test body',
                html_body='<p>Test body</p>'
            )
            
            # Verify thread was started for async sending
            assert mock_thread.called
    
    def test_send_email_no_server(self, app, caplog):
        """Test sending email with no mail server configured"""
        with app.app_context():
            app.config['MAIL_SERVER'] = None
            
            send_email(
                subject='Test Subject',
                recipients=['test@example.com'],
                text_body='Test body'
            )
            
            # Should log a warning
            assert 'Mail server not configured' in caplog.text
    
    def test_send_email_no_recipients(self, app, caplog):
        """Test sending email with no recipients"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            
            send_email(
                subject='Test Subject',
                recipients=[],
                text_body='Test body'
            )
            
            # Should log a warning
            assert 'No recipients' in caplog.text
    
    @patch('app.utils.email.mail.send')
    def test_send_test_email_success(self, mock_send, app):
        """Test sending test email successfully"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['MAIL_DEFAULT_SENDER'] = 'test@example.com'
            
            success, message = send_test_email('recipient@example.com', 'Test Sender')
            
            assert success is True
            assert 'successfully' in message.lower()
            assert mock_send.called
    
    def test_send_test_email_invalid_recipient(self, app):
        """Test sending test email with invalid recipient"""
        with app.app_context():
            success, message = send_test_email('invalid-email', 'Test Sender')
            
            assert success is False
            assert 'Invalid' in message
    
    def test_send_test_email_no_server(self, app):
        """Test sending test email with no mail server"""
        with app.app_context():
            app.config['MAIL_SERVER'] = None
            
            success, message = send_test_email('test@example.com', 'Test Sender')
            
            assert success is False
            assert 'not configured' in message
    
    @patch('app.utils.email.mail.send')
    def test_send_test_email_exception(self, mock_send, app):
        """Test sending test email with exception"""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['MAIL_DEFAULT_SENDER'] = 'test@example.com'
            
            # Simulate exception
            mock_send.side_effect = Exception('SMTP error')
            
            success, message = send_test_email('test@example.com', 'Test Sender')
            
            assert success is False
            assert 'Failed' in message


class TestEmailIntegration:
    """Integration tests for email functionality"""
    
    def test_email_configuration_in_app_context(self, app):
        """Test that email configuration is available in app context"""
        with app.app_context():
            assert hasattr(current_app, 'config')
            assert 'MAIL_SERVER' in current_app.config
            assert 'MAIL_PORT' in current_app.config
            assert 'MAIL_USE_TLS' in current_app.config
            assert 'MAIL_DEFAULT_SENDER' in current_app.config
    
    def test_email_settings_from_environment(self, app, monkeypatch):
        """Test that email settings are loaded from environment"""
        # Set environment variables
        monkeypatch.setenv('MAIL_SERVER', 'smtp.test.com')
        monkeypatch.setenv('MAIL_PORT', '465')
        monkeypatch.setenv('MAIL_USE_SSL', 'true')
        
        # Reinitialize mail with new environment
        with app.app_context():
            mail = init_mail(app)
            
            assert app.config['MAIL_SERVER'] == 'smtp.test.com'
            assert app.config['MAIL_PORT'] == 465
            assert app.config['MAIL_USE_SSL'] is True


class TestDatabaseEmailConfiguration:
    """Tests for database-backed email configuration"""
    
    def test_get_mail_config_when_disabled(self, app):
        """Test get_mail_config returns None when database config is disabled"""
        with app.app_context():
            from app.models import Settings
            settings = Settings.get_settings()
            settings.mail_enabled = False
            settings.mail_server = 'smtp.test.com'
            
            config = settings.get_mail_config()
            assert config is None
    
    def test_get_mail_config_when_enabled(self, app):
        """Test get_mail_config returns config when enabled"""
        with app.app_context():
            from app.models import Settings
            settings = Settings.get_settings()
            settings.mail_enabled = True
            settings.mail_server = 'smtp.test.com'
            settings.mail_port = 587
            settings.mail_use_tls = True
            settings.mail_use_ssl = False
            settings.mail_username = 'test@example.com'
            settings.mail_password = 'test_password'
            settings.mail_default_sender = 'noreply@example.com'
            
            config = settings.get_mail_config()
            
            assert config is not None
            assert config['MAIL_SERVER'] == 'smtp.test.com'
            assert config['MAIL_PORT'] == 587
            assert config['MAIL_USE_TLS'] is True
            assert config['MAIL_USE_SSL'] is False
            assert config['MAIL_USERNAME'] == 'test@example.com'
            assert config['MAIL_PASSWORD'] == 'test_password'
            assert config['MAIL_DEFAULT_SENDER'] == 'noreply@example.com'
    
    def test_init_mail_uses_database_config(self, app):
        """Test that init_mail uses database settings when available"""
        with app.app_context():
            from app.models import Settings
            from app.utils.email import init_mail
            
            settings = Settings.get_settings()
            settings.mail_enabled = True
            settings.mail_server = 'smtp.database.com'
            settings.mail_port = 465
            app.db.session.commit()
            
            init_mail(app)
            
            # Should use database settings
            assert app.config['MAIL_SERVER'] == 'smtp.database.com'
            assert app.config['MAIL_PORT'] == 465
    
    def test_reload_mail_config(self, app):
        """Test reloading email configuration"""
        with app.app_context():
            from app.models import Settings
            from app.utils.email import reload_mail_config
            
            # Set up database config
            settings = Settings.get_settings()
            settings.mail_enabled = True
            settings.mail_server = 'smtp.reloaded.com'
            app.db.session.commit()
            
            # Reload configuration
            success = reload_mail_config(app)
            
            assert success is True
            assert app.config['MAIL_SERVER'] == 'smtp.reloaded.com'
    
    def test_test_email_configuration_shows_source(self, app):
        """Test that configuration status shows source (database or environment)"""
        with app.app_context():
            from app.models import Settings
            from app.utils.email import test_email_configuration
            
            # Test with database config
            settings = Settings.get_settings()
            settings.mail_enabled = True
            settings.mail_server = 'smtp.database.com'
            app.db.session.commit()
            
            status = test_email_configuration()
            
            assert 'source' in status
            assert status['source'] == 'database'
            
            # Test with environment config
            settings.mail_enabled = False
            app.db.session.commit()
            
            status = test_email_configuration()
            assert status['source'] == 'environment'


# Fixtures
@pytest.fixture
def mock_mail_send():
    """Mock the mail.send method"""
    with patch('app.utils.email.mail.send') as mock:
        yield mock

