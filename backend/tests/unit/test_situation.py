import pytest
from app.legal.service import LegalService
from app.legal.situation import link_situation, situation_plan
from app.llm.schemas import Interpretation


@pytest.mark.mock
def test_situation_uses_only_grounded_context_and_kb_terms():
    interpretation = Interpretation.model_validate(
        {
            "intent": "rights",
            "domain_hints": [],
            "search_terms": [],
            "entities": [
                {"name": "трудовой договор", "type": "document", "original_text": "договор"},
                {"name": "квартира", "type": "other", "original_text": "несуществующая цитата"},
            ],
            "facts": [
                {"key": "event", "value": "увольнение", "present_in_user_text": True},
                {"key": "country", "value": "Россия", "present_in_user_text": True},
                {"key": "guess", "value": "договор", "present_in_user_text": False},
            ],
            "missing_information": ["В какой стране произошли события?"],
            "needs_clarification": False,
        }
    )
    plan = situation_plan(
        interpretation,
        "У меня договор, грозит увольнение.",
        ["трудовой договор", "увольнение", "квартира"],
    )
    assert len(plan["items"]) == 2
    assert plan["needs_clarification"]
    assert plan["assessment_status"] == "not_performed"
    result = link_situation(plan, [{"id": "test-only", "matched_terms": ["увольнение"]}])
    assert result["items"][0]["status"] == "unlinked"
    assert result["items"][1]["source_ids"] == ["test-only"]


def test_context_does_not_link_substrings_as_different_concepts():
    interpretation = Interpretation.model_validate(
        {
            "intent": "other",
            "domain_hints": [],
            "search_terms": [],
            "entities": [],
            "facts": [{"key": "event", "value": "безработица", "present_in_user_text": True}],
            "missing_information": [],
            "needs_clarification": False,
        }
    )
    plan = situation_plan(interpretation, "безработица", ["работа"])
    assert plan["items"][0]["terms"] == []


@pytest.mark.mock
def test_context_extends_search_even_with_empty_model_search_terms():
    class ContextInterpreter:
        def interpret(self, query, vocabulary):
            return Interpretation.model_validate(
                {
                    "intent": "rights",
                    "domain_hints": [],
                    "search_terms": [],
                    "entities": [],
                    "facts": [
                        {"key": "event", "value": "арендное жилье", "present_in_user_text": True}
                    ],
                    "missing_information": ["Каковы условия договора?"],
                    "needs_clarification": True,
                }
            )

    class ContextOstis:
        def ready(self):
            return {"kb_loaded": True}

        def vocabulary(self):
            return {"terms": ["арендное жилье"]}

        def search(self, terms):
            assert terms == ["арендное жилье"]
            return {"matches": [], "trace": [], "unmatched_terms": terms}

    result = LegalService(ContextOstis(), ContextInterpreter()).query(
        "Мне предлагают арендное жилье, какие условия?", "llm"
    )
    assert result["answer"]["status"] == "no_evidence"
    assert result["situation"]["items"][0]["status"] == "unlinked"
    assert result["situation"]["clarification_questions"] == ["Каковы условия договора?"]


@pytest.mark.mock
@pytest.mark.parametrize("needs_clarification", [True, False])
@pytest.mark.parametrize(
    "query",
    [
        "Помогите разобраться в моей ситуации",
        "Что мне делать?",
        "Мне нужна юридическая помощь",
        "У меня сложная проблема, подскажите, как поступить",
    ],
)
def test_vague_request_cannot_search_using_invented_context(query, needs_clarification):
    class InventingInterpreter:
        def interpret(self, query, vocabulary):
            return Interpretation.model_validate(
                {
                    "intent": "rights",
                    "domain_hints": ["жилищное право"],
                    "search_terms": ["арендное жилье"],
                    "entities": [
                        {"name": "арендное жилье", "type": "document", "original_text": query}
                    ],
                    "facts": [{"key": "event", "value": "выселение", "present_in_user_text": True}],
                    "missing_information": ["Какой договор найма?"],
                    "needs_clarification": needs_clarification,
                }
            )

    class MustNotSearch:
        def ready(self):
            return {"kb_loaded": True}

        def vocabulary(self):
            return {"terms": ["арендное жилье"]}

        def search(self, terms):
            pytest.fail("Общая просьба не должна запускать поиск по придуманным терминам")

    result = LegalService(MustNotSearch(), InventingInterpreter()).query(query, "llm")
    assert result["answer"]["status"] == "no_evidence"
    assert result["matches"] == result["search_terms"] == []
    assert result["situation"]["search_allowed"] is False
    assert result["situation"]["needs_clarification"]
    assert result["situation"]["clarification_questions"]
    assert result["interpretation"]["facts"][0]["present_in_user_text"] is False
    assert result["trace"][0]["reason"] == "insufficient_context"


@pytest.mark.parametrize(
    "query",
    [
        "Что такое арендное жилье?",
        "Мне предлагают арендное жилье. Какие условия?",
        "Меня уволили. Что делать?",
        "Я поступаю в вуз. Как называют поступающего?",
        "Подписал договор, но пока не знаю его условий.",
    ],
)
def test_clarification_does_not_block_subject_or_event(query):
    interpretation = Interpretation.model_validate(
        {
            "intent": "rights",
            "domain_hints": [],
            "search_terms": [],
            "entities": [],
            "facts": [],
            "missing_information": ["В какой стране произошли события?"],
            "needs_clarification": True,
        }
    )
    plan = situation_plan(interpretation, query, ["арендное жилье"])
    assert plan["search_allowed"]
    assert plan["needs_clarification"]
    assert plan["clarification_questions"] == ["В какой стране произошли события?"]


def test_literal_kb_concept_allows_definition_without_facts():
    interpretation = Interpretation.model_validate(
        {
            "intent": "definition",
            "domain_hints": [],
            "search_terms": ["юридическая помощь"],
            "entities": [],
            "facts": [],
            "missing_information": [],
            "needs_clarification": False,
        }
    )
    plan = situation_plan(interpretation, "Что такое юридическая помощь?", ["юридическая помощь"])
    assert plan["search_allowed"]
    assert not plan["needs_clarification"]
