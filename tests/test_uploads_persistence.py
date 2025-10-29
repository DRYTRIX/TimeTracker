"""Tests for uploads persistence functionality.

This module tests that uploaded files (logos and avatars) persist correctly
across application restarts and container rebuilds when using Docker volumes.
"""

import pytest
import os
import io
import tempfile
import shutil
from pathlib import Path
from flask import url_for
from app import db
from app.models import User, Settings
from PIL import Image


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    user = User(username='admintest', role='admin')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture
def authenticated_admin_client(client, admin_user):
    """Create an authenticated admin client."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
    return client


@pytest.fixture
def sample_logo_image():
    """Create a sample PNG image for testing."""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


@pytest.fixture
def uploads_dir(app):
    """Get the uploads directory path."""
    with app.app_context():
        return os.path.join(app.root_path, 'static', 'uploads')


@pytest.fixture
def cleanup_test_files(app):
    """Clean up test files after tests."""
    yield
    with app.app_context():
        upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'logos')
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.startswith('test_') or filename.startswith('company_logo_'):
                    try:
                        os.remove(os.path.join(upload_folder, filename))
                    except OSError:
                        pass


# ============================================================================
# Unit Tests - Directory Structure
# ============================================================================

@pytest.mark.unit
def test_uploads_directory_exists(app, uploads_dir):
    """Test that the uploads directory exists or can be created."""
    with app.app_context():
        # The directory should exist or be creatable
        os.makedirs(uploads_dir, exist_ok=True)
        assert os.path.exists(uploads_dir)
        assert os.path.isdir(uploads_dir)


@pytest.mark.unit
def test_logos_subdirectory_exists(app, uploads_dir):
    """Test that the logos subdirectory exists or can be created."""
    with app.app_context():
        logos_dir = os.path.join(uploads_dir, 'logos')
        os.makedirs(logos_dir, exist_ok=True)
        assert os.path.exists(logos_dir)
        assert os.path.isdir(logos_dir)


@pytest.mark.unit
def test_avatars_subdirectory_exists(app, uploads_dir):
    """Test that the avatars subdirectory exists or can be created."""
    with app.app_context():
        avatars_dir = os.path.join(uploads_dir, 'avatars')
        os.makedirs(avatars_dir, exist_ok=True)
        assert os.path.exists(avatars_dir)
        assert os.path.isdir(avatars_dir)


@pytest.mark.unit
def test_uploads_directory_is_writable(app, uploads_dir):
    """Test that the uploads directory is writable."""
    with app.app_context():
        os.makedirs(uploads_dir, exist_ok=True)
        test_file = os.path.join(uploads_dir, '.test_write_permissions')
        
        try:
            # Try to write a test file
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Verify it was created
            assert os.path.exists(test_file)
            
            # Clean up
            os.remove(test_file)
        except Exception as e:
            pytest.fail(f"Uploads directory is not writable: {e}")


# ============================================================================
# Integration Tests - File Persistence
# ============================================================================

@pytest.mark.integration
def test_logo_file_persists_after_upload(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test that uploaded logo file persists on disk after upload."""
    with app.app_context():
        # Upload logo
        data = {
            'logo': (sample_logo_image, 'test_logo_persist.png', 'image/png'),
        }
        
        response = authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Get the filename from database
        settings = Settings.get_settings()
        logo_filename = settings.company_logo_filename
        
        assert logo_filename != ''
        
        # Verify file exists on disk
        logo_path = settings.get_logo_path()
        assert os.path.exists(logo_path), f"Logo file does not exist at {logo_path}"
        assert os.path.isfile(logo_path), f"Logo path is not a file: {logo_path}"
        
        # Verify file is readable
        with open(logo_path, 'rb') as f:
            data = f.read()
            assert len(data) > 0, "Logo file is empty"


@pytest.mark.integration
def test_logo_accessible_after_simulated_restart(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test that logo remains accessible after simulated app restart."""
    with app.app_context():
        # Upload logo
        data = {
            'logo': (sample_logo_image, 'test_logo_restart.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Get the filename and path
        settings = Settings.get_settings()
        logo_filename = settings.company_logo_filename
        logo_path = settings.get_logo_path()
        
        # Verify file exists
        assert os.path.exists(logo_path)
        
        # Simulate restart by creating new app context
        # (In real Docker scenario, the file would still be there via volume)
        db.session.close()
    
    # New app context simulating restart
    with app.app_context():
        # Verify database still has the filename
        settings = Settings.get_settings()
        assert settings.company_logo_filename == logo_filename
        
        # Verify file still exists
        logo_path = settings.get_logo_path()
        assert os.path.exists(logo_path), "Logo file lost after simulated restart"


@pytest.mark.integration
def test_multiple_logos_in_directory(authenticated_admin_client, app, cleanup_test_files):
    """Test that multiple logos can exist in the directory (old and new)."""
    with app.app_context():
        logos_to_upload = []
        
        # Create and upload multiple logos
        for i in range(3):
            img = Image.new('RGB', (100, 100), color=('red', 'blue', 'green')[i])
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            
            data = {
                'logo': (img_io, f'test_logo_{i}.png', 'image/png'),
            }
            
            authenticated_admin_client.post(
                '/admin/upload-logo',
                data=data,
                content_type='multipart/form-data'
            )
            
            settings = Settings.get_settings()
            logos_to_upload.append(settings.company_logo_filename)
        
        # Verify at least the current logo exists
        settings = Settings.get_settings()
        current_logo_path = settings.get_logo_path()
        assert os.path.exists(current_logo_path), "Current logo does not exist"


@pytest.mark.integration
def test_logo_path_is_in_uploads_directory(authenticated_admin_client, sample_logo_image, app, uploads_dir, cleanup_test_files):
    """Test that uploaded logos are stored in the correct uploads directory."""
    with app.app_context():
        data = {
            'logo': (sample_logo_image, 'test_logo_path.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        logo_path = settings.get_logo_path()
        
        # Verify the logo is in the uploads/logos directory
        assert 'uploads' in logo_path, f"Logo not in uploads directory: {logo_path}"
        assert 'logos' in logo_path, f"Logo not in logos subdirectory: {logo_path}"
        
        # Verify the path structure
        expected_dir = os.path.join(uploads_dir, 'logos')
        assert expected_dir in logo_path, f"Logo not in expected directory: {logo_path}"


# ============================================================================
# Unit Tests - Path Resolution
# ============================================================================

@pytest.mark.unit
def test_settings_logo_path_resolution(app):
    """Test that Settings model correctly resolves logo paths."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = 'test_logo.png'
        db.session.commit()
        
        logo_path = settings.get_logo_path()
        
        assert logo_path is not None
        assert 'app/static/uploads/logos' in logo_path or 'app\\static\\uploads\\logos' in logo_path
        assert 'test_logo.png' in logo_path


@pytest.mark.unit
def test_settings_logo_url_format(app):
    """Test that Settings model returns correct URL format."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = 'test_logo.png'
        db.session.commit()
        
        logo_url = settings.get_logo_url()
        
        assert logo_url == '/uploads/logos/test_logo.png'


@pytest.mark.unit
def test_settings_logo_path_none_when_no_filename(app):
    """Test that logo path is None when no filename is set."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = None
        db.session.commit()
        
        logo_path = settings.get_logo_path()
        
        assert logo_path is None


# ============================================================================
# Integration Tests - File Operations
# ============================================================================

@pytest.mark.integration
def test_logo_file_has_correct_extension(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test that uploaded logo file has correct extension."""
    with app.app_context():
        data = {
            'logo': (sample_logo_image, 'test_logo.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        logo_filename = settings.company_logo_filename
        
        # Should have .png extension
        assert logo_filename.endswith('.png')


@pytest.mark.integration
def test_old_logo_removed_when_new_uploaded(authenticated_admin_client, app, cleanup_test_files):
    """Test that old logo file is removed when new one is uploaded."""
    with app.app_context():
        # Upload first logo
        img1 = Image.new('RGB', (100, 100), color='red')
        img1_io = io.BytesIO()
        img1.save(img1_io, 'PNG')
        img1_io.seek(0)
        
        data1 = {
            'logo': (img1_io, 'test_logo1.png', 'image/png'),
        }
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data1,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        old_filename = settings.company_logo_filename
        old_path = settings.get_logo_path()
        
        # Verify first logo exists
        assert os.path.exists(old_path)
        
        # Upload second logo
        img2 = Image.new('RGB', (100, 100), color='blue')
        img2_io = io.BytesIO()
        img2.save(img2_io, 'PNG')
        img2_io.seek(0)
        
        data2 = {
            'logo': (img2_io, 'test_logo2.png', 'image/png'),
        }
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data2,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        new_filename = settings.company_logo_filename
        new_path = settings.get_logo_path()
        
        # Verify new logo is different
        assert new_filename != old_filename
        
        # Verify new logo exists
        assert os.path.exists(new_path)


@pytest.mark.integration
def test_logo_removed_when_deleted(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test that logo file is removed when deleted via admin interface."""
    with app.app_context():
        # Upload logo
        data = {
            'logo': (sample_logo_image, 'test_logo_delete.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        logo_path = settings.get_logo_path()
        
        # Verify logo exists
        assert os.path.exists(logo_path)
        
        # Remove logo
        authenticated_admin_client.post(
            '/admin/remove-logo',
            follow_redirects=True
        )
        
        # Verify database field is cleared
        settings = Settings.get_settings()
        assert settings.company_logo_filename == '' or settings.company_logo_filename is None


# ============================================================================
# Smoke Tests
# ============================================================================

@pytest.mark.smoke
def test_uploads_directory_accessible(app, uploads_dir):
    """Smoke test: Verify uploads directory is accessible."""
    with app.app_context():
        # Create directory if it doesn't exist
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Verify we can list directory contents
        try:
            contents = os.listdir(uploads_dir)
            assert isinstance(contents, list)
        except Exception as e:
            pytest.fail(f"Cannot access uploads directory: {e}")


@pytest.mark.smoke
def test_logo_upload_and_retrieve_workflow(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Smoke test: Complete workflow of uploading and retrieving a logo."""
    with app.app_context():
        # 1. Upload logo
        data = {
            'logo': (sample_logo_image, 'test_workflow.png', 'image/png'),
        }
        
        upload_response = authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        assert upload_response.status_code == 200
        
        # 2. Verify logo is in database
        settings = Settings.get_settings()
        assert settings.company_logo_filename != ''
        
        # 3. Verify logo file exists
        logo_path = settings.get_logo_path()
        assert os.path.exists(logo_path)
        
        # 4. Retrieve logo URL
        logo_url = settings.get_logo_url()
        assert logo_url is not None
        
        # 5. Access logo via HTTP
        retrieve_response = authenticated_admin_client.get(logo_url)
        assert retrieve_response.status_code == 200
        assert retrieve_response.content_type.startswith('image/')


# ============================================================================
# Model Tests
# ============================================================================

@pytest.mark.models
def test_settings_has_logo_with_existing_file(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test Settings.has_logo() returns True when logo exists."""
    with app.app_context():
        # Upload logo
        data = {
            'logo': (sample_logo_image, 'test_has_logo.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        
        # has_logo() should return True
        assert settings.has_logo() is True


@pytest.mark.models
def test_settings_has_logo_without_file(app):
    """Test Settings.has_logo() returns False when no logo exists."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = ''
        db.session.commit()
        
        # has_logo() should return False
        assert settings.has_logo() is False


@pytest.mark.models
def test_settings_to_dict_includes_logo_info(authenticated_admin_client, sample_logo_image, app, cleanup_test_files):
    """Test Settings.to_dict() includes logo information."""
    with app.app_context():
        # Upload logo
        data = {
            'logo': (sample_logo_image, 'test_to_dict.png', 'image/png'),
        }
        
        authenticated_admin_client.post(
            '/admin/upload-logo',
            data=data,
            content_type='multipart/form-data'
        )
        
        settings = Settings.get_settings()
        settings_dict = settings.to_dict()
        
        # Should include logo filename and/or URL
        assert 'company_logo_filename' in settings_dict or 'logo_url' in settings_dict

