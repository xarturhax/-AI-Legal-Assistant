from unittest.mock import Mock

import pytest
from app.errors import ServiceError
from app.legal.relevance import filter_sources, literal_terms
from app.legal.search_baseline import is_definition_question
from app.llm.schemas import RelevantSource


def test_literal_terms_use_word_boundaries_and_allow_yo():
    assert literal_terms(
        "У меня арендное жильё, живу с ребёнком. Безработица.",
        ["работа", "арендное жилье", "ребёнок", "выпускник"],
    ) == ["арендное жилье"]


def test_definition_question_is_detected_independently_of_model_intent():
    assert is_definition_question("Я поступаю в вуз. Как называют поступающего?")
    assert is_definition_question("Расскажите, что такое арендное жильё")
    assert not is_definition_question("Можно ли меня выселить из арендного жилья?")


@pytest.mark.mock
def test_relevance_accepts_a_paraphrase_and_rejects_unverified_sources():
    rental = {"id": "rental", "title": "арендное жилье", "excerpt": "Определение жилья"}
    applicant = {"id": "applicant", "title": "абитуриент", "excerpt": "Лицо поступает в вуз"}
    graduate = {"id": "graduate", "title": "выпускник", "excerpt": "Лицо завершило обучение"}
    result = {"matches": [rental, applicant, graduate], "trace": []}
    interpreter = Mock()
    interpreter.relevant_sources.return_value = [
        RelevantSource(number=1, query_quote="поступаю в вуз"),
        RelevantSource(number=2, query_quote="окончил вуз"),
        RelevantSource(number=3, query_quote="в вуз"),
    ]
    query = "У меня арендное жильё. Я поступаю в вуз."
    assert filter_sources(query, result, interpreter, direct_terms=["арендное жилье"]) is None
    interpreter.relevant_sources.assert_called_once_with(query, [applicant, graduate])
    assert result["matches"] == [rental, applicant]
    assert result["trace"] == [
        {
            "method": "source_relevance",
            "status": "checked",
            "accepted_checked_ids": ["applicant"],
            "excluded_ids": ["graduate"],
        }
    ]


@pytest.mark.mock
def test_relevance_timeout_keeps_only_explicit_concepts():
    rental = {"id": "rental", "title": "арендное жилье", "excerpt": "Определение жилья"}
    other = {"id": "other", "title": "помещение", "excerpt": "Другое определение"}
    result = {"matches": [rental, other], "trace": []}
    interpreter = Mock()
    interpreter.relevant_sources.side_effect = ServiceError("Таймаут", "llm_timeout")
    assert (
        filter_sources(
            "Что такое арендное жильё?", result, interpreter, direct_terms=["арендное жилье"]
        )
        == "llm_timeout"
    )
    assert result["matches"] == [rental]
    assert result["trace"][0]["status"] == "unavailable"
