import json
import logging
import sys
import time

from sc_client import client

from app.ostis.memory import Memory


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    request = json.load(sys.stdin)
    response = {"request_id": request["request_id"], "ok": False}
    try:
        client.set_error_handler(
            lambda error: logging.warning("SC connection error: %s", type(error).__name__)
        )
        client.set_reconnect_handler(reconnect_retries=0, post_reconnect_handler=lambda: None)
        client.connect(request["url"])
        deadline = time.monotonic() + 3
        while not client.is_connected() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not client.is_connected():
            raise ConnectionError("Нет соединения с sc-server")
        memory = Memory()
        operation, arguments = request["operation"], request["arguments"]
        if operation == "ready":
            # Проверяется загруженная KB и чтение содержимого, не только WebSocket.
            source = memory.resolve_source("concept_applicant_belarus")
            if not source or not source["excerpt"]:
                raise RuntimeError("Юридическая KB не готова")
            result = {"connected": True, "kb_loaded": True, "probe": source["sc_identifier"]}
        elif operation == "search":
            result = memory.lookup(**arguments)
        elif operation == "vocabulary":
            result = memory.vocabulary()
        elif operation == "source":
            result = memory.resolve_source(arguments["identifier"])
        elif operation == "question":
            result = memory.question(**arguments)
        elif operation == "single_match_probe":
            result = memory.single_match_probe(arguments["terms"])
        else:
            raise ValueError("Неизвестная операция")
        response.update(ok=True, result=result)
    except Exception as error:
        logging.warning("SC operation failed: %s", type(error).__name__)
        response["error"] = type(error).__name__
    finally:
        client.disconnect()
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
