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


def test_invoice_templates_crud(client, admin_token):
    # list (empty)
    r = client.get('/api/v1/invoice-templates', headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.get_json()['templates'] == []

    # create
    r = client.post('/api/v1/invoice-templates', headers=_auth(admin_token), json={
        'name': 'Clean', 'description': 'Clean template', 'html': '<div>Hi</div>', 'css': 'div{color:#000}'
    })
    assert r.status_code == 201
    tpl_id = r.get_json()['template']['id']

    # get
    r = client.get(f'/api/v1/invoice-templates/{tpl_id}', headers=_auth(admin_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/invoice-templates/{tpl_id}', headers=_auth(admin_token), json={'is_default': True})
    assert r.status_code == 200

    # delete
    r = client.delete(f'/api/v1/invoice-templates/{tpl_id}', headers=_auth(admin_token))
    assert r.status_code == 200

