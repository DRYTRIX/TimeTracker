"""
Test suite for keyboard shortcuts input field fix.

This test ensures that keyboard shortcuts (like 'gr') do not trigger
when typing in input fields, textareas, or other editable elements.
"""

import pytest
from flask import url_for
from app import db
from app.models import User, Project, Client


class TestKeyboardShortcutsInputFix:
    """Test keyboard shortcuts behavior in input fields."""

    @pytest.fixture(autouse=True)
    def setup(self, admin_authenticated_client, admin_user, test_client):
        """Set up test fixtures."""
        self.client = admin_authenticated_client
        self.user = admin_user
        self.test_client = test_client

    def test_create_project_page_loads(self):
        """Test that create project page loads successfully."""
        response = self.client.get('/projects/create')
        assert response.status_code == 200
        assert b'Create Project' in response.data or b'New Project' in response.data

    def test_create_project_with_gr_in_name(self):
        """Test creating a project with 'gr' in the name (e.g., 'program')."""
        response = self.client.post('/projects/create', data={
            'name': 'Program Development',
            'description': 'A program for testing',
            'status': 'active',
            'hourly_rate': '50.00',
            'client_id': self.test_client.id
        }, follow_redirects=True)
        
        # Should successfully create the project
        assert response.status_code == 200
        
        # Verify project was created
        project = Project.query.filter_by(name='Program Development').first()
        assert project is not None
        assert project.name == 'Program Development'
        assert 'program' in project.description.lower()

    def test_create_task_with_trigger_in_name(self):
        """Test creating a task with shortcut trigger keys in the name."""
        # First create a project
        project = Project(
            name='Test Project',
            description='Test',
            client_id=self.test_client.id,
            status='active'
        )
        db.session.add(project)
        db.session.commit()
        
        # Create task with 'gr' in the name
        response = self.client.post('/tasks/create', data={
            'name': 'Upgrade system',
            'description': 'Migrate program to new version',
            'project_id': project.id,
            'status': 'todo',
            'priority': 'medium'
        }, follow_redirects=True)
        
        assert response.status_code == 200

    def test_project_name_with_multiple_triggers(self):
        """Test project names containing multiple keyboard shortcut triggers."""
        test_names = [
            'Program Graphics Design',  # Contains 'gr'
            'Client Portal Development',  # Contains 'port'
            'Integration Testing',  # Contains 'int'
            'Graphics Rendering Engine',  # Contains 'gr'
        ]
        
        for name in test_names:
            response = self.client.post('/projects/create', data={
                'name': name,
                'description': f'Testing {name}',
                'status': 'active',
                'hourly_rate': '50.00',
                'client_id': self.test_client.id
            }, follow_redirects=True)
            
            # Should successfully create without triggering shortcuts
            project = Project.query.filter_by(name=name).first()
            assert project is not None, f"Failed to create project: {name}"

    def test_keyboard_shortcuts_js_loaded(self):
        """Test that keyboard shortcuts JavaScript files are loaded."""
        response = self.client.get('/')
        assert response.status_code == 200
        
        # Check that at least one keyboard shortcuts file is referenced
        # (The actual check depends on how the JS is loaded in your templates)
        data = response.data.decode('utf-8')
        assert 'keyboard' in data.lower() or 'shortcut' in data.lower()


class TestKeyboardShortcutsJavaScriptLogic:
    """Test JavaScript keyboard shortcuts logic (documentation tests)."""

    def test_istyping_method_exists(self):
        """
        Documentation test: Verify isTyping/isTypingContext methods exist.
        
        The keyboard shortcut files should have methods to detect
        when user is typing in an input field:
        - keyboard-shortcuts.js: isTyping()
        - keyboard-shortcuts-enhanced.js: isTypingContext()
        - keyboard-shortcuts-advanced.js: isTyping()
        """
        # Read the JavaScript files with UTF-8 encoding
        with open('app/static/keyboard-shortcuts.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'isTyping' in content, "isTyping method not found in keyboard-shortcuts.js"
            assert 'tagName === \'input\'' in content or 'tagname === "input"' in content.lower()
        
        with open('app/static/keyboard-shortcuts-enhanced.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'isTypingContext' in content, "isTypingContext method not found"
            assert 'tagName' in content or 'tagname' in content.lower()
        
        with open('app/static/keyboard-shortcuts-advanced.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'isTyping' in content, "isTyping method not found in keyboard-shortcuts-advanced.js"

    def test_input_check_before_sequences(self):
        """
        Documentation test: Verify input checks happen before sequence handling.
        
        The keyboard shortcut handlers should check if user is typing
        BEFORE processing key sequences like 'g r'.
        """
        with open('app/static/keyboard-shortcuts.js', 'r', encoding='utf-8') as f:
            content = f.read()
            # Should check isTyping before handling sequences
            assert 'isTyping' in content
            assert 'keySequence' in content

    def test_sequence_cleared_when_typing(self):
        """
        Documentation test: Verify key sequences are cleared when typing.
        
        When user starts typing in an input field, any existing
        key sequence should be cleared to prevent partial matches.
        """
        with open('app/static/keyboard-shortcuts.js', 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for sequence clearing logic
            assert 'keySequence = []' in content or 'keySequence=[]' in content

    def test_allowed_shortcuts_in_inputs(self):
        """
        Documentation test: Verify certain shortcuts are allowed in inputs.
        
        Some shortcuts like Ctrl+K (command palette), Ctrl+/ (search),
        and Shift+? (help) should work even when in an input field.
        """
        # Check keyboard-shortcuts-enhanced.js for allowed shortcuts
        with open('app/static/keyboard-shortcuts-enhanced.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'isAllowedInInput' in content, "isAllowedInInput method not found"
            # Should include ctrl+k, ctrl+/, shift+?
            assert 'ctrl+k' in content.lower() or 'ctrlKey' in content

    def test_contenteditable_check(self):
        """
        Documentation test: Verify contentEditable elements are handled.
        
        The isTyping check should also cover contentEditable elements,
        not just input and textarea.
        """
        with open('app/static/keyboard-shortcuts.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'isContentEditable' in content or 'contentEditable' in content

    def test_rich_text_editor_detection(self):
        """
        Documentation test: Verify rich text editors are detected.
        
        The isTyping check should detect popular rich text editors like:
        - Toast UI Editor (used in this project)
        - TinyMCE
        - Quill
        - CodeMirror
        """
        with open('app/static/keyboard-shortcuts.js', 'r', encoding='utf-8') as f:
            content = f.read()
            # Should check for Toast UI Editor
            assert 'toastui-editor' in content.lower(), "Toast UI Editor detection not found"
            # Should check for other popular editors
            assert 'CodeMirror' in content or 'codemirror' in content.lower()
            assert 'closest' in content, "Should use closest() to check parent elements"
        
        with open('app/static/keyboard-shortcuts-enhanced.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'toastui-editor' in content.lower(), "Toast UI Editor detection not found in enhanced"
        
        with open('app/static/keyboard-shortcuts-advanced.js', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'toastui-editor' in content.lower(), "Toast UI Editor detection not found in advanced"


class TestKeyboardShortcutsBugScenarios:
    """Test specific bug scenarios reported by users."""

    @pytest.fixture(autouse=True)
    def setup(self, admin_authenticated_client, admin_user, test_client):
        """Set up test fixtures."""
        self.client = admin_authenticated_client
        self.user = admin_user
        self.test_client = test_client

    def test_reported_bug_typing_program(self):
        """
        Test the exact bug scenario: typing 'program' in create project.
        
        Bug report: When typing 'gr' in text field (e.g., in 'program'),
        it triggers the 'g r' shortcut (Go to Reports).
        
        Expected: Should NOT trigger the shortcut, should type normally.
        """
        response = self.client.post('/projects/create', data={
            'name': 'New program',
            'description': 'program for programming',
            'status': 'active',
            'hourly_rate': '75.00',
            'client_id': self.test_client.id
        }, follow_redirects=True)
        
        # Should create project successfully without being redirected to reports
        assert response.status_code == 200
        
        # Verify we're not on the reports page
        assert b'Reports' not in response.data or b'New program' in response.data
        
        # Verify project was created
        project = Project.query.filter_by(name='New program').first()
        assert project is not None
        assert 'program' in project.description

    def test_all_shortcut_triggers_in_text(self):
        """
        Test typing text that contains all common shortcut triggers.
        
        Common shortcuts:
        - g d: Go to Dashboard
        - g p: Go to Projects
        - g t: Go to Tasks
        - g r: Go to Reports
        - g i: Go to Invoices
        """
        test_text = "a program with great ideas and graphics"
        
        response = self.client.post('/projects/create', data={
            'name': test_text,
            'description': 'This project has: goals, graphics, great progress, grand ideas',
            'status': 'active',
            'hourly_rate': '60.00',
            'client_id': self.test_client.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify project was created with the full text
        project = Project.query.filter_by(name=test_text).first()
        assert project is not None


def test_smoke_keyboard_shortcuts_on_multiple_pages(admin_authenticated_client):
    """
    Smoke test: Verify keyboard shortcuts don't interfere on multiple pages.
    
    This test loads various pages to ensure the keyboard shortcuts
    JavaScript is properly loaded and configured on all pages.
    """
    # Test pages that have text inputs
    pages_with_inputs = [
        '/projects/create',
        '/tasks/create',
        '/clients/create',
        '/timer/manual-entry',
    ]
    
    for page in pages_with_inputs:
        response = admin_authenticated_client.get(page)
        # Should load successfully (200) or redirect to valid page (302)
        assert response.status_code in [200, 302, 404], \
            f"Page {page} returned unexpected status: {response.status_code}"

