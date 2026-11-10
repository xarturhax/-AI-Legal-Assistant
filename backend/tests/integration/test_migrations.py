"""Настоящий CLI и SQLite: новый файл и повторный запуск с данными пользователя."""

import os
import secrets
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_db_upgrade_cli_preserves_existing_data(tmp_path):
    database_path = tmp_path / "app.sqlite3"
    environment = {
        **os.environ,
        "SECRET_KEY": secrets.token_hex(32),
        "DATABASE_URL": "sqlite:///" + database_path.as_posix(),
        "APP_INSTANCE_PATH": str(tmp_path / "instance"),
        "DOCUMENT_CATALOG": str(tmp_path / "documents/catalog.json"),
        "DEV_MAIL_DIR": str(tmp_path / "dev-mail"),
        "OSTIS_WS_URL": "ws://127.0.0.1:8090/ws_json",
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    }

    def upgrade():
        result = subprocess.run(
            [sys.executable, "-m", "app", "db-upgrade"],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")

    upgrade()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "migration-test@example.invalid", "test-only-unusable", "2026-01-01", "user", 1, 1),
        )
        connection.execute(
            "INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)",
            (1, 1, None, "Проверка сохранения заметки", "2026-01-01", "2026-01-01"),
        )
    upgrade()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "003_recommendations",
        )
        assert connection.execute("SELECT email FROM users").fetchall() == [
            ("migration-test@example.invalid",)
        ]
        assert connection.execute("SELECT text FROM notes").fetchall() == [
            ("Проверка сохранения заметки",)
        ]
