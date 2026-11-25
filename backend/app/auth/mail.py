import json
import secrets
import smtplib
import ssl
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formataddr
from pathlib import Path

import httpx
from flask import current_app


def mail_mode(config):
    if config["GMAIL_OAUTH_FILE"]:
        return (
            "gmail"
            if config["GMAIL_SENDER"] and Path(config["GMAIL_OAUTH_FILE"]).is_file()
            else None
        )
    if config["SMTP_HOST"]:
        return "smtp" if config["SMTP_USERNAME"] and config["SMTP_PASSWORD"] else None
    return "local" if config["DEV_LOCAL_MAIL"] else None


def deliver_code(recipient, purpose, token):
    config = current_app.config
    mode = mail_mode(config)
    if mode == "local":
        directory = Path(config["DEV_MAIL_DIR"])
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (secrets.token_hex(12) + ".txt")
        with path.open("x", encoding="utf-8") as output:
            output.write(
                f"ЛОКАЛЬНЫЙ DEV-РЕЖИМ: письмо не отправлялось.\nemail: {recipient}\n"
                f"purpose: {purpose}\nКод: {token}\nСрок: 15 минут.\n"
            )
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return
    if mode is None:
        raise OSError("Mail delivery is not configured")

    action = "подтверждения аккаунта" if purpose == "verify" else "восстановления доступа"
    message = EmailMessage()
    sender = config["GMAIL_SENDER"] if mode == "gmail" else config["SMTP_USERNAME"]
    message["From"] = formataddr(("Themis", sender))
    message["To"] = recipient
    message["Subject"] = f"Themis — код {action}"
    message.set_content(f"Код {action}: {token}\n\nКод действует 15 минут.\n")
    if mode == "gmail":
        send_with_gmail(message, Path(config["GMAIL_OAUTH_FILE"]))
        return
    with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"], timeout=10) as client:
        client.starttls(context=ssl.create_default_context())
        client.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
        client.send_message(message)


def send_with_gmail(message, credential_file):
    try:
        credentials = json.loads(credential_file.read_text(encoding="utf-8"))
        grant = {key: credentials[key] for key in ("client_id", "client_secret", "refresh_token")}
        with httpx.Client(timeout=10, trust_env=False) as client:
            token = client.post(
                "https://oauth2.googleapis.com/token",
                data={**grant, "grant_type": "refresh_token"},
            )
            token.raise_for_status()
            access_token = token.json()["access_token"]
            reply = client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": urlsafe_b64encode(message.as_bytes(policy=SMTP)).decode("ascii")},
            )
            reply.raise_for_status()
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise OSError("Gmail API delivery failed") from None
