import pytest

pytestmark = pytest.mark.live_stack


@pytest.mark.parametrize(
    ("query", "code", "articles", "fragment"),
    [
        pytest.param(
            "Хочу уволиться. У меня контракт ещё на полгода. Могу уйти раньше?",
            "hk9900296",
            [40, 41],
            "уважительных причинах",
            id="resignation",
        ),
        pytest.param(
            "Меня уволили и не заплатили. Когда работодатель должен рассчитаться?",
            "hk9900296",
            [77, 179],
            "дня увольнения",
            id="dismissal-pay",
        ),
        pytest.param(
            "Могу ли я разделить отпуск на несколько коротких частей?",
            "hk9900296",
            [155, 174],
            "14 календарных дней",
            id="annual-leave",
        ),
        pytest.param(
            "Второй родитель перестал помогать. Как взыскать алименты на ребёнка?",
            "hk9900278",
            [91, 92],
            "25 процентов",
            id="child-support",
        ),
        pytest.param(
            "Можно ли развестись через ЗАГС, если есть общий несовершеннолетний ребёнок?",
            "hk9900278",
            [36, 351],
            "нет общих несовершеннолетних детей",
            id="divorce",
        ),
        pytest.param(
            "Бывшая супруга не даёт видеться с ребёнком. Какие правила общения?",
            "hk9900278",
            [77],
            "право общаться с ребёнком",
            id="child-contact",
        ),
        pytest.param(
            "Купил куртку, не подошёл размер. Я её не носил. Можно вернуть?",
            "h10200090",
            [28],
            "14 дней с передачи",
            id="undamaged-return",
        ),
        pytest.param(
            "Гарантийный ремонт затянулся. Какой срок у мастерской?",
            "h10200090",
            [22],
            "14 днями",
            id="warranty-repair",
        ),
        pytest.param(
            "Потерял диплом. Можно ли получить документ повторно?",
            "hk1100243",
            [95],
            "дубликат с той же силой",
            id="diploma",
        ),
        pytest.param(
            "Собственник предлагает сдать квартиру без договора. Как оформляется найм?",
            "hk1200428",
            [51, 53],
            "с даты регистрации",
            id="lease-registration",
        ),
        pytest.param(
            "У меня пропал оригинал аттестата. Как получить новый документ об окончании школы?",
            "hk1100243",
            [95],
            "дубликат с той же силой",
            id="diploma-paraphrase",
        ),
    ],
)
def test_case_answer_links_to_real_article_and_text(app, query, code, articles, fragment):
    client = app.test_client()
    response = client.post("/api/legal/query", json={"query": query, "mode": "llm"})
    assert response.status_code == 200, response.json
    result = response.json
    assert result["runtime"]["llm_used"] and not result["runtime"]["mock"]
    assert result["answer"]["status"] == "grounded"
    assert fragment in result["answer"]["text"], (result["search_terms"], result["trace"])
    provisions = {
        entry["id"]: entry for case in result["answer"]["guidance"] for entry in case["provisions"]
    }
    assert set(provisions) == {f"by_act_{code}_article_{number}" for number in articles}
    for identifier, entry in provisions.items():
        source = client.get(f"/api/legal/sources/{identifier}")
        assert source.status_code == 200
        assert entry["text_link"] > 0
        assert source.json["official_url"] == entry["official_url"]
        assert source.json["source_citation"] == entry["citation"]
        assert source.json["text"]
        if source.json["text_kind"] == "summary":
            assert entry["text_link"] in source.json["provenance"]["text_links"]
            assert source.json["text"] == entry["text"]
