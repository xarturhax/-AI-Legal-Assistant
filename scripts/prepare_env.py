"""Подготовка локального секрета без вывода его значения."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_environment():
    target = ROOT / ".env"
    if not target.exists():
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        target.write_text(
            text.replace("CHANGE_ME_LOCALLY", secrets.token_urlsafe(48)), encoding="utf-8"
        )
        try:
            target.chmod(0o600)
        except OSError:
            pass


if __name__ == "__main__":
    prepare_environment()
    print("Локальный .env подготовлен. Значение секрета не выводится.")
