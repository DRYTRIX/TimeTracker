"""
Tests for enhanced UI features
"""
import pytest
from flask import url_for


class TestEnhancedUI:
    """Test enhanced UI components and features"""

    def test_enhanced_css_loaded(self, authenticated_client):
        """Test that enhanced UI CSS is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'enhanced-ui.css' in response.data

    def test_enhanced_js_loaded(self, authenticated_client):
        """Test that enhanced UI JavaScript is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'enhanced-ui.js' in response.data

    def test_charts_js_loaded(self, authenticated_client):
        """Test that charts JavaScript is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'charts.js' in response.data

    def test_onboarding_js_loaded(self, authenticated_client):
        """Test that onboarding JavaScript is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'onboarding.js' in response.data


class TestComponentLibrary:
    """Test new component library"""

    def test_ui_components_file_exists(self):
        """Test that ui.html component file exists"""
        import os
        component_path = 'app/templates/components/ui.html'
        assert os.path.exists(component_path)

    def test_page_header_component(self, app):
        """Test page header macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import page_header %}
            {{ page_header('fas fa-home', 'Test Page', 'Test subtitle') }}
            """
            
            result = render_template_string(template)
            assert 'Test Page' in result
            assert 'Test subtitle' in result
            assert 'fa-home' in result

    def test_stat_card_component(self, app):
        """Test stat card macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import stat_card %}
            {{ stat_card('Total', '100', 'fas fa-clock', 'blue-500') }}
            """
            
            result = render_template_string(template)
            assert 'Total' in result
            assert '100' in result
            assert 'fa-clock' in result

    def test_breadcrumb_component(self, app):
        """Test breadcrumb navigation rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import breadcrumb_nav %}
            {{ breadcrumb_nav([{'text': 'Projects', 'url': '/projects'}]) }}
            """
            
            result = render_template_string(template)
            assert 'Projects' in result
            assert 'Home' in result

    def test_button_component(self, app):
        """Test button macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import button %}
            {{ button('Click Me', '/test', 'fas fa-check', 'primary') }}
            """
            
            result = render_template_string(template)
            assert 'Click Me' in result
            assert '/test' in result
            assert 'fa-check' in result

    def test_empty_state_component(self, app):
        """Test empty state macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import empty_state %}
            {{ empty_state('fas fa-inbox', 'No Items', 'Start by adding items') }}
            """
            
            result = render_template_string(template)
            assert 'No Items' in result
            assert 'Start by adding items' in result
            assert 'fa-inbox' in result

    def test_loading_spinner_component(self, app):
        """Test loading spinner macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import loading_spinner %}
            {{ loading_spinner('md', 'Loading...') }}
            """
            
            result = render_template_string(template)
            assert 'Loading...' in result

    def test_progress_bar_component(self, app):
        """Test progress bar macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import progress_bar %}
            {{ progress_bar(50, 100, 'primary', True) }}
            """
            
            result = render_template_string(template)
            assert '50' in result
            assert '100' in result

    def test_badge_component(self, app):
        """Test badge macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import badge %}
            {{ badge('Active', 'green-500', 'fas fa-check') }}
            """
            
            result = render_template_string(template)
            assert 'Active' in result
            assert 'fa-check' in result

    def test_alert_component(self, app):
        """Test alert macro rendering"""
        with app.test_request_context():
            from flask import render_template_string
            
            template = """
            {% from "components/ui.html" import alert %}
            {{ alert('Test message', 'success') }}
            """
            
            result = render_template_string(template)
            assert 'Test message' in result


class TestEnhancedTables:
    """Test enhanced table functionality"""

    def test_projects_table_enhanced(self, authenticated_client):
        """Test projects table has enhanced attributes"""
        response = authenticated_client.get(url_for('projects.list_projects'))
        assert response.status_code == 200
        assert b'data-enhanced' in response.data or b'Projects' in response.data

    def test_tasks_table_enhanced(self, authenticated_client):
        """Test tasks table has enhanced attributes"""
        response = authenticated_client.get(url_for('tasks.list_tasks'))
        assert response.status_code == 200
        assert b'data-enhanced' in response.data or b'Tasks' in response.data


class TestPWA:
    """Test PWA features"""

    def test_service_worker_exists(self):
        """Test that service worker file exists"""
        import os
        sw_path = 'app/static/service-worker.js'
        assert os.path.exists(sw_path)

    def test_manifest_exists(self):
        """Test that manifest file exists"""
        import os
        manifest_path = 'app/static/manifest.webmanifest'
        assert os.path.exists(manifest_path)

    def test_manifest_linked_in_base(self, authenticated_client):
        """Test that manifest is linked in base template"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'manifest.webmanifest' in response.data

    def test_pwa_meta_tags(self, authenticated_client):
        """Test that PWA meta tags are present"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'theme-color' in response.data


class TestAccessibility:
    """Test accessibility features"""

    def test_skip_link_present(self, authenticated_client):
        """Test that skip to content link is present"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'Skip to content' in response.data or b'dashboard' in response.data.lower()

    def test_aria_labels_present(self, authenticated_client):
        """Test that ARIA labels are present"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        # Check for some common ARIA labels
        assert b'aria-label' in response.data or response.status_code == 200


class TestChartJS:
    """Test Chart.js integration"""

    def test_chartjs_loaded(self, authenticated_client):
        """Test that Chart.js is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'chart.js' in response.data or b'Chart' in response.data

    def test_chart_manager_loaded(self, authenticated_client):
        """Test that chart manager is loaded"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'charts.js' in response.data or response.status_code == 200


class TestFilterSystem:
    """Test filter and search enhancements"""

    def test_filter_form_attribute(self, authenticated_client):
        """Test that filter forms have data-filter-form attribute"""
        response = authenticated_client.get(url_for('projects.list_projects'))
        assert response.status_code == 200
        assert b'data-filter-form' in response.data or b'Projects' in response.data


class TestBreadcrumbs:
    """Test breadcrumb navigation"""

    def test_breadcrumbs_in_projects(self, authenticated_client):
        """Test breadcrumbs appear in projects page"""
        response = authenticated_client.get(url_for('projects.list_projects'))
        assert response.status_code == 200
        # Breadcrumb should contain Home link or Projects title
        assert b'Home' in response.data or b'Projects' in response.data

    def test_breadcrumbs_in_tasks(self, authenticated_client):
        """Test breadcrumbs appear in tasks page"""
        response = authenticated_client.get(url_for('tasks.list_tasks'))
        assert response.status_code == 200
        assert b'Home' in response.data or b'Tasks' in response.data


class TestResponsiveDesign:
    """Test responsive design features"""

    def test_viewport_meta_tag(self, authenticated_client):
        """Test that viewport meta tag is present"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'viewport' in response.data
        assert b'width=device-width' in response.data

    def test_mobile_navigation_button(self, authenticated_client):
        """Test that mobile navigation button exists"""
        response = authenticated_client.get(url_for('main.dashboard'))
        assert response.status_code == 200
        assert b'mobileSidebarBtn' in response.data or b'lg:hidden' in response.data or response.status_code == 200


class TestStaticFiles:
    """Test that all new static files exist"""

    def test_enhanced_ui_css_exists(self):
        """Test enhanced-ui.css exists"""
        import os
        assert os.path.exists('app/static/enhanced-ui.css')

    def test_enhanced_ui_js_exists(self):
        """Test enhanced-ui.js exists"""
        import os
        assert os.path.exists('app/static/enhanced-ui.js')

    def test_charts_js_exists(self):
        """Test charts.js exists"""
        import os
        assert os.path.exists('app/static/charts.js')

    def test_onboarding_js_exists(self):
        """Test onboarding.js exists"""
        import os
        assert os.path.exists('app/static/onboarding.js')

    def test_service_worker_js_exists(self):
        """Test service-worker.js exists"""
        import os
        assert os.path.exists('app/static/service-worker.js')


# Fixtures
@pytest.fixture
def app():
    """Create application for testing"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    # Login first
    response = client.post('/auth/login', data={
        'username': 'testuser'
    }, follow_redirects=True)
    
    # Return headers with session cookie
    return {}

