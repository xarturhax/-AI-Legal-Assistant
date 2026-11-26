import pytest

pytestmark = pytest.mark.live_stack


@pytest.mark.parametrize(
    ("query", "expected", "irrelevant"),
    [
        (
            "У меня арендное жильё, живу с ребёнком. Можно ли меня выселить?",
            "concept_rental_housing_belarus",
            {"concept_graduate_belarus", "concept_underage_belarus"},
        ),
        (
            "Я поступаю в вуз. Как называют поступающего?",
            "concept_applicant_belarus",
            {"concept_graduate_belarus"},
        ),
        (
            "Как называют человека, который окончил обучение?",
            "concept_graduate_belarus",
            {"concept_training_belarus", "concept_applicant_belarus"},
        ),
    ],
    ids=["short-eviction", "applicant", "graduate"],
)
def test_relevance_for_literal_and_descriptive_questions(app, query, expected, irrelevant):
    response = app.test_client().post("/api/legal/query", json={"query": query, "mode": "llm"})
    assert response.status_code == 200, response.json
    result = response.json
    assert result["runtime"]["llm_used"] and not result["runtime"]["mock"]
    assert result["answer"]["status"] == "grounded"
    assert expected in {source["id"] for source in result["matches"]}
    assert not irrelevant.intersection(source["id"] for source in result["matches"])
    if expected == "concept_rental_housing_belarus":
        assert any(case["checks"] for case in result["answer"]["guidance"])
        assert any(item["source_ids"] for item in result["situation"]["items"])
    else:
        assert any(event["method"] == "source_relevance" for event in result["trace"])


def test_unrelated_question_does_not_return_legal_sources(app):
    response = app.test_client().post(
        "/api/legal/query",
        json={"query": "Как сварить гречку в мультиварке?", "mode": "llm"},
    )
    assert response.status_code == 200, response.json
    result = response.json
    assert result["runtime"]["llm_used"] and not result["runtime"]["mock"]
    assert result["answer"]["status"] == "no_evidence"
    assert not result["matches"]


@pytest.mark.parametrize(
    ("query", "expected_articles", "answer_fragment"),
    [
        (
            "У меня арендное жильё, живу с ребёнком. Можно ли меня выселить? "
            "Длительность аренды: 5 лет. У арендодателя нет присин меня выселить. "
            "Арендодателем является моя подруга. Не знаю насчёт условий аренды. "
            "У меня есть договор аренды.",
            {f"by_act_hk1200428_article_{n}" for n in (61, 62, 64)},
            "судебный порядок выселения",
        ),
        (
            "Купил телефон, через неделю он перестал включаться, "
            "а продавец отказывается возвращать деньги?",
            {"by_act_h10200090_article_20"},
            "30 дней",
        ),
        (
            "Хозяйка требует освободить съёмную квартиру, хотя договор ещё действует. "
            "Может ли она заставить меня уйти?",
            {f"by_act_hk1200428_article_{n}" for n in (61, 62, 64)},
            "судебный порядок выселения",
        ),
        (
            "Новый смартфон сломался спустя несколько дней после покупки. "
            "Магазин не хочет возвращать оплату. Что делать?",
            {"by_act_h10200090_article_20"},
            "30 дней",
        ),
    ],
    ids=["eviction", "phone", "eviction-variant", "phone-variant"],
)
def test_conversational_cases_give_ostis_provisions(app, query, expected_articles, answer_fragment):
    client = app.test_client()
    response = client.post("/api/legal/query", json={"query": query, "mode": "llm"})
    assert response.status_code == 200, response.json
    result = response.json
    assert result["runtime"]["llm_used"] and not result["runtime"]["mock"]
    assert result["answer"]["status"] == "grounded"
    assert answer_fragment in result["answer"]["text"]
    assert result["situation"]["assessment_status"] == "not_performed"
    provisions = {
        provision["id"]: provision
        for case in result["answer"]["guidance"]
        for provision in case["provisions"]
    }
    assert set(provisions) == expected_articles
    for identifier, provision in provisions.items():
        response = client.get(f"/api/legal/sources/{identifier}")
        assert response.status_code == 200
        assert provision["official_url"] == response.json["official_url"]
        assert provision["citation"] == response.json["source_citation"]
        assert provision["text_link"] > 0


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
    if result["answer"]["guidance"]:
        for case in result["answer"]["guidance"]:
            for provision in case["provisions"]:
                assert provision["text"] in result["answer"]["text"]
                assert service.ostis.source(provision["id"])["source_citation"]
    elif result["answer"]["status"] == "grounded":
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
