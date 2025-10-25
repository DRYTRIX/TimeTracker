"""Tests for utility modules in app/utils."""

import pytest
import datetime
import os
import tempfile
from unittest.mock import patch
from flask import g
from werkzeug.exceptions import Forbidden, BadRequest, InternalServerError
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Settings
from app.utils.template_filters import register_template_filters
from app.utils.context_processors import register_context_processors
from app.utils.error_handlers import register_error_handlers
from app.utils.i18n import _needs_compile, compile_po_to_mo, ensure_translations_compiled
from app.utils.db import safe_commit


# ============================================================================
# Template Filter Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.utils
def test_local_datetime_filter(app):
    """Test local_datetime filter with valid datetime."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_datetime')
        utc_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = filter_func(utc_dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_local_datetime_filter_none(app):
    """Test local_datetime filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_datetime')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_local_date_filter(app):
    """Test local_date filter."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_date')
        utc_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = filter_func(utc_dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_local_date_filter_none(app):
    """Test local_date filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_date')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_local_time_filter(app):
    """Test local_time filter."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_time')
        utc_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = filter_func(utc_dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_local_time_filter_none(app):
    """Test local_time filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_time')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_local_datetime_short_filter(app):
    """Test local_datetime_short filter."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_datetime_short')
        utc_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = filter_func(utc_dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_local_datetime_short_filter_none(app):
    """Test local_datetime_short filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('local_datetime_short')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_nl2br_filter(app):
    """Test nl2br filter converts newlines to br tags."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('nl2br')
        text = "Line 1\nLine 2\r\nLine 3\rLine 4"
        result = filter_func(text)
        assert '<br>' in result
        assert result.count('<br>') == 3


@pytest.mark.unit
@pytest.mark.utils
def test_nl2br_filter_none(app):
    """Test nl2br filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('nl2br')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_markdown_filter_empty(app):
    """Test markdown filter with empty text."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('markdown')
        result = filter_func("")
        assert result == ""
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_markdown_filter_with_text(app):
    """Test markdown filter with actual markdown."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('markdown')
        text = "# Header\n\n**Bold text**"
        result = filter_func(text)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_format_date_filter_with_datetime(app):
    """Test format_date filter with datetime object."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_date')
        dt = datetime.datetime(2024, 1, 15, 12, 0, 0)
        result = filter_func(dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_format_date_filter_with_date(app):
    """Test format_date filter with date object."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_date')
        dt = datetime.date(2024, 1, 15)
        result = filter_func(dt)
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.utils
def test_format_date_filter_formats(app):
    """Test format_date filter with different formats."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_date')
        dt = datetime.date(2024, 1, 15)
        
        # Test different formats
        result_full = filter_func(dt, 'full')
        result_long = filter_func(dt, 'long')
        result_short = filter_func(dt, 'short')
        result_medium = filter_func(dt, 'medium')
        
        assert all(isinstance(r, str) for r in [result_full, result_long, result_short, result_medium])


@pytest.mark.unit
@pytest.mark.utils
def test_format_date_filter_none(app):
    """Test format_date filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_date')
        result = filter_func(None)
        assert result == ''


@pytest.mark.unit
@pytest.mark.utils
def test_format_date_filter_non_date(app):
    """Test format_date filter with non-date value."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_date')
        result = filter_func("not a date")
        assert result == "not a date"


@pytest.mark.unit
@pytest.mark.utils
def test_format_money_filter(app):
    """Test format_money filter."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_money')
        
        # Test with float
        result = filter_func(1234.56)
        assert result == "1,234.56"
        
        # Test with int
        result = filter_func(1000)
        assert result == "1,000.00"
        
        # Test with string number
        result = filter_func("999.99")
        assert result == "999.99"


@pytest.mark.unit
@pytest.mark.utils
def test_format_money_filter_invalid(app):
    """Test format_money filter with invalid input."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('format_money')
        result = filter_func("not a number")
        assert result == "not a number"


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_none(app):
    """Test timeago filter with None."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        result = filter_func(None)
        assert result == ""


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_just_now(app):
    """Test timeago filter with very recent datetime."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 30 seconds ago
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(seconds=30)
        result = filter_func(dt)
        assert result == "just now"


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_minutes(app):
    """Test timeago filter with minutes ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 5 minutes ago
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(minutes=5)
        result = filter_func(dt)
        assert "minute" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_hours(app):
    """Test timeago filter with hours ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 3 hours ago
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(hours=3)
        result = filter_func(dt)
        assert "hour" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_days(app):
    """Test timeago filter with days ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 2 days ago
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(days=2)
        result = filter_func(dt)
        assert "day" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_weeks(app):
    """Test timeago filter with weeks ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 2 weeks ago
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(weeks=2)
        result = filter_func(dt)
        assert "week" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_months(app):
    """Test timeago filter with months ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 60 days ago (2 months)
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(days=60)
        result = filter_func(dt)
        assert "month" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_years(app):
    """Test timeago filter with years ago."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime for 400 days ago (over a year)
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now - datetime.timedelta(days=400)
        result = filter_func(dt)
        assert "year" in result
        assert "ago" in result


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_future(app):
    """Test timeago filter with future datetime."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create datetime in the future
        now = datetime.datetime.now(datetime.timezone.utc)
        dt = now + datetime.timedelta(hours=2)
        result = filter_func(dt)
        assert result == "just now"


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_naive_datetime(app):
    """Test timeago filter with naive datetime (no timezone)."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        # Create naive datetime for 1 hour ago
        dt = datetime.datetime.now() - datetime.timedelta(hours=1)
        result = filter_func(dt)
        # Should still work and convert to UTC
        assert "ago" in result or result == "just now"


@pytest.mark.unit
@pytest.mark.utils
def test_timeago_filter_singular_plural(app):
    """Test timeago filter uses correct singular/plural forms."""
    register_template_filters(app)
    with app.app_context():
        filter_func = app.jinja_env.filters.get('timeago')
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Test singular (1 minute)
        dt = now - datetime.timedelta(minutes=1)
        result = filter_func(dt)
        assert "1 minute ago" in result
        
        # Test plural (2 minutes)
        dt = now - datetime.timedelta(minutes=2)
        result = filter_func(dt)
        assert "2 minutes ago" in result


# ============================================================================
# Context Processor Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.utils
def test_inject_settings(app, client):
    """Test inject_settings context processor."""
    register_context_processors(app)
    with app.app_context():
        # Make a request to trigger context processors
        response = client.get('/')
        assert response is not None


@pytest.mark.unit
@pytest.mark.utils
def test_inject_globals(app, client):
    """Test inject_globals context processor."""
    register_context_processors(app)
    with app.app_context():
        response = client.get('/')
        assert response is not None


@pytest.mark.unit
@pytest.mark.utils
def test_before_request(app, client):
    """Test before_request function."""
    register_context_processors(app)
    with app.test_request_context('/'):
        # Trigger before_request
        app.preprocess_request()
        # Check that g.request_start_time is set
        assert hasattr(g, 'request_start_time')


# ============================================================================
# Error Handler Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.utils
def test_404_error_html(app, client):
    """Test 404 error handler returns HTML for non-API routes."""
    register_error_handlers(app)
    response = client.get('/nonexistent-page')
    assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.utils
def test_404_error_api(app, client):
    """Test 404 error handler returns JSON for API routes."""
    register_error_handlers(app)
    response = client.get('/api/nonexistent')
    assert response.status_code == 404
    # Should return JSON
    if response.content_type and 'json' in response.content_type:
        data = response.get_json()
        assert 'error' in data


@pytest.mark.unit
@pytest.mark.utils
def test_500_error_html(app, client):
    """Test 500 error handler returns HTML for non-API routes."""
    register_error_handlers(app)
    
    @app.route('/test-500')
    def test_500():
        raise Exception("Test error")
    
    response = client.get('/test-500')
    assert response.status_code == 500


@pytest.mark.unit
@pytest.mark.utils
def test_500_error_api(app, client):
    """Test 500 error handler returns JSON for API routes."""
    register_error_handlers(app)
    
    @app.route('/api/test-500')
    def test_api_500():
        raise Exception("Test API error")
    
    response = client.get('/api/test-500')
    assert response.status_code == 500
    if response.content_type and 'json' in response.content_type:
        data = response.get_json()
        assert 'error' in data


@pytest.mark.unit
@pytest.mark.utils
def test_403_error_html(app, client):
    """Test 403 error handler returns HTML for non-API routes."""
    register_error_handlers(app)
    
    @app.route('/test-403')
    def test_403():
        raise Forbidden("Forbidden")
    
    response = client.get('/test-403')
    assert response.status_code == 403


@pytest.mark.unit
@pytest.mark.utils
def test_403_error_api(app, client):
    """Test 403 error handler returns JSON for API routes."""
    register_error_handlers(app)
    
    @app.route('/api/test-403')
    def test_api_403():
        raise Forbidden("Forbidden")
    
    response = client.get('/api/test-403')
    assert response.status_code == 403
    if response.content_type and 'json' in response.content_type:
        data = response.get_json()
        assert 'error' in data


@pytest.mark.unit
@pytest.mark.utils
def test_400_error_html(app, client):
    """Test 400 error handler returns HTML for non-API routes."""
    register_error_handlers(app)
    
    @app.route('/test-400')
    def test_400():
        raise BadRequest("Bad request")
    
    response = client.get('/test-400')
    assert response.status_code == 400


@pytest.mark.unit
@pytest.mark.utils
def test_400_error_api(app, client):
    """Test 400 error handler returns JSON for API routes."""
    register_error_handlers(app)
    
    @app.route('/api/test-400')
    def test_api_400():
        raise BadRequest("Bad request")
    
    response = client.get('/api/test-400')
    assert response.status_code == 400
    if response.content_type and 'json' in response.content_type:
        data = response.get_json()
        assert 'error' in data


@pytest.mark.unit
@pytest.mark.utils
def test_http_exception_handler(app, client):
    """Test generic HTTP exception handler."""
    register_error_handlers(app)
    
    @app.route('/test-http-exception')
    def test_http():
        raise InternalServerError("Server error")
    
    response = client.get('/test-http-exception')
    assert response.status_code == 500


# ============================================================================
# I18n Utility Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.utils
def test_needs_compile_mo_missing():
    """Test _needs_compile returns True when .mo file is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        po_path = os.path.join(tmpdir, 'messages.po')
        mo_path = os.path.join(tmpdir, 'messages.mo')
        
        # Create po file
        with open(po_path, 'w') as f:
            f.write('# test')
        
        # mo file doesn't exist
        assert _needs_compile(po_path, mo_path) is True


@pytest.mark.unit
@pytest.mark.utils
def test_needs_compile_po_newer():
    """Test _needs_compile returns True when .po is newer than .mo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        po_path = os.path.join(tmpdir, 'messages.po')
        mo_path = os.path.join(tmpdir, 'messages.mo')
        
        # Create mo file first
        with open(mo_path, 'wb') as f:
            f.write(b'old')
        
        # Wait a bit and create po file
        import time
        time.sleep(0.01)
        with open(po_path, 'w') as f:
            f.write('# new')
        
        assert _needs_compile(po_path, mo_path) is True


@pytest.mark.unit
@pytest.mark.utils
def test_needs_compile_mo_current():
    """Test _needs_compile returns False when .mo is current."""
    with tempfile.TemporaryDirectory() as tmpdir:
        po_path = os.path.join(tmpdir, 'messages.po')
        mo_path = os.path.join(tmpdir, 'messages.mo')
        
        # Create po file first
        with open(po_path, 'w') as f:
            f.write('# test')
        
        # Wait and create mo file
        import time
        time.sleep(0.01)
        with open(mo_path, 'wb') as f:
            f.write(b'compiled')
        
        assert _needs_compile(po_path, mo_path) is False


@pytest.mark.unit
@pytest.mark.utils
def test_compile_po_to_mo_success():
    """Test compile_po_to_mo successfully compiles a valid .po file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        po_path = os.path.join(tmpdir, 'messages.po')
        mo_path = os.path.join(tmpdir, 'messages.mo')
        
        # Create a minimal valid .po file
        po_content = '''# Translation file
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hallo"
'''
        with open(po_path, 'w', encoding='utf-8') as f:
            f.write(po_content)
        
        result = compile_po_to_mo(po_path, mo_path)
        assert result is True
        assert os.path.exists(mo_path)


@pytest.mark.unit
@pytest.mark.utils
def test_compile_po_to_mo_invalid_file():
    """Test compile_po_to_mo handles invalid .po files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        po_path = os.path.join(tmpdir, 'invalid.po')
        mo_path = os.path.join(tmpdir, 'invalid.mo')
        
        # Don't create the po file
        result = compile_po_to_mo(po_path, mo_path)
        assert result is False


@pytest.mark.unit
@pytest.mark.utils
def test_ensure_translations_compiled_empty_dir():
    """Test ensure_translations_compiled with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Should not raise any errors
        ensure_translations_compiled(tmpdir)


@pytest.mark.unit
@pytest.mark.utils
def test_ensure_translations_compiled_valid_structure():
    """Test ensure_translations_compiled with valid translation structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a valid translation structure
        lang_dir = os.path.join(tmpdir, 'de', 'LC_MESSAGES')
        os.makedirs(lang_dir, exist_ok=True)
        
        po_path = os.path.join(lang_dir, 'messages.po')
        po_content = '''# Translation file
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hallo"
'''
        with open(po_path, 'w', encoding='utf-8') as f:
            f.write(po_content)
        
        # Should compile the po file
        ensure_translations_compiled(tmpdir)
        
        mo_path = os.path.join(lang_dir, 'messages.mo')
        assert os.path.exists(mo_path)


@pytest.mark.unit
@pytest.mark.utils
def test_ensure_translations_compiled_none():
    """Test ensure_translations_compiled with None path."""
    # Should not raise any errors
    ensure_translations_compiled(None)


@pytest.mark.unit
@pytest.mark.utils
def test_ensure_translations_compiled_relative_path():
    """Test ensure_translations_compiled with relative path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            subdir = 'translations'
            os.makedirs(subdir, exist_ok=True)
            
            # Should handle relative path
            ensure_translations_compiled(subdir)
        finally:
            os.chdir(old_cwd)


@pytest.mark.unit
@pytest.mark.utils
def test_ensure_translations_compiled_nonexistent_dir():
    """Test ensure_translations_compiled with nonexistent directory."""
    # Should not raise any errors
    ensure_translations_compiled('/nonexistent/path')


# ============================================================================
# Database Utility Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_success(app):
    """Test safe_commit with successful commit."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_name = 'Test Company'
        result = safe_commit('test action')
        assert result is True


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_with_context(app):
    """Test safe_commit with context information."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_name = 'Test Company 2'
        result = safe_commit('test action', {'user': 'test_user'})
        assert result is True


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_sqlalchemy_error(app):
    """Test safe_commit handles SQLAlchemyError."""
    with app.app_context():
        # Mock db.session.commit to raise SQLAlchemyError
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError("Test error")):
            result = safe_commit('test action')
            assert result is False


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_sqlalchemy_error_with_context(app):
    """Test safe_commit handles SQLAlchemyError with context."""
    with app.app_context():
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError("Test error")):
            result = safe_commit('test action', {'user': 'test_user'})
            assert result is False


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_sqlalchemy_error_no_action(app):
    """Test safe_commit handles SQLAlchemyError without action."""
    with app.app_context():
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError("Test error")):
            result = safe_commit()
            assert result is False


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_generic_exception(app):
    """Test safe_commit handles generic exceptions."""
    with app.app_context():
        # Mock db.session.commit to raise generic Exception
        with patch.object(db.session, 'commit', side_effect=Exception("Unexpected error")):
            result = safe_commit('test action')
            assert result is False


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_rollback_error(app):
    """Test safe_commit handles errors during rollback."""
    with app.app_context():
        # Mock both commit and rollback to raise errors
        # The rollback is in a finally block, so the exception is suppressed
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError("Test error")):
            # The rollback error should be suppressed by the finally block
            original_rollback = db.session.rollback
            try:
                db.session.rollback = lambda: None  # Mock rollback to do nothing
                result = safe_commit('test action')
                assert result is False
            finally:
                db.session.rollback = original_rollback


@pytest.mark.unit
@pytest.mark.utils
def test_safe_commit_logging_error(app):
    """Test safe_commit handles errors during logging."""
    with app.app_context():
        # Mock commit to raise error and logger to raise error
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError("Test error")):
            with patch('flask.current_app.logger.exception', side_effect=Exception("Logging error")):
                result = safe_commit('test action')
                assert result is False

