import hashlib
import re
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.db.models import Profile, User, VerificationToken, now
from app.extensions import db
from app.web_utils import payload, string_value

bp = Blueprint("auth", __name__)


def find_user(email):
    return db.session.execute(
        db.select(User).filter_by(email=email.casefold())
    ).scalar_one_or_none()


def email_value(data):
    email = string_value(data, "email", 254).casefold()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        abort(400, description="Проверьте адрес электронной почты.")
    return email


def password_value(data):
    password = string_value(data, "password", 256)
    if len(password) < 10:
        abort(400, description="Пароль должен содержать от 10 до 256 символов.")
    return password


def issue_token(user, purpose):
    if not current_app.config["DEV_LOCAL_MAIL"]:
        abort(
            503,
            description="Доставка кода не настроена. Включите локальный режим DEV_LOCAL_MAIL=1.",
        )
    token = secrets.token_urlsafe(32)
    db.session.execute(
        db.update(VerificationToken)
        .where(
            VerificationToken.user_id == user.id,
            VerificationToken.purpose == purpose,
            VerificationToken.used_at.is_(None),
        )
        .values(used_at=now())
    )
    db.session.add(
        VerificationToken(
            user_id=user.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            purpose=purpose,
            expires_at=now() + timedelta(minutes=15),
        )
    )
    directory = Path(
        current_app.config.get("DEV_MAIL_DIR", str(Path(current_app.instance_path) / "dev-mail"))
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (secrets.token_hex(12) + ".txt")
    path.write_text(
        f"ЛОКАЛЬНЫЙ DEV-РЕЖИМ: письмо не отправлялось.\nemail: {user.email}\n"
        f"purpose: {purpose}\nКод: {token}\nСрок: 15 минут.\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass


def consume_token(email, code, purpose):
    user = find_user(email)
    token = db.session.execute(
        db.select(VerificationToken).filter_by(
            token_hash=hashlib.sha256(code.encode()).hexdigest(),
            purpose=purpose,
            user_id=user.id if user else -1,
        )
    ).scalar_one_or_none()
    if token is None or token.used_at is not None or token.expires_at < now():
        abort(400, description="Код недействителен или истёк.")
    consumed = db.session.execute(
        db.update(VerificationToken)
        .where(
            VerificationToken.id == token.id,
            VerificationToken.used_at.is_(None),
            VerificationToken.expires_at >= now(),
        )
        .values(used_at=now())
    )
    if consumed.rowcount != 1:
        abort(400, description="Код уже использован.")
    return user


@bp.route("/reg", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = payload()
        email = email_value(data)
        password = password_value(data)
        kind = data.get("user_type", "user")
        if not isinstance(kind, str) or kind not in {"user", "specialist"}:
            abort(400, description="Неизвестный тип профиля.")
        user = User(email=email, password_hash=generate_password_hash(password), role=kind)
        db.session.add(user)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            abort(409, description="Не удалось создать аккаунт с этим адресом.")
        name = string_value(data, "display_name", 120, required=False)
        db.session.add(Profile(user_id=user.id, display_name=name))
        issue_token(user, "verify")
        db.session.commit()
        session["verification_email"] = email
        return redirect("/verification")
    return render_template("auth.html", kind="reg")


@bp.route("/auth", methods=["GET", "POST"])
def authenticate():
    if request.method == "POST":
        data = payload()
        user = find_user(email_value(data))
        password = string_value(data, "password", 256)
        # Одинаковая ветка проверки хеша для неизвестного пользователя.
        stored = user.password_hash if user else current_app.config["DUMMY_PASSWORD_HASH"]
        valid = check_password_hash(stored, password)
        if not user or not valid:
            abort(401, description="Неверный адрес или пароль.")
        if not user.is_verified:
            abort(403, description="Подтвердите аккаунт кодом из локального dev-письма.")
        session.clear()
        login_user(user, fresh=True)
        return redirect("/cabinet")
    return render_template("auth.html", kind="auth")


@bp.route("/verification", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        data = payload()
        user = consume_token(email_value(data), string_value(data, "token", 100), "verify")
        user.is_verified = True
        db.session.commit()
        flash("Аккаунт подтверждён. Теперь можно войти.")
        return redirect("/auth")
    return render_template("auth.html", kind="verification")


@bp.post("/resend_code")
def resend():
    user = find_user(email_value(payload()))
    if user and not user.is_verified:
        issue_token(user, "verify")
        db.session.commit()
    flash("Если аккаунт существует, новый код сохранён в локальном dev-письме.")
    return redirect("/verification")


@bp.route("/recover", methods=["GET", "POST"])
def recover():
    if request.method == "POST":
        data = payload()
        email = email_value(data)
        code = string_value(data, "token", 100, required=False)
        if code:
            user = consume_token(email, code, "recover")
            user.password_hash = generate_password_hash(password_value(data))
            user.auth_version += 1  # Все прежние сессии перестают действовать.
            db.session.commit()
            flash("Пароль изменён. Войдите с новым паролем.")
            return redirect("/auth")
        user = find_user(email)
        if user:
            issue_token(user, "recover")
            db.session.commit()
        flash("Если аккаунт существует, код восстановления сохранён в локальном dev-письме.")
    return render_template("auth.html", kind="recover")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")


@bp.get("/guest_mode")
def guest():
    return redirect("/requests")
