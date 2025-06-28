import os,sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid

from fastapi.testclient import TestClient
# Configure a temporary SQLite database
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'

from app.app.main import app
from app.app.dependencies import engine
from app.app import models

models.Base.metadata.create_all(bind=engine)

client = TestClient(app)


def teardown_module(module):
    try:
        os.remove('test.db')
    except FileNotFoundError:
        pass


def unique_email():
    return f"user_{uuid.uuid4().hex}@example.com"


def signup_client(email=None, password='pass'):
    if email is None:
        email = unique_email()
    resp = client.post('/signup', json={'email': email, 'password': password})
    assert resp.status_code == 200
    return resp.json()['access_token']


def test_health():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


def test_signup_and_token():
    token = signup_client()
    assert token


def test_upload_ask_history():
    token = signup_client()
    headers = {'Authorization': f'Bearer {token}'}
    files = {'file': ('note.txt', b'hello world', 'text/plain')}
    r = client.post('/upload', files=files, headers=headers)
    assert r.status_code == 200
    doc_id = r.json()['id']

    ask_resp = client.post('/ask', json={'document_id': doc_id, 'question': 'hi?'}, headers=headers)
    assert ask_resp.status_code == 200
    assert 'answer' in ask_resp.json()

    hist_resp = client.get('/history', headers=headers)
    assert hist_resp.status_code == 200
    items = hist_resp.json()
    assert len(items) == 1
    assert items[0]['question'] == 'hi?'
