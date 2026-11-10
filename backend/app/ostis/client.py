import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.config import local_service_url
from app.errors import ServiceError

_operation_lock = Lock()
logger = logging.getLogger(__name__)


class OstisClient:
    def __init__(self, url, timeout=40):
        self.url = local_service_url(
            url, "ws", {"machine", "localhost", "127.0.0.1", "host.docker.internal"}
        )
        self.timeout = timeout

    def call(self, operation, **arguments):
        request_id = str(uuid4())
        if not _operation_lock.acquire(timeout=1):
            raise ServiceError("OSTIS обрабатывает другой запрос. Повторите позже.", "ostis_busy")
        try:
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8"
            payload = {
                "url": self.url,
                "operation": operation,
                "arguments": arguments,
                "request_id": request_id,
            }
            result = subprocess.run(
                [sys.executable, "-m", "app.ostis.worker"],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                cwd=Path(__file__).resolve().parents[2],
                timeout=self.timeout,
            )
            if result.returncode:
                logger.warning(
                    "OSTIS worker failed request_id=%s returncode=%s", request_id, result.returncode
                )
                raise ServiceError(
                    "Не удалось прочитать OSTIS. Проверьте sc-machine и загруженную КБ.",
                    "ostis_unavailable",
                )
            response = json.loads(result.stdout)
            if response.get("request_id") != request_id:
                raise ServiceError("Нарушена корреляция ответа OSTIS.", "ostis_protocol")
            if not response.get("ok"):
                if response.get("error") == "TimeoutError":
                    raise ServiceError("Истекло ожидание действия OSTIS.", "ostis_timeout", 504)
                raise ServiceError(
                    "OSTIS не выполнил запрос. Проверьте состояние КБ.", "ostis_unavailable"
                )
            return response["result"]
        except subprocess.TimeoutExpired as error:
            logger.warning("OSTIS timeout request_id=%s", request_id)
            raise ServiceError("Истекло время ожидания OSTIS.", "ostis_timeout", 504) from error
        except (ValueError, KeyError, OSError) as error:
            raise ServiceError("Некорректный ответ службы OSTIS.", "ostis_protocol") from error
        finally:
            _operation_lock.release()

    def ready(self):
        return self.call("ready")

    def search(self, terms, use_agent=True):
        return self.call("search", terms=terms[:16], use_agent=use_agent)

    def vocabulary(self):
        return self.call("vocabulary")

    def source(self, identifier):
        return self.call("source", identifier=identifier)
