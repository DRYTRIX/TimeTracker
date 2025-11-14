import pytest
from datetime import date

from app import create_app, db
from app.models import User, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_mileage.sqlite',
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
    u = User(username='mileuser', email='mileuser@example.com', role='user')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='Mileage Token',
        scopes='read:mileage,write:mileage'
    )
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_mileage_crud(client, api_token):
    # list empty
    r = client.get('/api/v1/mileage', headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()['mileage'] == []

    # create
    payload = {
        'trip_date': date.today().isoformat(),
        'purpose': 'Airport transfer',
        'start_location': 'Home',
        'end_location': 'Airport',
        'distance_km': 15.5,
        'rate_per_km': 0.3
    }
    r = client.post('/api/v1/mileage', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    entry = r.get_json()['mileage']
    eid = entry['id']

    # get
    r = client.get(f'/api/v1/mileage/{eid}', headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/mileage/{eid}', headers=_auth(api_token), json={'notes': 'return trip included'})
    assert r.status_code == 200
    assert r.get_json()['mileage']['notes'] == 'return trip included'

    # delete (reject)
    r = client.delete(f'/api/v1/mileage/{eid}', headers=_auth(api_token))
    assert r.status_code == 200

