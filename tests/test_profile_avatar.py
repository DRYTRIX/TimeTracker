import io
import pytest
from PIL import Image


def _make_test_image_bytes(fmt='PNG', size=(10, 10), color=(255, 0, 0, 255)):
    img = Image.new('RGBA', size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


@pytest.mark.routes
def test_upload_avatar(authenticated_client, user, app):
    with app.app_context():
        assert user.avatar_filename is None

    data = {
        'full_name': 'Test User',
        'preferred_language': 'en',
        'avatar': ( _make_test_image_bytes('PNG'), 'avatar.png' )
    }
    resp = authenticated_client.post('/profile/edit', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        from app.models import User
        u = User.query.get(user.id)
        assert u.avatar_filename is not None
        assert u.get_avatar_url() is not None


@pytest.mark.routes
def test_remove_avatar(authenticated_client, user, app):
    # First upload an avatar
    data = {
        'full_name': 'Test User',
        'preferred_language': 'en',
        'avatar': ( _make_test_image_bytes('PNG'), 'avatar.png' )
    }
    authenticated_client.post('/profile/edit', data=data, content_type='multipart/form-data')

    with app.app_context():
        from app.models import User
        u = User.query.get(user.id)
        assert u.avatar_filename

    # Remove it
    resp = authenticated_client.post('/profile/avatar/remove', data={'csrf_token': 'disabled-in-tests'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        from app.models import User
        u = User.query.get(user.id)
        assert u.avatar_filename is None


