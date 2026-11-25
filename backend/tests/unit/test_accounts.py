import json
import re
import smtplib
from base64 import urlsafe_b64decode
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from app import create_app
from app.db.migrate import upgrade
from app.db.models import User, VerificationToken
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


def test_repeat_registration_can_resume_without_changing_password(app):
    client = app.test_client()
    registration = {"email": "pending@example.test", "password": "Secure-local-123"}
    assert client.post("/reg", data=registration).location == "/verification"
    original = next(Path(app.config["DEV_MAIL_DIR"]).glob("*.txt")).read_text(encoding="utf-8")
    assert client.post("/reg", data={**registration, "password": "Different-123"}).location == (
        "/verification"
    )
    assert client.post("/resend_code", data={"email": registration["email"]}).status_code == 302
    old_code = re.search(r"Код: (\S+)", original)[1]
    new_code = next(
        code
        for path in Path(app.config["DEV_MAIL_DIR"]).glob("*.txt")
        if (code := re.search(r"Код: (\S+)", path.read_text(encoding="utf-8"))[1]) != old_code
    )
    assert (
        client.post(
            "/verification", data={"email": registration["email"], "token": old_code}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/verification", data={"email": registration["email"], "token": new_code}
        ).status_code
        == 302
    )
    assert client.post("/auth", data=registration).location == "/cabinet"


@pytest.mark.mock
def test_smtp_delivery_failure_rolls_back_registration(app, monkeypatch):
    app.config.update(
        SMTP_HOST="smtp.example.test", SMTP_USERNAME="themis@example.test", SMTP_PASSWORD="test"
    )

    def reject(*args, **kwargs):
        raise smtplib.SMTPAuthenticationError(535, b"test failure")

    monkeypatch.setattr("app.auth.mail.smtplib.SMTP", reject)
    response = app.test_client().post(
        "/reg", data={"email": "pending@example.test", "password": "Secure-local-123"}
    )
    assert response.status_code == 503
    with app.app_context():
        assert db.session.execute(db.select(User)).scalar_one_or_none() is None
        assert db.session.execute(db.select(VerificationToken)).scalar_one_or_none() is None
    assert not list(Path(app.config["DEV_MAIL_DIR"]).glob("*.txt"))


@pytest.mark.mock
def test_gmail_api_sends_registration_code_with_oauth(app, tmp_path, monkeypatch):
    credential_file = tmp_path / "oauth.json"
    credential_file.write_text(
        json.dumps({"client_id": "test", "client_secret": "test", "refresh_token": "test"}),
        encoding="utf-8",
    )
    app.config.update(GMAIL_OAUTH_FILE=str(credential_file), GMAIL_SENDER="themis@example.test")
    messages = []

    def google(request):
        if request.url.host == "oauth2.googleapis.com":
            assert parse_qs(request.content.decode())["grant_type"] == ["refresh_token"]
            return httpx.Response(200, json={"access_token": "test-access-token"})
        assert str(request.url) == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        assert request.headers["Authorization"] == "Bearer test-access-token"
        content = urlsafe_b64decode(json.loads(request.content)["raw"])
        messages.append(BytesParser(policy=policy.default).parsebytes(content))
        return httpx.Response(200, json={"id": "test-message"})

    http_client = httpx.Client
    monkeypatch.setattr(
        "app.auth.mail.httpx.Client",
        lambda **kwargs: http_client(transport=httpx.MockTransport(google)),
    )
    client = app.test_client()
    email = "pending@example.test"
    assert (
        client.post("/reg", data={"email": email, "password": "Secure-local-123"}).status_code
        == 302
    )
    (message,) = messages
    assert message["To"].addresses[0].addr_spec == email
    assert message["From"].addresses[0].addr_spec == "themis@example.test"
    code = re.search(r"Код подтверждения аккаунта: (\S+)", message.get_content())[1]
    assert client.post("/verification", data={"email": email, "token": code}).status_code == 302
    assert not list(Path(app.config["DEV_MAIL_DIR"]).glob("*.txt"))
