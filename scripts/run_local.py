"""Локальный Python-backend для разработки; реальные зависимости нужны для поиска."""

import os
import sys

from prepare_env import ROOT, prepare_environment


def main():
    prepare_environment()
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    runtime = ROOT / "data/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    # Docker-адреса преобразуются только для явно выбранного запуска на хосте.
    if os.environ.get("DATABASE_URL") == "sqlite:////app/data/app.sqlite3":
        os.environ["DATABASE_URL"] = "sqlite:///" + (runtime / "app.sqlite3").as_posix()
    os.environ["OSTIS_WS_URL"] = os.environ.get("OSTIS_WS_URL", "").replace(
        "ws://machine:", "ws://127.0.0.1:"
    )
    os.environ["OLLAMA_BASE_URL"] = os.environ.get("OLLAMA_BASE_URL", "").replace(
        "http://ollama:", "http://127.0.0.1:"
    )
    os.environ.setdefault("DEV_MAIL_DIR", str(runtime / "dev-mail"))
    os.environ.setdefault("APP_INSTANCE_PATH", str(runtime / "instance"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.__main__ import main as run

    run()


if __name__ == "__main__":
    main()
