import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.errors import ServiceError
from app.ostis.client import OstisClient


@pytest.mark.mock
def test_parallel_requests_do_not_mix_results(monkeypatch):
    def respond(*args, **kwargs):
        payload = json.loads(kwargs["input"])
        time.sleep(0.03)
        output = {
            "request_id": payload["request_id"],
            "ok": True,
            "result": {"test_value": payload["arguments"]["value"]},
        }
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(output))

    monkeypatch.setattr(subprocess, "run", respond)
    client = OstisClient("ws://localhost:8090/ws_json")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda value: client.call("test-fixture", value=value), ["A", "B"]))
    assert results == [{"test_value": "A"}, {"test_value": "B"}]


@pytest.mark.mock
def test_wrong_correlation_id_is_rejected(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a, 0, stdout=json.dumps({"request_id": "wrong", "ok": True, "result": {}})
        ),
    )
    with pytest.raises(ServiceError) as caught:
        OstisClient("ws://localhost:8090/ws_json").ready()
    assert caught.value.code == "ostis_protocol"


def test_empty_oversized_invalid_modes(app):
    client = app.test_client()
    for body in (
        None,
        [],
        {"query": " "},
        {"query": "x" * 1501},
        {"query": "тест", "mode": "cloud"},
    ):
        assert client.post("/api/legal/query", json=body).status_code == 400


def test_auth_rate_limit(app):
    app.config["TEST_RATE_LIMIT"] = True
    client = app.test_client()
    statuses = [
        client.post("/auth", data={"email": "not-an-email", "password": "x"}).status_code
        for _ in range(13)
    ]
    assert statuses[-1] == 429


def test_baseline_keeps_prepositions_and_long_terms():
    from app.legal.search_baseline import extract_terms

    assert extract_terms("Что такое грант на обучение?")[0] == "грант на обучение"
    title = "органы государственной службы занятости населения"
    assert title in extract_terms(f"Что такое {title}?")
