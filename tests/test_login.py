import json
import pytest
from fastapi.testclient import TestClient
from dental_lab.auth import hash_password, verify_password
from dental_lab.config import Settings, load, set_login
from dental_lab.server import create_app

WEB_PASSWORD = 'contraseña de prueba €'
API_KEY = 'independent-api-test-key'


@pytest.fixture
def web_client(tmp_path):
    settings = Settings(data=tmp_path, password=API_KEY, username='Técnico',
                        password_hash=hash_password(WEB_PASSWORD),
                        semantic=False, vision=False).prepare()
    with TestClient(create_app(settings, start_worker=False)) as client:
        yield client


def test_username_password_required_and_api_key_separate(web_client):
    c = web_client
    assert c.get('/api/cases').status_code == 401
    assert c.post('/login', json={'password': WEB_PASSWORD}).status_code == 422
    for username, password in [('Otro', WEB_PASSWORD), ('Técnico', 'incorrecta'), ('Técnico', API_KEY)]:
        response = c.post('/login', json={'username': username, 'password': password})
        assert response.status_code == 401
        assert response.json()['detail'] == 'Usuario o contraseña incorrectos'
        assert 'dental_session' not in c.cookies
    assert c.get('/api/cases', headers={'Authorization': 'Bearer '+API_KEY}).status_code == 200
    assert c.get('/api/cases', headers={'Authorization': 'Bearer incorrect-api-key'}).status_code == 401
    response = c.post('/login', json={'username': ' TÉCNICO ', 'password': WEB_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {'ok': True, 'username': 'Técnico'}
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Max-Age=43200' in cookie
    assert c.get('/api/cases').status_code == 200
    old_session = c.cookies['dental_session']
    assert c.post('/api/logout').status_code == 200
    assert c.get('/api/cases', headers={'Cookie': 'dental_session='+old_session}).status_code == 401


def test_login_throttle_and_cross_origin(web_client):
    c = web_client
    body = {'username': 'Técnico', 'password': WEB_PASSWORD}
    assert c.post('/login', json=body, headers={'Origin': 'https://other.example'}).status_code == 403
    body['password'] = 'incorrecta'
    for _ in range(10):
        assert c.post('/login', json=body).status_code == 401
    assert c.post('/login', json=body).status_code == 429


@pytest.mark.parametrize('encoded', [None, '', 'broken', 'pbkdf2_sha256$999999999999$a$b'])
def test_invalid_hash_never_falls_back_to_api_key(tmp_path, encoded):
    settings = Settings(data=tmp_path, password=API_KEY, password_hash=encoded,
                        semantic=False, vision=False).prepare()
    with TestClient(create_app(settings, start_worker=False)) as c:
        assert c.post('/login', json={'username': 'admin', 'password': API_KEY}).status_code == 401


def test_salted_hash_and_exact_password():
    first, second = hash_password(WEB_PASSWORD), hash_password(WEB_PASSWORD)
    assert first != second and WEB_PASSWORD not in first
    assert verify_password(WEB_PASSWORD, first)
    assert not verify_password(WEB_PASSWORD+' ', first)


def test_config_migration_and_login_change_preserve_api_and_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('DENTAL_LAB_DATA', str(tmp_path))
    path = tmp_path/'config.local.json'
    path.write_text(json.dumps({'password': API_KEY, 'blender': 'custom-blender',
                                'geometry_python': 'custom-python', 'model': 'custom-model'}))
    initial = load()
    assert initial.username == 'admin' and verify_password(API_KEY, initial.password_hash)
    set_login(tmp_path, 'Técnico', WEB_PASSWORD)
    configured = load()
    assert configured.username == 'Técnico' and verify_password(WEB_PASSWORD, configured.password_hash)
    assert not verify_password(API_KEY, configured.password_hash)
    assert configured.password == API_KEY and configured.blender == 'custom-blender'
    assert configured.geometry_python == 'custom-python' and configured.model == 'custom-model'
    assert WEB_PASSWORD not in path.read_text(encoding='utf-8')
