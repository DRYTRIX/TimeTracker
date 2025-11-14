import pytest

from app import create_app, db
from app.models import User, Client, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_client_notes.sqlite',
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
def user(app):
    u = User(username='cnoteuser', email='cnote@example.com', role='user')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='ClientNotes Token',
        scopes='read:clients,write:clients'
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def client_model(app):
    c = Client(name='Client Notes', email='client@example.com')
    db.session.add(c)
    db.session.commit()
    return c


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_client_notes_crud(client, api_token, client_model):
    # list empty
    r = client.get(f'/api/v1/clients/{client_model.id}/notes', headers=_auth(api_token))
    assert r.status_code == 200
    body = r.get_json()
    assert 'notes' in body and 'pagination' in body
    assert body['notes'] == []

    # create
    payload = {'content': 'Important note', 'is_important': True}
    r = client.post(f'/api/v1/clients/{client_model.id}/notes', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    note_id = r.get_json()['note']['id']

    # get
    r = client.get(f'/api/v1/client-notes/{note_id}', headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/client-notes/{note_id}', headers=_auth(api_token), json={'content': 'Updated'})
    assert r.status_code == 200
    assert r.get_json()['note']['content'] == 'Updated'

    # delete
    r = client.delete(f'/api/v1/client-notes/{note_id}', headers=_auth(api_token))
    assert r.status_code == 200

