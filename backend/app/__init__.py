import logging
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from app.config import configuration
from app.errors import ServiceError
from app.extensions import csrf, login
from app.extensions import db as database
from app.legal.service import LegalService
from app.ostis.client import OstisClient


@event.listens_for(Engine, "connect")
def sqlite_options(connection, _):
    if isinstance(connection, sqlite3.Connection):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")


def create_app(overrides=None):
    options = (
        {"instance_path": os.environ["APP_INSTANCE_PATH"]} if os.getenv("APP_INSTANCE_PATH") else {}
    )
    app = Flask(__name__, instance_relative_config=True, **options)
    app.json.ensure_ascii = False
    app.config.from_mapping(configuration())
    if overrides:
        app.config.update(overrides)
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "CHANGE_ME_LOCALLY":
        raise ValueError(
            "Задайте SECRET_KEY: случайный локальный секрет длиной не менее 32 символов."
        )
    if len(app.config["SECRET_KEY"]) < 32:
        raise ValueError("SECRET_KEY слишком короткий.")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database.init_app(app)
    login.init_app(app)
    from app.db.models import User

    @login.user_loader
    def load_user(identifier):
        try:
            user_id, version = map(int, identifier.split(":"))
            user = database.session.get(User, user_id)
            return user if user and user.auth_version == version else None
        except (ValueError, TypeError):
            return None

    @login.unauthorized_handler
    def unauthorized():
        from flask import redirect

        if request.path.startswith("/api/"):
            return jsonify(error={"code": 401, "message": "Требуется вход в аккаунт."}), 401
        return redirect("/auth")

    @app.before_request
    def private_api_authentication():
        private = (
            "/api/profile",
            "/api/settings",
            "/api/history",
            "/api/notes",
            "/api/bookmarks",
            "/api/calendar",
            "/api/test/",
        )
        private_forum_write = request.path.startswith("/api/forum/") and request.method != "GET"
        if (
            request.path.startswith(private) or private_forum_write
        ) and not current_user.is_authenticated:
            return unauthorized()

    csrf.init_app(app)
    app.config["DUMMY_PASSWORD_HASH"] = generate_password_hash(os.urandom(32).hex())
    from app.account.routes import bp as account_bp
    from app.auth.routes import bp as auth_bp
    from app.rate_limit import install_rate_limits

    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    from app.documents.routes import bp as documents_bp
    from app.forum.routes import bp as forum_bp
    from app.news.routes import bp as news_bp
    from app.test_module.routes import bp as quiz_bp

    for blueprint in (forum_bp, news_bp, documents_bp, quiz_bp):
        app.register_blueprint(blueprint)
    install_rate_limits(app)
    ostis = OstisClient(app.config["OSTIS_WS_URL"], app.config["OSTIS_TIMEOUT_SECONDS"])
    from app.llm.interpreter import OllamaInterpreter

    interpreter = OllamaInterpreter(
        app.config["OLLAMA_BASE_URL"],
        app.config["OLLAMA_MODEL"],
        app.config["OLLAMA_TIMEOUT_SECONDS"],
    )
    app.extensions["legal_service"] = LegalService(ostis, interpreter)
    from app.legal.routes import bp

    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return render_template("home.html")

    @app.get("/health/live")
    def live():
        return {"status": "alive", "mock": False}

    @app.get("/health/ready")
    def ready():
        statuses = {"database": False, "ostis": False, "llm": False}
        try:
            version = database.session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            statuses["database"] = version == "003_recommendations"
        except Exception:
            database.session.rollback()
        try:
            statuses["ostis"] = bool(ostis.ready().get("kb_loaded"))
        except ServiceError:
            pass
        interpreter = app.extensions["legal_service"].interpreter
        if interpreter:
            statuses["llm"] = interpreter.ready()
        # LLM необязательна для baseline, но её статус всегда показывается отдельно.
        critical = statuses["database"] and statuses["ostis"]
        if app.config["LEGAL_QUERY_DEFAULT_MODE"] == "llm":
            critical = critical and statuses["llm"]
        return jsonify(**statuses, mock=False), 200 if critical else 503

    @app.errorhandler(ServiceError)
    def service_error(error):
        logging.getLogger(__name__).warning("Dependency failure code=%s", error.code)
        if request.path.startswith(("/api/", "/health/")):
            return jsonify(
                error={"code": error.code, "message": str(error)}, runtime={"mock": False}
            ), error.status
        return render_template("error.html", message=str(error), code=error.status), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error={"code": error.code, "message": error.description}), error.code
        return render_template("error.html", message=error.description, code=error.code), error.code

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = "Форма устарела или отсутствует CSRF-токен. Обновите страницу."
        if request.path.startswith("/api/"):
            return jsonify(error={"code": 400, "message": message}), 400
        return render_template("error.html", message=message, code=400), 400

    from sqlalchemy.exc import IntegrityError

    @app.errorhandler(IntegrityError)
    def conflict(error):
        database.session.rollback()
        message = "Запись уже существует или была изменена другим запросом. Обновите страницу."
        if request.path.startswith("/api/"):
            return jsonify(error={"code": 409, "message": message}), 409
        return render_template("error.html", message=message, code=409), 409

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
