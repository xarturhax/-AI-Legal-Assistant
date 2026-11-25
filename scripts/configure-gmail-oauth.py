import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = "https://www.googleapis.com/auth/gmail.send"


def main():
    parser = argparse.ArgumentParser(description="Настроить отправку кодов Themis через Gmail API.")
    parser.add_argument("client_json", type=Path, help="Скачанный OAuth Client для Desktop app")
    args = parser.parse_args()
    env_file = ROOT / ".env"
    if not env_file.is_file():
        parser.error("Сначала выполните setup.bat.")
    try:
        client = json.loads(args.client_json.read_text(encoding="utf-8-sig"))
        if not isinstance(client.get("installed"), dict):
            raise ValueError
    except (OSError, ValueError, AttributeError):
        parser.error("Укажите скачанный JSON OAuth-клиента типа Desktop app.")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from oauthlib.oauth2 import OAuth2Error
    except ImportError:
        parser.error("Установите пакет командой python -m pip install google-auth-oauthlib==1.5.0.")

    sender = input("Адрес Gmail-ящика Themis: ").strip().lower()
    if not re.fullmatch(r"[a-z0-9.]+@(?:gmail\.com|googlemail\.com)", sender):
        parser.error("Укажите полный адрес Gmail-ящика отправителя.")

    print("В браузере выберите ящик Themis и разрешите отправку писем.", flush=True)
    try:
        flow = InstalledAppFlow.from_client_config(client, [SCOPE], autogenerate_code_verifier=True)
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            prompt="consent",
            login_hint=sender,
            authorization_prompt_message="Откройте ссылку, если браузер не запустился:\n{url}",
            success_message="Google подтвердил доступ. Вернитесь в PowerShell.",
            timeout_seconds=300,
        )
    except (OSError, ValueError, OAuth2Error, AttributeError) as error:
        parser.error(f"Google не завершил авторизацию ({type(error).__name__}).")
    if not credentials.refresh_token:
        parser.error("Google не выдал токен обновления. Повторите авторизацию.")

    directory = ROOT / "data" / "runtime" / "mail-credentials"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "gmail-oauth.json"
    token = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(token), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)

    settings = {
        "GMAIL_OAUTH_FILE": "/run/themis-mail/gmail-oauth.json",
        "GMAIL_SENDER": sender,
        "DEV_LOCAL_MAIL": "0",
    }
    lines = [
        line
        for line in env_file.read_text(encoding="utf-8-sig").splitlines()
        if line.split("=", 1)[0].strip() not in settings
    ]
    lines.extend(f"{key}={value}" for key, value in settings.items())
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Авторизация сохранена локально. Теперь пересоздайте контейнер app.")


if __name__ == "__main__":
    main()
