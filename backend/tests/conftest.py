import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from app import create_app


def pytest_configure(config):
    # У разных Windows-сеансов может совпадать имя пользователя, но отличаться ACL.
    # Не переиспользуем общий pytest-of-user, созданный другим сеансом.
    if config.option.basetemp is None:
        temporary = TemporaryDirectory(prefix="jurisprudencia-pytest-", ignore_cleanup_errors=True)
        config.add_cleanup(temporary.cleanup)
        config.option.basetemp = str(Path(temporary.name) / "cases")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_INSTANCE_PATH", str(tmp_path / "instance"))
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-" + "x" * 40,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "DEV_LOCAL_MAIL": True,
            "DEV_MAIL_DIR": str(tmp_path / "dev-mail"),
            "GMAIL_OAUTH_FILE": "",
            "SMTP_HOST": "",
        }
    )
    from app.db.migrate import upgrade

    with app.app_context():
        upgrade()
    return app


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "live_ostis" in item.keywords and os.getenv("RUN_LIVE_OSTIS") != "1":
            item.add_marker(
                pytest.mark.skip(
                    reason="SKIPPED: RUN_LIVE_OSTIS=1 не задан; настоящий OSTIS обязателен"
                )
            )
        if "live_stack" in item.keywords and os.getenv("RUN_LIVE_STACK") != "1":
            item.add_marker(
                pytest.mark.skip(
                    reason="SKIPPED: RUN_LIVE_STACK=1 не задан; нужны настоящие OSTIS и Ollama"
                )
            )
