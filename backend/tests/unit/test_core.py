import subprocess

import pytest
from app.config import local_service_url
from app.errors import ServiceError
from app.legal.contracts import QueryInput
from app.legal.search_baseline import extract_terms
from app.ostis.client import OstisClient
from pydantic import ValidationError


def test_query_contract():
    for value in (
        {"query": " "},
        {"query": "x" * 1501},
        {"query": "тест", "mode": "cloud"},
        {"query": "тест", "injected": True},
    ):
        with pytest.raises(ValidationError):
            QueryInput.model_validate(value)
    assert "арендное жилье" in extract_terms("Что такое арендное жилье?")


def test_local_only():
    with pytest.raises(ValueError):
        local_service_url("https://external.example/api", "http", {"localhost"})


def test_home_and_liveness(app):
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/requests").status_code == 200
    assert client.get("/directory").status_code == 200
    assert client.get("/health/live").json["mock"] is False


@pytest.mark.mock
def test_timeout_is_bounded(monkeypatch):
    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 1)

    monkeypatch.setattr(subprocess, "run", hang)
    with pytest.raises(ServiceError) as caught:
        OstisClient("ws://localhost:8090/ws_json", 1).ready()
    assert caught.value.code == "ostis_timeout"


@pytest.mark.mock
def test_no_evidence_when_ostis_unavailable(app, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ServiceError("OSTIS недоступен", "ostis_unavailable")

    monkeypatch.setattr(app.extensions["legal_service"].ostis, "search", unavailable)
    result = app.test_client().post("/api/legal/query", json={"query": "арендное жилье"})
    assert result.status_code == 503
    assert "answer" not in result.json
