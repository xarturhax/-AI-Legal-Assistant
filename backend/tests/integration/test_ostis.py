import os

import pytest
from app.ostis.client import OstisClient

pytestmark = pytest.mark.live_ostis


def test_real_kb_read():
    client = OstisClient(os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json"))
    assert client.ready()["kb_loaded"]
    result = client.search(["арендное жилье"], use_agent=False)
    source = next(
        m for m in result["matches"] if m["sc_identifier"] == "concept_rental_housing_belarus"
    )
    assert source["excerpt"] and source["provenance"]["text_links"]
    assert client.source(source["id"])["text"]
    vocabulary = client.vocabulary()
    assert vocabulary["concept_count"] > 0
    assert "арендное жилье" in vocabulary["terms"]
    assert {
        "работники, находящиеся под угрозой увольнения,",
        "свободное рабочее место (вакансия)",
        "государственная поддержка при строительстве (реконструкции) "
        "или приобретении жилых помещений",
    } <= set(vocabulary["terms"])


def test_article_file_reference_and_readable_concept(app):
    http = app.test_client()
    article_id = "by_act_hk1200428_article_1"
    article = http.get(f"/api/legal/sources/{article_id}")
    assert article.status_code == 200, article.json
    assert article.json["text_status"] == "unavailable_file_reference"
    assert article.json["sc_identifier"] == article_id
    assert article.json["text"] == article.json["excerpt"] == ""
    assert article.json["source_exists"] and article.json["provenance"]["text_links"]
    assert article.json["source_relevant"] is article.json["legal_applicability"] is None
    page = http.get(f"/article/{article_id}")
    assert page.status_code == 200
    assert "Текст не извлечён из SC-памяти." in page.get_data(as_text=True)
    assert "/tmp/" not in page.get_data(as_text=True)
    concept = http.get("/api/legal/sources/concept_rental_housing_belarus")
    assert concept.status_code == 200
    assert concept.json["text_status"] == "available" and concept.json["text"]


def test_exact_title_precedes_related_agent_sources():
    client = OstisClient(os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json"))
    result = client.search(["воспитание"])
    assert "concept_education_belarus" in [m["sc_identifier"] for m in result["matches"][:2]]
    assert any(
        event["method"] == "sc_template_search" and event["status"] == "matched"
        for event in result["trace"]
    )


def test_existing_agent_single_title_link():
    client = OstisClient(os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json"))
    probe = client.call("single_match_probe", terms=["арендное жилье", "абитуриент", "занятость"])
    if probe is None:
        pytest.skip("В текущей KB не найден термин с ровно одной исходной title-ссылкой")
    assert probe["title_link_count"] == 1
    assert probe["links_before_action"] >= 1
    assert probe["links_after_action"] >= probe["links_before_action"] + 1
    assert probe["trace"]["status"] == "finished"
    if probe["result_nodes_count"] == 0 and not probe["matches"]:
        pytest.xfail(
            "Известное ограничение upstream action_user_request: завершение без источников; "
            f"term={probe['term']}, result_nodes={probe['result_nodes_count']}, "
            f"diagnostics={probe['diagnostics']}. "
            "Fallback к настоящей KB проверяется отдельным тестом."
        )
    assert probe["matches"], "Агент не вернул источники; проверить singular/plural и шаблоны"


def test_action_search_uses_real_sources_with_explicit_fallback():
    client = OstisClient(os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json"))
    result = client.search(["арендное жилье"])
    source = next(
        item
        for item in result["matches"]
        if item["sc_identifier"] == "concept_rental_housing_belarus"
    )
    assert source["excerpt"] and source["provenance"]["text_links"]
    assert client.source(source["id"])["text"]
    action = next(event for event in result["trace"] if event["method"] == "action_user_request")
    assert action["status"] == "finished"
    if action["source_count"] == 0:
        assert any(
            event["method"] == "sc_template_search"
            and event["status"] == "matched"
            and event.get("reason") == "agent_no_sources"
            for event in result["trace"]
        )
