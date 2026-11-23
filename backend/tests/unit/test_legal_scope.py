import pytest
from app.legal.service import LegalService


@pytest.mark.mock
@pytest.mark.parametrize("mode", ["baseline", "llm"])
def test_maritime_registration_does_not_borrow_unrelated_vocabulary(mode):
    class Catalogue:
        def ready(self):
            return {"kb_loaded": True}

        def vocabulary(self):
            return {"terms": ["государственная регистрация", "международный стандарт"]}

        def search(self, terms):
            pytest.fail("Unrelated matches must not be searched")

    result = LegalService(Catalogue()).query(
        "Как зарегистрировать морское судно под флагом Панамы?", mode
    )
    assert result["matches"] == result["search_terms"] == []
    assert result["answer"]["status"] == "no_evidence"
    assert result["situation"]["needs_clarification"]
    assert result["trace"][0]["reason"] == "outside_confirmed_scope"
    assert result["runtime"]["llm_used"] is False


@pytest.mark.mock
@pytest.mark.parametrize("term", ["регистрация судна", "государственная регистрация"])
def test_scope_guard_allows_confirmed_maritime_topic_and_ordinary_definitions(term):
    class Catalogue:
        def vocabulary(self):
            return {"terms": ["регистрация судна", "государственная регистрация"]}

        def search(self, terms):
            assert terms[0] == term
            return {
                "matches": [
                    {"id": "direct", "title": term, "excerpt": "Извлечённый текст"},
                    {"id": "related", "title": "Связанный материал", "excerpt": "Другой текст"},
                ],
                "trace": [],
            }

    result = LegalService(Catalogue()).query(f"Что такое {term}?", "baseline")
    assert [match["source_exists"] for match in result["matches"]] == [True, True]
    assert [match["source_relevant"] for match in result["matches"]] == [True, None]
    assert all(match["legal_applicability"] is None for match in result["matches"])
