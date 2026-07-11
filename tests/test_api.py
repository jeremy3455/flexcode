import os
import tempfile

import pytest

import database

# Use a temporary database for all API tests
tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp_db.close()
database.DB_PATH = tmp_db.name

from fastapi.testclient import TestClient
from web_app import app


@pytest.fixture(autouse=True)
def reset_db():
    database.init_db()
    yield
    # Clear all tables between tests
    conn = database.get_connection()
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


def cleanup():
    conn = database.get_connection()
    conn.close()
    try:
        os.unlink(tmp_db.name)
    except PermissionError:
        pass


client = TestClient(app)


def test_register():
    resp = client.post("/register", json={"username": "nuevo", "password": "12345678"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "nuevo"


def test_register_duplicate():
    client.post("/register", json={"username": "dup", "password": "12345678"})
    resp = client.post("/register", json={"username": "dup", "password": "56789012"})
    assert resp.status_code == 409


def test_register_short_username():
    resp = client.post("/register", json={"username": "ab", "password": "12345678"})
    assert resp.status_code == 400


def test_login():
    client.post("/register", json={"username": "user1", "password": "pass1234"})
    resp = client.post("/login", json={"username": "user1", "password": "pass1234"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong():
    resp = client.post("/login", json={"username": "noexiste", "password": "x"})
    assert resp.status_code == 401


def test_me():
    reg = client.post("/register", json={"username": "meuser", "password": "12345678"})
    token = reg.json()["token"]
    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


def test_me_unauthorized():
    resp = client.get("/me")
    assert resp.status_code == 401


def test_create_session_authenticated():
    reg = client.post("/register", json={"username": "sess", "password": "12345678"})
    token = reg.json()["token"]
    resp = client.post("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "session_id" in resp.json()


def test_guest_session():
    resp = client.post("/sessions/guest")
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    assert sid.startswith("guest_")


def test_list_sessions():
    reg = client.post("/register", json={"username": "listuser", "password": "12345678"})
    token = reg.json()["token"]
    client.post("/sessions", headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_index():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
