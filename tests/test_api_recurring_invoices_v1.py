import pytest
from datetime import date, timedelta

from app import create_app, db
from app.models import User, Client, Project, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_recurring.sqlite',
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
    u = User(username='riuser', email='ri@example.com', role='admin')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='RI Token',
        scopes='read:recurring_invoices,write:recurring_invoices,read:invoices,write:invoices'
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def setup_project_client(app):
    c = Client(name='RI Client', email='client@example.com')
    db.session.add(c)
    db.session.commit()
    p = Project(name='RI Project', client_id=c.id, status='active')
    db.session.add(p)
    db.session.commit()
    return p, c


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_recurring_invoices_crud_and_generate(client, api_token, user, setup_project_client):
    project, cl = setup_project_client
    # list empty
    r = client.get('/api/v1/recurring-invoices', headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()['recurring_invoices'] == []

    # create
    payload = {
        'name': 'Monthly Billing',
        'project_id': project.id,
        'client_id': cl.id,
        'client_name': cl.name,
        'frequency': 'monthly',
        'interval': 1,
        'next_run_date': date.today().isoformat(),
        'tax_rate': 0.0
    }
    r = client.post('/api/v1/recurring-invoices', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    ri_id = r.get_json()['recurring_invoice']['id']

    # get
    r = client.get(f'/api/v1/recurring-invoices/{ri_id}', headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/recurring-invoices/{ri_id}', headers=_auth(api_token), json={'notes': 'updated'})
    assert r.status_code == 200

    # generate
    r = client.post(f'/api/v1/recurring-invoices/{ri_id}/generate', headers=_auth(api_token))
    assert r.status_code in (200, 201)

    # deactivate
    r = client.delete(f'/api/v1/recurring-invoices/{ri_id}', headers=_auth(api_token))
    assert r.status_code == 200

