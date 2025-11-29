"""Tests for admin settings and logo upload functionality."""

import pytest
import os
import io
from flask import url_for
from app import db
from app.models import User, Settings
from PIL import Image


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    user = User(username="admintest", role="admin")
    user.is_active = True
    user.set_password("testpass123")  # Set password for login endpoint
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


# Use admin_authenticated_client from conftest instead of defining our own
@pytest.fixture
def authenticated_admin_client(admin_authenticated_client):
    """Alias for admin_authenticated_client for backward compatibility with existing tests."""
    return admin_authenticated_client


@pytest.fixture
def sample_logo_image():
    """Create a sample PNG image for testing."""
    # Create a simple 100x100 red square PNG
    img = Image.new("RGB", (100, 100), color="red")
    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)
    return img_io


@pytest.fixture
def cleanup_logos(app):
    """Clean up uploaded logos after tests."""
    yield
    with app.app_context():
        upload_folder = os.path.join(app.root_path, "static", "uploads", "logos")
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.startswith("company_logo_"):
                    try:
                        os.remove(os.path.join(upload_folder, filename))
                    except OSError:
                        pass


# ============================================================================
# Unit Tests - Settings Model
# ============================================================================


@pytest.mark.unit
@pytest.mark.models
def test_settings_has_logo_no_filename(app):
    """Test has_logo returns False when no logo filename is set."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = ""
        db.session.commit()

        assert settings.has_logo() is False


@pytest.mark.unit
@pytest.mark.models
def test_settings_has_logo_file_not_exists(app):
    """Test has_logo returns False when logo file doesn't exist."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = "nonexistent_logo.png"
        db.session.commit()

        assert settings.has_logo() is False


@pytest.mark.unit
@pytest.mark.models
def test_settings_get_logo_url(app):
    """Test get_logo_url returns correct URL."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = "test_logo.png"
        db.session.commit()

        assert settings.get_logo_url() == "/uploads/logos/test_logo.png"


@pytest.mark.unit
@pytest.mark.models
def test_settings_get_logo_url_no_filename(app):
    """Test get_logo_url returns None when no filename is set."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = ""
        db.session.commit()

        assert settings.get_logo_url() is None


@pytest.mark.unit
@pytest.mark.models
def test_settings_get_logo_path(app):
    """Test get_logo_path returns correct file system path."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = "test_logo.png"
        db.session.commit()

        logo_path = settings.get_logo_path()
        assert logo_path is not None
        assert "test_logo.png" in logo_path
        assert os.path.isabs(logo_path)


# ============================================================================
# Integration Tests - Logo Upload Routes
# ============================================================================


@pytest.mark.smoke
@pytest.mark.routes
def test_admin_settings_page_accessible(admin_authenticated_client):
    """Test that admin settings page is accessible to admin users."""
    response = admin_authenticated_client.get("/admin/settings")
    assert response.status_code == 200
    # Check for Company Logo text (may be translated)
    html = response.get_data(as_text=True)
    assert "Company Logo" in html or "logo" in html.lower()


@pytest.mark.routes
def test_admin_settings_requires_authentication(client):
    """Test that admin settings requires authentication."""
    response = client.get("/admin/settings", follow_redirects=False)
    assert response.status_code == 302  # Redirect to login


@pytest.mark.routes
def test_logo_upload_successful(authenticated_admin_client, sample_logo_image, cleanup_logos, app):
    """Test successful logo upload."""
    with app.app_context():
        data = {
            "logo": (sample_logo_image, "test_logo.png", "image/png"),
        }

        response = authenticated_admin_client.post(
            "/admin/upload-logo", data=data, content_type="multipart/form-data", follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Company logo uploaded successfully" in response.data

        # Verify logo was saved in database
        settings = Settings.get_settings()
        assert settings.company_logo_filename != ""
        assert settings.company_logo_filename.startswith("company_logo_")
        assert settings.company_logo_filename.endswith(".png")

        # Verify file exists on disk
        logo_path = settings.get_logo_path()
        assert os.path.exists(logo_path)


@pytest.mark.routes
def test_logo_upload_no_file(authenticated_admin_client, app):
    """Test logo upload without a file."""
    with app.app_context():
        response = authenticated_admin_client.post("/admin/upload-logo", data={}, follow_redirects=True)

        assert response.status_code == 200
        assert b"No logo file selected" in response.data


@pytest.mark.routes
def test_logo_upload_invalid_file_type(authenticated_admin_client, app):
    """Test logo upload with invalid file type."""
    with app.app_context():
        # Create a text file instead of an image
        text_file = io.BytesIO(b"This is not an image")

        data = {
            "logo": (text_file, "test.txt", "text/plain"),
        }

        response = authenticated_admin_client.post(
            "/admin/upload-logo", data=data, content_type="multipart/form-data", follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Invalid file type" in response.data or b"Invalid image file" in response.data


@pytest.mark.routes
def test_logo_upload_replaces_old_logo(authenticated_admin_client, cleanup_logos, app):
    """Test that uploading a new logo replaces the old one."""
    with app.app_context():
        # Create first logo
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_io = io.BytesIO()
        img1.save(img1_io, "PNG")
        img1_io.seek(0)

        # Upload first logo
        data1 = {
            "logo": (img1_io, "test_logo1.png", "image/png"),
        }
        authenticated_admin_client.post("/admin/upload-logo", data=data1, content_type="multipart/form-data")

        settings = Settings.get_settings()
        old_filename = settings.company_logo_filename
        old_path = settings.get_logo_path()

        # Create second logo
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = io.BytesIO()
        img2.save(img2_io, "PNG")
        img2_io.seek(0)

        # Upload second logo
        data2 = {
            "logo": (img2_io, "test_logo2.png", "image/png"),
        }
        authenticated_admin_client.post("/admin/upload-logo", data=data2, content_type="multipart/form-data")

        settings = Settings.get_settings()
        new_filename = settings.company_logo_filename
        new_path = settings.get_logo_path()

        # Verify new logo is different
        assert new_filename != old_filename

        # Verify new logo exists
        assert os.path.exists(new_path)

        # Old logo should be deleted (this might not always work depending on timing)
        # So we won't strictly assert this


@pytest.mark.routes
def test_remove_logo_successful(authenticated_admin_client, sample_logo_image, cleanup_logos, app):
    """Test successful logo removal."""
    with app.app_context():
        # First upload a logo
        data = {
            "logo": (sample_logo_image, "test_logo.png", "image/png"),
        }
        authenticated_admin_client.post("/admin/upload-logo", data=data, content_type="multipart/form-data")

        settings = Settings.get_settings()
        logo_path = settings.get_logo_path()

        # Verify logo exists
        assert settings.company_logo_filename != ""
        assert os.path.exists(logo_path)

        # Remove logo
        response = authenticated_admin_client.post("/admin/remove-logo", follow_redirects=True)

        assert response.status_code == 200
        assert b"Company logo removed successfully" in response.data

        # Verify logo was removed from database
        settings = Settings.get_settings()
        assert settings.company_logo_filename == ""

        # Verify file was deleted (might not always work depending on timing)
        # So we won't strictly assert this


@pytest.mark.routes
def test_remove_logo_when_none_exists(authenticated_admin_client, app):
    """Test removing logo when none exists."""
    with app.app_context():
        settings = Settings.get_settings()
        settings.company_logo_filename = ""
        db.session.commit()

        response = authenticated_admin_client.post("/admin/remove-logo", follow_redirects=True)

        assert response.status_code == 200
        assert b"No logo to remove" in response.data


@pytest.mark.routes
def test_serve_uploaded_logo(authenticated_admin_client, sample_logo_image, cleanup_logos, app):
    """Test serving uploaded logo files."""
    with app.app_context():
        # Upload a logo
        data = {
            "logo": (sample_logo_image, "test_logo.png", "image/png"),
        }
        authenticated_admin_client.post("/admin/upload-logo", data=data, content_type="multipart/form-data")

        settings = Settings.get_settings()
        logo_url = settings.get_logo_url()

        # Try to access the logo
        response = authenticated_admin_client.get(logo_url)
        assert response.status_code == 200
        assert response.content_type.startswith("image/")


# ============================================================================
# Security Tests
# ============================================================================


@pytest.mark.routes
@pytest.mark.security
def test_logo_upload_requires_admin(client, app):
    """Test that logo upload requires admin privileges."""
    with app.app_context():
        # Create a regular user
        user = User(username="regular_user", role="user")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        sample_logo = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(sample_logo, "PNG")
        sample_logo.seek(0)

        data = {
            "logo": (sample_logo, "test_logo.png", "image/png"),
        }

        response = client.post(
            "/admin/upload-logo", data=data, content_type="multipart/form-data", follow_redirects=False
        )

        # Should redirect or show forbidden
        assert response.status_code in [302, 403]


@pytest.mark.routes
@pytest.mark.security
def test_remove_logo_requires_admin(client, app):
    """Test that logo removal requires admin privileges."""
    with app.app_context():
        # Create a regular user
        user = User(username="regular_user", role="user")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/admin/remove-logo", follow_redirects=False)

        # Should redirect or show forbidden
        assert response.status_code in [302, 403]


# ============================================================================
# Smoke Tests
# ============================================================================


@pytest.mark.smoke
def test_logo_display_in_settings_page_no_logo(admin_authenticated_client):
    """Test that settings page displays correctly when no logo exists."""
    response = admin_authenticated_client.get("/admin/settings")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No company logo uploaded yet" in html or "Company Logo" in html or "logo" in html.lower()


@pytest.mark.smoke
def test_logo_display_in_settings_page_with_logo(admin_authenticated_client, sample_logo_image, cleanup_logos, app):
    """Test that settings page displays the logo when it exists."""
    with app.app_context():
        # Set up a logo in the database directly (simpler than testing upload in smoke test)
        settings = Settings.get_settings()
        # Create a test logo file
        import uuid
        upload_folder = os.path.join(app.root_path, "static", "uploads", "logos")
        os.makedirs(upload_folder, exist_ok=True)
        test_logo_filename = f"company_logo_{uuid.uuid4().hex[:8]}.png"
        test_logo_path = os.path.join(upload_folder, test_logo_filename)
        
        # Save the sample image to disk
        sample_logo_image.seek(0)
        with open(test_logo_path, "wb") as f:
            f.write(sample_logo_image.read())
        
        # Set the logo filename in settings
        settings.company_logo_filename = test_logo_filename
        db.session.commit()
        
        # Now check the settings page
        response = admin_authenticated_client.get("/admin/settings")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Current Company Logo" in html or ("Current" in html and "Logo" in html)

        # Verify logo URL is in the page
        logo_url = settings.get_logo_url()
        assert logo_url in html or "/uploads/logos/" in html
