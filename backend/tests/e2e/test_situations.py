import pytest

pytestmark = pytest.mark.live_stack


@pytest.mark.parametrize(
    "query",
    [
        "Я абитуриент, подаю документы в два вуза. Могут ли мне отказать?",
        "У меня арендное жилье, живу с ребёнком. Можно ли меня выселить?",
        "Подписан трудовой договор, работодатель требует уйти завтра. Что делать?",
    ],
)
def test_situation_returns_only_kb_excerpts(app, query):
    service = app.extensions["legal_service"]
    result = service.query(query, "llm")
    situation = result["situation"]
    assert situation["assessment_status"] == "not_performed"
    interpretation = result["interpretation"]
    assert all(
        e["original_text"].casefold() in query.casefold() for e in interpretation["entities"]
    )
    assert all(
        f["value"].casefold() in query.casefold()
        for f in interpretation["facts"]
        if f["present_in_user_text"]
    )
    if result["answer"]["status"] == "grounded":
        evidence = [source for source in result["matches"] if source.get("excerpt")]
        assert result["answer"]["text"] == "\n\n".join(s["excerpt"] for s in evidence[:4])
    for source in result["matches"]:
        actual = service.ostis.source(source["id"])
        assert actual and source["excerpt"] in actual["text"]
    source_ids = {source["id"] for source in result["matches"]}
    for item in situation["items"]:
        assert set(item["source_ids"]) <= source_ids


@pytest.mark.parametrize(
    "query",
    [
        "Помогите разобраться в моей ситуации",
        "Что мне делать?",
        "У меня сложная проблема, подскажите, как поступить",
        "Скажите, как мне дальше действовать?",
    ],
)
def test_vague_request_asks_for_context_without_sources(app, query):
    response = app.test_client().post("/api/legal/query", json={"query": query, "mode": "llm"})
    assert response.status_code == 200, response.json
    result = response.json
    assert result["answer"]["status"] == "no_evidence"
    assert result["matches"] == result["search_terms"] == []
    assert result["situation"]["search_allowed"] is False
    assert result["situation"]["needs_clarification"]
    assert result["situation"]["clarification_questions"]
    assert not any(event["method"] == "action_user_request" for event in result["trace"])
    assert result["runtime"]["llm_used"] and result["runtime"]["ostis_connected"]
    assert result["runtime"]["mock"] is False


@pytest.mark.parametrize(
    "query",
    [
        "У меня арендное жилье. Условий договора не знаю, документов под рукой нет. С чего начать?",
        "Что такое арендное жилье?",
    ],
)
def test_partial_context_and_definition_keep_real_search(app, query):
    response = app.test_client().post("/api/legal/query", json={"query": query, "mode": "llm"})
    assert response.status_code == 200, response.json
    result = response.json
    assert result["situation"]["search_allowed"]
    assert result["answer"]["status"] == "grounded"
    source = next(
        m for m in result["matches"] if m["sc_identifier"] == "concept_rental_housing_belarus"
    )
    assert source["excerpt"]
    assert app.extensions["legal_service"].ostis.source(source["id"])["text"]
    assert any(event["method"] == "action_user_request" for event in result["trace"])


@pytest.mark.parametrize("mode", ["baseline", "llm"])
def test_maritime_registration_without_confirmed_kb_scope(app, mode):
    response = app.test_client().post(
        "/api/legal/query",
        json={
            "query": "Как зарегистрировать морское судно под флагом Панамы?",
            "mode": mode,
        },
    )
    assert response.status_code == 200, response.json
    result = response.json
    assert result["answer"]["status"] == "no_evidence"
    assert result["matches"] == result["search_terms"] == []
    assert result["situation"]["clarification_questions"]
    assert result["trace"][0]["reason"] == "outside_confirmed_scope"
    assert result["runtime"]["mock"] is False
    assert result["runtime"]["llm_used"] is False
