import os
import tempfile
import uuid

import pytest

import database


@pytest.fixture(autouse=True)
def setup_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    old_path = database.DB_PATH
    database.DB_PATH = tmp.name
    database.init_db()
    yield
    # Close all connections so the file can be deleted
    conn = database.get_connection()
    conn.close()
    try:
        os.unlink(tmp.name)
    except PermissionError:
        pass
    database.DB_PATH = old_path


def test_create_and_get_user():
    uid = str(uuid.uuid4())
    database.create_user(uid, "testuser", "hash123")
    user = database.get_user_by_username("testuser")
    assert user is not None
    assert user["id"] == uid
    assert user["password_hash"] == "hash123"


def test_get_user_not_found():
    user = database.get_user_by_username("nonexistent")
    assert user is None


def test_get_user_by_id():
    uid = str(uuid.uuid4())
    database.create_user(uid, "user2", "hash456")
    user = database.get_user_by_id(uid)
    assert user is not None
    assert user["username"] == "user2"


def test_create_session():
    sid = str(uuid.uuid4())
    uid = str(uuid.uuid4())
    database.create_user(uid, "session_user", "hash")
    database.create_session(sid, uid)
    sessions = database.get_sessions(uid)
    assert len(sessions) == 1
    assert sessions[0]["id"] == sid


def test_add_and_get_messages():
    sid = str(uuid.uuid4())
    database.create_session(sid)
    database.add_message(sid, "user", "Hola")
    database.add_message(sid, "assistant", "Hola, ¿cómo estás?")
    msgs = database.get_messages(sid)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "Hola, ¿cómo estás?"


def test_delete_session():
    sid = str(uuid.uuid4())
    database.create_session(sid)
    database.add_message(sid, "user", "msg")
    database.delete_session(sid)
    assert database.get_messages(sid) == []
    sessions = database.get_sessions()
    ids = [s["id"] for s in sessions]
    assert sid not in ids


def test_update_session_title():
    sid = str(uuid.uuid4())
    database.create_session(sid)
    database.update_session_title(sid, "Nuevo título")
    sessions = database.get_sessions()
    for s in sessions:
        if s["id"] == sid:
            assert s["title"] == "Nuevo título"
            return
    assert False, "Session not found"
