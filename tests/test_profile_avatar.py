import io
import os
import pytest
from PIL import Image


def _make_test_image_bytes(fmt='PNG', size=(10, 10), color=(255, 0, 0, 255)):
    img = Image.new('RGBA', size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


@pytest.fixture
def avatar_test_app(app, temp_dir):
    """Configure app with temporary upload folder for avatar tests"""
    app.config['UPLOAD_FOLDER'] = temp_dir
    # Ensure the avatars directory exists
    avatars_dir = os.path.join(temp_dir, 'avatars')
    os.makedirs(avatars_dir, exist_ok=True)
    return app


@pytest.mark.routes
def test_upload_avatar(app, temp_dir, user):
    """Test uploading an avatar"""
    from app import db
    
    # Configure temp upload folder
    app.config['UPLOAD_FOLDER'] = temp_dir
    avatars_dir = os.path.join(temp_dir, 'avatars')
    os.makedirs(avatars_dir, exist_ok=True)
    
    # Create authenticated client
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        assert user.avatar_filename is None

        data = {
            'full_name': 'Test User',
            'preferred_language': 'en',
            'avatar': (_make_test_image_bytes('PNG'), 'avatar.png')
        }
        resp = client.post('/profile/edit', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert resp.status_code == 200

        from app.models import User
        u = User.query.get(user.id)
        assert u.avatar_filename is not None
        assert u.get_avatar_url() is not None


@pytest.mark.routes
def test_remove_avatar(app, temp_dir, user):
    """Test removing an avatar"""
    from app import db
    
    # Configure temp upload folder
    app.config['UPLOAD_FOLDER'] = temp_dir
    avatars_dir = os.path.join(temp_dir, 'avatars')
    os.makedirs(avatars_dir, exist_ok=True)
    
    # Create authenticated client
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        # First upload an avatar
        data = {
            'full_name': 'Test User',
            'preferred_language': 'en',
            'avatar': (_make_test_image_bytes('PNG'), 'avatar.png')
        }
        client.post('/profile/edit', data=data, content_type='multipart/form-data')

        from app.models import User
        u = User.query.get(user.id)
        assert u.avatar_filename

        # Remove it
        resp = client.post('/profile/avatar/remove', data={'csrf_token': 'disabled-in-tests'}, follow_redirects=True)
        assert resp.status_code == 200

        u = User.query.get(user.id)
        assert u.avatar_filename is None


