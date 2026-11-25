import os
from pathlib import Path
from urllib.parse import urlsplit


def local_service_url(value, scheme, hosts):
    parsed = urlsplit(value)
    if (
        parsed.scheme != scheme
        or parsed.hostname not in hosts
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Разрешён только локальный адрес сервиса без учётных данных.")
    return value.rstrip("/")


def configuration():
    application_root = Path(__file__).resolve().parent.parent
    instance_root = Path(os.getenv("APP_INSTANCE_PATH", str(application_root / "instance")))
    # В checkout пакет находится в backend/app, в Docker — в /app/app.
    catalog_default = application_root / "documents/catalog.json"
    if application_root.name == "backend":
        catalog_default = application_root.parent / "data/documents/catalog.json"
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "SQLALCHEMY_DATABASE_URI": os.getenv("DATABASE_URL", "sqlite:///app.sqlite3"),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "OSTIS_WS_URL": os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json"),
        "OSTIS_TIMEOUT_SECONDS": float(os.getenv("OSTIS_TIMEOUT_SECONDS", "40")),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct"),
        "OLLAMA_TIMEOUT_SECONDS": float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
        "MAX_QUERY_LENGTH": int(os.getenv("MAX_QUERY_LENGTH", "1500")),
        "LEGAL_QUERY_DEFAULT_MODE": os.getenv("LEGAL_QUERY_DEFAULT_MODE", "baseline"),
        "DEV_LOCAL_MAIL": os.getenv("DEV_LOCAL_MAIL", "0") == "1",
        "DEV_MAIL_DIR": os.getenv("DEV_MAIL_DIR", str(instance_root / "dev-mail")),
        "SMTP_HOST": os.getenv("SMTP_HOST", "").strip(),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME", "").strip(),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
        "GMAIL_OAUTH_FILE": os.getenv("GMAIL_OAUTH_FILE", ""),
        "GMAIL_SENDER": os.getenv("GMAIL_SENDER", "").strip(),
        "APP_ENV": os.getenv("APP_ENV", "development"),
        "DOCUMENT_CATALOG": os.getenv("DOCUMENT_CATALOG", str(catalog_default)),
        "NEWS_RSS_URLS": os.getenv("NEWS_RSS_URLS", ""),
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "WTF_CSRF_TIME_LIMIT": 3600,
    }
