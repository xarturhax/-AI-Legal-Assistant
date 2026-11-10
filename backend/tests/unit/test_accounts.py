import re
from pathlib import Path

from app import create_app
from app.db.migrate import upgrade
from app.db.models import User
from app.extensions import db
from sqlalchemy import text


def register_and_login(app, email):
    client = app.test_client()
    assert (
        client.post(
            "/reg", data={"email": email, "password": "Secure-local-123", "display_name": email}
        ).status_code
        == 302
    )
    files = sorted(
        Path(app.config["DEV_MAIL_DIR"]).glob("*.txt"), key=lambda p: p.stat().st_mtime_ns
    )
    code = next(
        re.search(r"Код: (\S+)", p.read_text(encoding="utf-8"))[1]
        for p in reversed(files)
        if f"email: {email}\n" in p.read_text(encoding="utf-8")
    )
    assert client.post("/verification", data={"email": email, "token": code}).status_code == 302
    assert client.post("/verification", data={"email": email, "token": code}).status_code == 400
    assert (
        client.post("/auth", data={"email": email, "password": "Secure-local-123"}).status_code
        == 302
    )
    return client


def test_ownership_and_no_guest_access(app):
    alice = register_and_login(app, "alice@example.test")
    bob = register_and_login(app, "bob@example.test")
    created = alice.post("/api/notes", json={"text": "Личная заметка"})
    assert created.status_code == 201
    note_id = created.json["id"]
    assert bob.get("/api/notes").json["items"] == []
    assert bob.put("/api/notes", json={"id": note_id, "text": "подмена"}).status_code == 404
    assert bob.delete("/api/notes", json={"id": note_id}).status_code == 404
    assert app.test_client().get("/api/notes").status_code == 401
    assert app.test_client().post("/api/notes", json={"text": "подмена"}).status_code == 401
    assert alice.put("/api/notes", json={"id": note_id, "text": "Обновлено"}).status_code == 200
    assert alice.get("/api/notes").json["items"][0]["text"] == "Обновлено"


def test_passwords_xss_and_calendar(app):
    alice = register_and_login(app, "alice@example.test")
    alice.post("/api/notes", json={"text": "<script>alert('x')</script>"})
    assert b"<script>alert" not in alice.get("/cabinet").data
    event = alice.post(
        "/api/calendar",
        json={"title": "Встреча", "starts_at": "2026-11-01T12:00", "timezone": "Europe/Minsk"},
    )
    assert event.status_code == 201
    assert alice.get("/show_calendar").status_code == 200
    assert (
        alice.post(
            "/api/calendar",
            json={"title": "Ошибка", "starts_at": "bad", "timezone": "Europe/Minsk"},
        ).status_code
        == 400
    )
    with app.app_context():
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.password_hash.startswith("scrypt:")
        assert user.password_hash != "Secure-local-123"


def test_csrf_is_required(app):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    assert (
        client.post(
            "/reg", data={"email": "test@example.test", "password": "Secure-local-123"}
        ).status_code
        == 400
    )
    assert client.post("/api/notes", json={"text": "x"}).status_code == 401
    assert client.post("/api/forum/topics", json={"title": "x", "body": "x"}).status_code == 401
    page = client.get("/reg").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page)[1]
    assert (
        client.post(
            "/reg",
            data={
                "email": "test@example.test",
                "password": "Secure-local-123",
                "csrf_token": token,
            },
        ).status_code
        == 302
    )


def test_migrations_and_persistence(tmp_path):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-only-" + "x" * 40,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "persistent.sqlite3"),
    }
    first = create_app(config)
    with first.app_context():
        upgrade()
        upgrade()
        db.session.add(User(email="persist@example.test", password_hash="test-hash"))
        db.session.commit()
        db.session.remove()
        db.engine.dispose()
    second = create_app(config)
    with second.app_context():
        upgrade()
        assert db.session.execute(db.select(User)).scalar_one().email == "persist@example.test"


def test_recovery_invalidates_sessions(app):
    email = "alice@example.test"
    alice = register_and_login(app, email)
    other = app.test_client()
    other.post("/recover", data={"email": email})
    files = sorted(
        Path(app.config["DEV_MAIL_DIR"]).glob("*.txt"), key=lambda p: p.stat().st_mtime_ns
    )
    code = re.search(r"Код: (\S+)", files[-1].read_text(encoding="utf-8"))[1]
    assert (
        other.post(
            "/recover", data={"email": email, "token": code, "password": "Changed-local-456"}
        ).status_code
        == 302
    )
    assert alice.get("/api/profile").status_code == 401
    assert (
        other.post("/auth", data={"email": email, "password": "Changed-local-456"}).status_code
        == 302
    )


def test_account_pages(app):
    alice = register_and_login(app, "alice@example.test")
    for path in (
        "/cabinet",
        "/show_calendar",
        "/requests",
        "/directory",
        "/auth",
        "/reg",
        "/recover",
        "/verification",
    ):
        assert alice.get(path).status_code == 200
    assert alice.put("/api/profile", json={"display_name": "Новое имя"}).status_code == 200
    assert (
        alice.put("/api/settings", json={"mode": "llm", "timezone": "Europe/Minsk"}).status_code
        == 200
    )
    assert alice.get("/api/settings").json["mode"] == "llm"
    assert 'value="llm" selected' in alice.get("/requests").data.decode()
