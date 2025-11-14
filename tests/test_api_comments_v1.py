import pytest

from app import create_app, db
from app.models import User, Project, Task, ApiToken


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_api_comments.sqlite',
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
    u = User(username='cuser', email='c@example.com', role='user')
    u.is_active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def api_token(app, user):
    token, plain = ApiToken.create_token(
        user_id=user.id,
        name='Comments Token',
        scopes='read:comments,write:comments'
    )
    db.session.add(token)
    db.session.commit()
    return plain


@pytest.fixture
def project(app):
    p = Project(name='Comments Project', status='active')
    db.session.add(p)
    db.session.commit()
    return p


def _auth(t):
    return {'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}


def test_comments_crud_project(client, api_token, project):
    # create
    payload = {'content': 'Hello world', 'project_id': project.id}
    r = client.post('/api/v1/comments', headers=_auth(api_token), json=payload)
    assert r.status_code == 201
    c_id = r.get_json()['comment']['id']

    # list
    r = client.get(f'/api/v1/comments?project_id={project.id}', headers=_auth(api_token))
    assert r.status_code == 200
    assert len(r.get_json()['comments']) >= 1

    # update
    r = client.patch(f'/api/v1/comments/{c_id}', headers=_auth(api_token), json={'content': 'Updated'})
    assert r.status_code == 200
    assert r.get_json()['comment']['content'] == 'Updated'

    # delete
    r = client.delete(f'/api/v1/comments/{c_id}', headers=_auth(api_token))
    assert r.status_code == 200

