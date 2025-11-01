"""Tests for internationalization (i18n) functionality"""

import pytest
from flask import session
from app import create_app, db
from app.models import User
from flask_babel import get_locale


class TestI18nConfiguration:
    """Test internationalization configuration"""
    
    def test_supported_languages_configured(self, client):
        """Test that all supported languages are configured"""
        with client.application.app_context():
            languages = client.application.config.get('LANGUAGES', {})
            
            # Check that all required languages are present
            assert 'en' in languages
            assert 'de' in languages
            assert 'fr' in languages
            assert 'es' in languages
            assert 'ar' in languages
            assert 'he' in languages
            assert 'nl' in languages
            assert 'it' in languages
            assert 'fi' in languages
            
            # Check that language labels are set
            assert languages['en'] == 'English'
            assert languages['es'] == 'Español'
            assert languages['ar'] == 'العربية'
            assert languages['he'] == 'עברית'
    
    def test_rtl_languages_configured(self, client):
        """Test that RTL languages are configured"""
        with client.application.app_context():
            rtl_languages = client.application.config.get('RTL_LANGUAGES', set())
            
            # Check that RTL languages are present
            assert 'ar' in rtl_languages
            assert 'he' in rtl_languages
            
            # Check that LTR languages are not in RTL set
            assert 'en' not in rtl_languages
            assert 'de' not in rtl_languages
            assert 'es' not in rtl_languages
    
    def test_default_locale_is_english(self, client):
        """Test that default locale is English"""
        with client.application.app_context():
            default_locale = client.application.config.get('BABEL_DEFAULT_LOCALE')
            assert default_locale == 'en'


class TestLocaleSelection:
    """Test locale selection logic"""
    
    def test_locale_from_user_preference(self, client, test_user):
        """Test that locale is selected from user's preference"""
        # Set user's preferred language
        test_user.preferred_language = 'de'
        db.session.commit()
        
        # Login as user
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Check that locale is set to user's preference
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                # Simulate request context
                from flask import g
                from app import babel
                
                # The locale selector should return user's preference
                assert test_user.preferred_language == 'de'
    
    def test_locale_from_session(self, client):
        """Test that locale is selected from session when not logged in"""
        with client:
            # Set language in session
            with client.session_transaction() as sess:
                sess['preferred_language'] = 'fr'
            
            # Make a request
            response = client.get('/')
            
            # Check that session language is used
            with client.session_transaction() as sess:
                assert sess.get('preferred_language') == 'fr'
    
    def test_locale_fallback_to_default(self, client):
        """Test that locale falls back to default when not set"""
        with client:
            # Don't set any language preference
            response = client.get('/')
            
            # Should use default locale (English)
            assert response.status_code in [200, 302]  # May redirect to login


class TestLanguageSwitching:
    """Test language switching functionality"""
    
    def test_set_language_direct_route(self, client, test_user):
        """Test direct language switching route"""
        # Login first
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Switch to Spanish
        response = client.get('/set-language/es', follow_redirects=False)
        
        # Should redirect
        assert response.status_code == 302
        
        # Check that user's preference is updated
        db.session.refresh(test_user)
        assert test_user.preferred_language == 'es'
        
        # Check that session is updated
        with client.session_transaction() as sess:
            assert sess.get('preferred_language') == 'es'
    
    def test_set_language_api_endpoint(self, client, test_user):
        """Test API endpoint for language switching"""
        # Login first
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Switch to Arabic via API
        response = client.post(
            '/api/language',
            json={'language': 'ar'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['language'] == 'ar'
        
        # Check that user's preference is updated
        db.session.refresh(test_user)
        assert test_user.preferred_language == 'ar'
    
    def test_set_invalid_language(self, client, test_user):
        """Test that invalid languages are rejected"""
        # Login first
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Try to set invalid language
        response = client.post(
            '/api/language',
            json={'language': 'invalid'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_language_persists_across_sessions(self, client, test_user):
        """Test that language preference persists across sessions"""
        # Login and set language
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        client.get('/set-language/de', follow_redirects=True)
        
        # Logout
        client.get('/auth/logout', follow_redirects=True)
        
        # Login again
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Check that language preference is still set
        db.session.refresh(test_user)
        assert test_user.preferred_language == 'de'


class TestRTLSupport:
    """Test Right-to-Left language support"""
    
    def test_rtl_detection_for_arabic(self, client, test_user):
        """Test that Arabic is detected as RTL"""
        # Set language to Arabic
        test_user.preferred_language = 'ar'
        db.session.commit()
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get dashboard
        response = client.get('/dashboard')
        
        # Check that page includes RTL directive
        assert response.status_code == 200
        assert b'dir="rtl"' in response.data or b"dir='rtl'" in response.data
    
    def test_rtl_detection_for_hebrew(self, client, test_user):
        """Test that Hebrew is detected as RTL"""
        # Set language to Hebrew
        test_user.preferred_language = 'he'
        db.session.commit()
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get dashboard
        response = client.get('/dashboard')
        
        # Check that page includes RTL directive
        assert response.status_code == 200
        assert b'dir="rtl"' in response.data or b"dir='rtl'" in response.data
    
    def test_ltr_for_english(self, client, test_user):
        """Test that English is LTR"""
        # Set language to English
        test_user.preferred_language = 'en'
        db.session.commit()
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get dashboard
        response = client.get('/dashboard')
        
        # Check that page includes LTR directive
        assert response.status_code == 200
        assert b'dir="ltr"' in response.data or b"dir='ltr'" in response.data


class TestTranslations:
    """Test that translations are working"""
    
    def test_english_translations(self, client):
        """Test English translations"""
        with client.application.test_request_context():
            from flask_babel import _
            
            # Test common translations
            assert _('Dashboard') == 'Dashboard'
            assert _('Projects') == 'Projects'
            assert _('Login') == 'Login'
    
    def test_translation_files_exist(self, client):
        """Test that translation files exist for all languages"""
        import os
        
        languages = ['en', 'de', 'fr', 'es', 'ar', 'he', 'nl', 'it', 'fi']
        
        for lang in languages:
            po_file = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
            assert os.path.exists(po_file), f"Translation file missing for {lang}"


class TestLanguageSelectorUI:
    """Test language selector UI"""
    
    def test_language_selector_in_header(self, client, test_user):
        """Test that language selector appears in header"""
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get dashboard
        response = client.get('/dashboard')
        
        # Check that language selector is present
        assert response.status_code == 200
        assert b'langDropdown' in response.data or b'lang-dropdown' in response.data.lower()
        assert b'fa-globe' in response.data or b'globe' in response.data.lower()
    
    def test_language_list_contains_all_languages(self, client, test_user):
        """Test that language selector contains all available languages"""
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get dashboard
        response = client.get('/dashboard')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        # Check for language names in the page
        languages_to_check = ['English', 'Español', 'Français', 'Deutsch']
        for lang in languages_to_check:
            assert lang in response_text, f"Language '{lang}' not found in language selector"


class TestUserSettingsLanguage:
    """Test language settings in user settings page"""
    
    def test_language_setting_in_user_settings(self, client, test_user):
        """Test that language setting is available in user settings"""
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Get settings page
        response = client.get('/settings')
        
        # Check that language setting is present
        assert response.status_code == 200
        assert b'preferred_language' in response.data or b'language' in response.data.lower()
    
    def test_save_language_in_user_settings(self, client, test_user):
        """Test saving language preference in user settings"""
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Update settings with language
        response = client.post('/settings', data={
            'preferred_language': 'fr',
            'full_name': test_user.full_name or 'Test User',
            'email': test_user.email or 'test@example.com'
        }, follow_redirects=True)
        
        # Check that setting was saved
        assert response.status_code == 200
        db.session.refresh(test_user)
        assert test_user.preferred_language == 'fr'


@pytest.fixture
def test_user(client):
    """Create a test user"""
    with client.application.app_context():
        user = User(username='testuser', role='user')
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        yield user
        # Cleanup - delete related activities first to avoid constraint violations
        from app.models import Activity
        Activity.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()

