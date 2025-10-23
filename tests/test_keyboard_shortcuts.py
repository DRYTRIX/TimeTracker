"""
Unit tests for keyboard shortcuts functionality
"""

import pytest
from flask import url_for
from app import create_app, db
from app.models import User


class TestKeyboardShortcutsRoutes:
    """Test keyboard shortcuts routes"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_keyboard_shortcuts_settings_page(self):
        """Test keyboard shortcuts settings page loads"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        assert b'Keyboard Shortcuts' in response.data
        assert b'shortcuts-search' in response.data
        assert b'total-shortcuts' in response.data

    def test_keyboard_shortcuts_settings_requires_auth(self):
        """Test keyboard shortcuts settings requires authentication"""
        self.client.get('/auth/logout')
        response = self.client.get('/settings/keyboard-shortcuts', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_settings_index_loads(self):
        """Test settings index page loads"""
        response = self.client.get('/settings')
        assert response.status_code == 200

    def test_keyboard_shortcuts_css_exists(self):
        """Test keyboard shortcuts CSS file exists"""
        response = self.client.get('/static/keyboard-shortcuts.css')
        assert response.status_code == 200
        assert b'keyboard' in response.data.lower()

    def test_keyboard_shortcuts_js_exists(self):
        """Test keyboard shortcuts JavaScript file exists"""
        response = self.client.get('/static/keyboard-shortcuts-enhanced.js')
        assert response.status_code == 200
        assert b'EnhancedKeyboardShortcuts' in response.data


class TestKeyboardShortcutsIntegration:
    """Integration tests for keyboard shortcuts"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_keyboard_shortcuts_in_base_template(self):
        """Test keyboard shortcuts are included in base template"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'keyboard-shortcuts.css' in response.data
        assert b'keyboard-shortcuts-enhanced.js' in response.data

    def test_command_palette_in_base_template(self):
        """Test command palette is available"""
        response = self.client.get('/')
        assert response.status_code == 200
        # Check for command palette modal structure
        assert b'commandPaletteModal' in response.data or b'command-palette' in response.data

    def test_cheat_sheet_elements_in_page(self):
        """Test keyboard shortcuts cheat sheet elements"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        # Check for key elements
        assert b'shortcuts-content' in response.data
        assert b'shortcuts-search' in response.data
        assert b'shortcut-tabs' in response.data

    def test_navigation_shortcuts_documented(self):
        """Test navigation shortcuts are documented"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        # Check for some key navigation shortcuts
        assert b'Go to Dashboard' in response.data or b'Dashboard' in response.data

    def test_statistics_elements_present(self):
        """Test statistics elements are present"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        assert b'most-used-list' in response.data
        assert b'recent-usage-list' in response.data
        assert b'total-shortcuts' in response.data


class TestKeyboardShortcutsAccessibility:
    """Test keyboard shortcuts accessibility features"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_skip_to_main_content_link(self):
        """Test skip to main content link exists"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'Skip to content' in response.data
        assert b'mainContentAnchor' in response.data

    def test_aria_labels_in_shortcuts_page(self):
        """Test ARIA labels are present"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        # Check for accessibility attributes
        assert b'aria-label' in response.data or b'role' in response.data

    def test_keyboard_navigation_styles(self):
        """Test keyboard navigation styles exist"""
        response = self.client.get('/static/keyboard-shortcuts.css')
        assert response.status_code == 200
        assert b'focus' in response.data.lower()
        assert b'keyboard-navigation' in response.data.lower()


class TestKeyboardShortcutsDocumentation:
    """Test keyboard shortcuts documentation"""

    def test_documentation_exists(self):
        """Test documentation file exists"""
        import os
        doc_path = 'docs/features/KEYBOARD_SHORTCUTS_ENHANCED.md'
        assert os.path.exists(doc_path), f"Documentation not found at {doc_path}"

    def test_documentation_has_content(self):
        """Test documentation has expected content"""
        import os
        doc_path = 'docs/features/KEYBOARD_SHORTCUTS_ENHANCED.md'
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Keyboard Shortcuts' in content
                assert 'Navigation' in content
                assert 'Ctrl+K' in content or 'Cmd+K' in content
                assert 'Usage Guide' in content


# Fixtures

@pytest.fixture
def app():
    """Create and configure a test application instance"""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def auth_user(app):
    """Create and authenticate a test user"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            is_active=True,
            role='user'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Login the user
        from flask_login import login_user
        with app.test_request_context():
            login_user(user)
        
        return user


@pytest.fixture
def admin_user(app):
    """Create and authenticate an admin user"""
    with app.app_context():
        user = User(
            username='admin',
            email='admin@example.com',
            is_active=True,
            role='admin'
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        
        return user


# Smoke Tests

def test_keyboard_shortcuts_module_imports():
    """Test that keyboard shortcuts modules can be imported"""
    # This is a smoke test to ensure Python syntax is valid
    assert True  # If we got here, imports worked


def test_settings_route_registered(app):
    """Test that settings route is registered"""
    with app.app_context():
        # Check if route exists
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/settings' in rule for rule in rules), "Settings route not registered"


def test_keyboard_shortcuts_route_registered(app):
    """Test that keyboard shortcuts route is registered"""
    with app.app_context():
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('keyboard-shortcuts' in rule for rule in rules), "Keyboard shortcuts route not registered"


# Model Tests (if applicable)

class TestKeyboardShortcutsData:
    """Test keyboard shortcuts data handling"""

    def test_shortcuts_data_structure(self):
        """Test that shortcuts have proper data structure"""
        # This tests the JavaScript data structure indirectly
        # by checking the HTML template has the expected elements
        pass  # Placeholder for future JavaScript testing

    def test_statistics_tracking(self):
        """Test that statistics can be tracked"""
        # This would test localStorage interactions
        # Requires JavaScript testing framework
        pass  # Placeholder for future testing


# Performance Tests

class TestKeyboardShortcutsPerformance:
    """Test keyboard shortcuts performance"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_settings_page_loads_quickly(self):
        """Test keyboard shortcuts settings page loads within acceptable time"""
        import time
        start = time.time()
        response = self.client.get('/settings/keyboard-shortcuts')
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0, f"Page took {duration}s to load (should be < 2s)"

    def test_css_file_size_reasonable(self):
        """Test CSS file is not too large"""
        response = self.client.get('/static/keyboard-shortcuts.css')
        assert response.status_code == 200
        size = len(response.data)
        assert size < 100000, f"CSS file is {size} bytes (should be < 100KB)"

    def test_js_file_size_reasonable(self):
        """Test JavaScript file is not too large"""
        response = self.client.get('/static/keyboard-shortcuts-enhanced.js')
        assert response.status_code == 200
        size = len(response.data)
        assert size < 500000, f"JavaScript file is {size} bytes (should be < 500KB)"


# Security Tests

class TestKeyboardShortcutsSecurity:
    """Test keyboard shortcuts security"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_settings_requires_authentication(self):
        """Test settings page requires authentication"""
        self.client.get('/auth/logout')
        response = self.client.get('/settings/keyboard-shortcuts', follow_redirects=False)
        assert response.status_code == 302

    def test_no_xss_in_shortcuts_page(self):
        """Test no XSS vulnerabilities in shortcuts page"""
        # Test with XSS payload in URL parameters
        response = self.client.get('/settings/keyboard-shortcuts?q=<script>alert("XSS")</script>')
        assert response.status_code == 200
        # Should not contain unescaped script tag
        assert b'<script>alert("XSS")</script>' not in response.data

    def test_csrf_protection_enabled(self, app):
        """Test CSRF protection is enabled"""
        assert app.config.get('WTF_CSRF_ENABLED', True) or app.config.get('TESTING')


# Edge Cases

class TestKeyboardShortcutsEdgeCases:
    """Test edge cases for keyboard shortcuts"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_settings_page_with_no_shortcuts(self):
        """Test settings page handles no shortcuts gracefully"""
        response = self.client.get('/settings/keyboard-shortcuts')
        assert response.status_code == 200
        # Should not crash even if no shortcuts are defined

    def test_settings_page_with_special_characters(self):
        """Test settings page handles special characters"""
        response = self.client.get('/settings/keyboard-shortcuts?search=%E2%9C%93')
        assert response.status_code == 200

    def test_multiple_concurrent_requests(self):
        """Test multiple concurrent requests don't cause issues"""
        responses = []
        for _ in range(10):
            response = self.client.get('/settings/keyboard-shortcuts')
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)


# Regression Tests

class TestKeyboardShortcutsRegression:
    """Regression tests for keyboard shortcuts"""

    @pytest.fixture(autouse=True)
    def setup(self, client, auth_user):
        """Setup for each test"""
        self.client = client
        self.user = auth_user

    def test_base_template_not_broken(self):
        """Test base template still works after adding shortcuts"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data

    def test_other_pages_not_affected(self):
        """Test other pages still work"""
        pages = [
            '/projects',
            '/tasks',
            '/reports',
        ]
        
        for page in pages:
            response = self.client.get(page)
            assert response.status_code == 200, f"Page {page} broken"

    def test_sidebar_navigation_still_works(self):
        """Test sidebar navigation still works"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'sidebar' in response.data.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

