import pytest

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_invoice_templates.sqlite',
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    u = User(username='admin', email='admin@example.com', role='admin')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin_token(app, admin_user):
    token, plain = ApiToken.create_token(
        user_id=admin_user.id,
        name='Admin Token',
        scopes='admin:all'
    )
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_invoice_pdf_templates_list_and_get(client, admin_token):
    r = client.get('/api/v1/invoice-pdf-templates', headers=_auth(admin_token))
    assert r.status_code == 200
    # A4 default template is always available via get_template()
    r = client.get('/api/v1/invoice-pdf-templates/A4', headers=_auth(admin_token))
    assert r.status_code == 200

