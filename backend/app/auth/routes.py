import hashlib
import re
import secrets
from datetime import timedelta
from email.headerregistry import Address

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.mail import deliver_code, mail_mode
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
    try:
        if Address(addr_spec=email).addr_spec != email:
            raise ValueError
    except (ValueError, IndexError):
        abort(400, description="Проверьте адрес электронной почты.")
    return email


def password_value(data):
    password = string_value(data, "password", 256)
    if len(password) < 10:
        abort(400, description="Пароль должен содержать от 10 до 256 символов.")
    return password


def issue_token(user, purpose):
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
    try:
        deliver_code(user.email, purpose, token)
    except OSError:
        db.session.rollback()
        # Журналу достаточно факта сбоя. Ответ SMTP может содержать адрес или другие данные.
        current_app.logger.warning("Не удалось доставить код аккаунта (%s).", purpose)
        abort(503, description="Не удалось отправить код. Повторите попытку позже.")


def auth_page(kind):
    return render_template("auth.html", kind=kind, delivery=mail_mode(current_app.config))


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
            existing = find_user(email)
            if existing is not None and not existing.is_verified:
                session["verification_email"] = email
                flash("Если код уже приходил, введите его. Новый код можно запросить ниже.")
                return redirect("/verification")
            flash("Аккаунт с этим адресом уже существует. Войдите или восстановите доступ.")
            return auth_page("reg"), 409
        name = string_value(data, "display_name", 120, required=False)
        db.session.add(Profile(user_id=user.id, display_name=name))
        issue_token(user, "verify")
        db.session.commit()
        session["verification_email"] = email
        if mail_mode(current_app.config) in {"smtp", "gmail"}:
            flash("Код подтверждения отправлен на указанный адрес.")
        return redirect("/verification")
    return auth_page("reg")


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
            session["verification_email"] = user.email
            flash("Подтвердите аккаунт. При необходимости запросите новый код.")
            return redirect("/verification")
        session.clear()
        login_user(user, fresh=True)
        return redirect("/cabinet")
    return auth_page("auth")


@bp.route("/verification", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        data = payload()
        user = consume_token(email_value(data), string_value(data, "token", 100), "verify")
        user.is_verified = True
        db.session.commit()
        flash("Аккаунт подтверждён. Теперь можно войти.")
        return redirect("/auth")
    return auth_page("verification")


@bp.post("/resend_code")
def resend():
    email = email_value(payload())
    user = find_user(email)
    if user and not user.is_verified:
        issue_token(user, "verify")
        db.session.commit()
    session["verification_email"] = email
    if mail_mode(current_app.config) in {"smtp", "gmail"}:
        flash("Если адрес ожидает подтверждения, на него отправлен новый код.")
    else:
        flash("Если адрес ожидает подтверждения, новый код доступен владельцу установки.")
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
        if mail_mode(current_app.config) in {"smtp", "gmail"}:
            flash("Если аккаунт существует, код восстановления отправлен на этот адрес.")
        else:
            flash("Если аккаунт существует, код восстановления доступен владельцу установки.")
    return auth_page("recover")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")


@bp.get("/guest_mode")
def guest():
    return redirect("/requests")
