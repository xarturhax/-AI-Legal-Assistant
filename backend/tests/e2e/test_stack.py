import re

import pytest

pytestmark = pytest.mark.live_stack


def test_real_flask_llm_to_ostis(app):
    # Тестовая SQLite/сессия, но настоящие WebSocket и Ollama без подмен.
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    page = client.get("/requests")
    token = re.search(r'name="csrf-token" content="([^"]+)"', page.data.decode())[1]
    response = client.post(
        "/api/legal/query",
        json={"query": "Расскажите, что такое арендное жилье", "mode": "llm"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200, response.json
    result = response.json
    assert result["runtime"]["ostis_connected"]
    assert result["runtime"]["llm_used"]
    assert result["runtime"]["mock"] is False
    assert result["answer"]["status"] == "grounded"
    assert any(m["sc_identifier"] == "concept_rental_housing_belarus" for m in result["matches"])


def test_directory_llm_searches_ostis_templates(app):
    client = app.test_client()
    response = client.get(
        "/api/legal/concepts",
        query_string={
            "term": "Как называется жильё, которое государство сдаёт гражданам в аренду?",
            "mode": "llm",
        },
    )
    assert response.status_code == 200, response.json
    assert response.json["runtime"]["llm_used"] and not response.json["runtime"]["mock"]
    assert any(m["id"] == "concept_rental_housing_belarus" for m in response.json["matches"])
    assert {event["method"] for event in response.json["trace"]} == {
        "sc_template_search",
        "source_relevance",
    }
