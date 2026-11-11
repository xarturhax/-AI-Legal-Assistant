"""Настоящие сетевые клиенты, отказ соединения на зарезервированном порту."""

import socket

import pytest
from app.llm.interpreter import OllamaInterpreter
from app.ostis.client import OstisClient


@pytest.mark.live_ostis
def test_baseline_with_unreachable_ollama(app):
    with socket.socket() as closed_service:
        closed_service.bind(("127.0.0.1", 0))
        port = closed_service.getsockname()[1]
        app.extensions["legal_service"].interpreter = OllamaInterpreter(
            f"http://127.0.0.1:{port}", app.config["OLLAMA_MODEL"], timeout=2
        )
        client = app.test_client()
        baseline = client.post(
            "/api/legal/query", json={"query": "Что такое арендное жилье?", "mode": "baseline"}
        )
        assert baseline.status_code == 200, baseline.json
        assert baseline.json["answer"]["status"] == "grounded"
        assert baseline.json["runtime"]["llm_used"] is False
        llm = client.post(
            "/api/legal/query", json={"query": "Что такое арендное жилье?", "mode": "llm"}
        )
        assert llm.status_code == 503
        assert llm.json["error"]["code"] == "llm_unavailable"
        assert "answer" not in llm.json


@pytest.mark.parametrize("mode", ["baseline", "llm"])
def test_no_legal_answer_with_unreachable_ostis(app, mode):
    with socket.socket() as closed_service:
        closed_service.bind(("127.0.0.1", 0))
        port = closed_service.getsockname()[1]
        app.extensions["legal_service"].ostis = OstisClient(
            f"ws://127.0.0.1:{port}/ws_json", timeout=8
        )
        response = app.test_client().post(
            "/api/legal/query", json={"query": "Могу ли я получить арендное жилье?", "mode": mode}
        )
        assert response.status_code in (503, 504), response.json
        assert response.json["error"]["code"].startswith("ostis_")
        assert "answer" not in response.json
