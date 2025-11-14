import pytest
from datetime import date

from app import create_app, db
from app.models import User, Expense, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_expenses.sqlite',
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
    u = User(username='expuser', email='expuser@example.com', role='user')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='Expenses Token',
        scopes='read:expenses,write:expenses'
    )
    db.session.add(token)
    db.session.commit()
    return plain


def _auth(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


def test_expenses_crud(client, api_token):
    # list empty
    r = client.get('/api/v1/expenses', headers=_auth(api_token))
    assert r.status_code == 200
    assert r.get_json()['expenses'] == []

    # create
    payload = {
        'title': 'Taxi',
        'category': 'travel',
        'amount': 23.5,
        'expense_date': date.today().isoformat(),
        'billable': True
    }
    r = client.post('/api/v1/expenses', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    exp = r.get_json()['expense']
    exp_id = exp['id']

    # get
    r = client.get(f'/api/v1/expenses/{exp_id}', headers=_auth(api_token))
    assert r.status_code == 200

    # update
    r = client.patch(f'/api/v1/expenses/{exp_id}', headers=_auth(api_token), json={'notes': 'airport ride'})
    assert r.status_code == 200
    assert r.get_json()['expense']['notes'] == 'airport ride'

    # delete (reject)
    r = client.delete(f'/api/v1/expenses/{exp_id}', headers=_auth(api_token))
    assert r.status_code == 200
    db.session.expire_all()
    assert Expense.query.get(exp_id).status == 'rejected'

