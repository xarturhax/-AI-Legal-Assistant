import time

from app.legal.scope import maritime_registration
from app.legal.search_baseline import extract_terms, normalize_search_term, query_phrase
from app.legal.situation import link_situation, situation_plan


class LegalService:
    def __init__(self, ostis, interpreter=None):
        self.ostis = ostis
        self.interpreter = interpreter

    def query(self, query, mode):
        started = time.monotonic()
        interpretation = None
        situation = None
        maritime = maritime_registration(query)
        vocabulary = []
        if mode == "llm":
            # OSTIS проверяется ДО передачи текста локальной модели.
            self.ostis.ready()
        if mode == "llm" or maritime:
            vocabulary = self.ostis.vocabulary()["terms"]
        exact = normalize_search_term(query_phrase(query))
        blocked_reason = None
        if maritime and not any(maritime_registration(term) for term in vocabulary):
            blocked_reason = "outside_confirmed_scope"
            terms = []
            situation = {
                "items": [],
                "search_allowed": False,
                "clarification_questions": ["Уточните юрисдикцию или укажите имеющийся источник."],
                "needs_clarification": True,
                "assessment_status": "not_performed",
                "notice": "В загруженной базе нет подтверждённой темы регистрации морских судов.",
            }
        elif mode == "llm":
            if exact in vocabulary:
                vocabulary = [exact]
            else:
                exact = None
            interpretation = self.interpreter.interpret(query, vocabulary=vocabulary)
            situation = situation_plan(interpretation, query, vocabulary)
            terms = [exact] if exact else interpretation.search_terms
            terms = list(
                dict.fromkeys(
                    [*terms, *(term for item in situation["items"] for term in item["terms"])]
                )
            )[:16]
            if not situation["search_allowed"]:
                blocked_reason = "insufficient_context"
                terms = []
                interpretation.needs_clarification = True
                interpretation.missing_information = situation["clarification_questions"]
        else:
            terms = extract_terms(query)
        if blocked_reason:
            result = {
                "matches": [],
                "linked_terms": [],
                "unmatched_terms": [],
                "trace": [
                    {
                        "method": "query_interpretation",
                        "status": "needs_clarification",
                        "reason": blocked_reason,
                    }
                ],
            }
        else:
            result = self.ostis.search(terms)
        for match in result["matches"]:
            title = normalize_search_term(match.get("title", ""))
            match["source_exists"] = True
            match["source_relevant"] = True if exact and exact == title else None
            match["legal_applicability"] = None
        evidence = [m for m in result["matches"] if m.get("excerpt")]
        answer = (
            "\n\n".join(m["excerpt"] for m in evidence[:4])
            if evidence
            else "Подтверждённых сведений по запросу не найдено."
        )
        if blocked_reason == "outside_confirmed_scope":
            answer = "В загруженной базе нет подтверждённых сведений о регистрации морских судов."
        elif blocked_reason == "insufficient_context":
            answer = "Для поиска опишите обстоятельства ситуации и свой вопрос."
        return {
            "query": query,
            "mode": mode,
            "interpretation": interpretation.model_dump() if interpretation else None,
            "search_terms": terms,
            "situation": link_situation(situation, result["matches"]) if situation else None,
            **result,
            "answer": {"text": answer, "status": "grounded" if evidence else "no_evidence"},
            "runtime": {
                "ostis_connected": True,
                "llm_used": interpretation is not None,
                "mock": False,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            },
        }
