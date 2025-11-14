import pytest
from datetime import date

from app import create_app, db
from app.models import User, Client, Project, Invoice, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_credit_notes.sqlite',
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
    u = User(username='cnuser', email='cn@example.com', role='admin')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='CN Token',
        scopes='read:invoices,write:invoices'
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def setup_invoice(app, user):
    c = Client(name='CN Client', email='client@example.com')
    db.session.add(c)
    db.session.commit()
    p = Project(name='CN Project', client_id=c.id, status='active')
    db.session.add(p)
    db.session.commit()
    inv = Invoice(
        invoice_number=Invoice.generate_invoice_number(),
        project_id=p.id,
        client_name=c.name,
        client_id=c.id,
        due_date=date.today(),
        created_by=user.id,
    )
    db.session.add(inv)
    db.session.commit()
    return inv


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_credit_notes_crud(client, api_token, setup_invoice):
    inv = setup_invoice
    # list empty
    r = client.get(f'/api/v1/credit-notes?invoice_id={inv.id}', headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()['credit_notes'] == []

    # create
    payload = {'invoice_id': inv.id, 'amount': 10.0, 'reason': 'Discount'}
    r = client.post('/api/v1/credit-notes', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    cn_id = r.get_json()['credit_note']['id']

    # get
    r = client.get(f'/api/v1/credit-notes/{cn_id}', headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/credit-notes/{cn_id}', headers=_auth(api_token), json={'reason': 'Updated'})
    assert r.status_code == 200

    # delete
    r = client.delete(f'/api/v1/credit-notes/{cn_id}', headers=_auth(api_token))
    assert r.status_code == 200

