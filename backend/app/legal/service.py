import time

from app.legal.relevance import filter_sources, literal_terms, matched_topic_terms
from app.legal.scope import maritime_registration
from app.legal.search_baseline import (
    extract_terms,
    is_definition_question,
    matching_text,
    normalize_search_term,
    query_phrase,
)
from app.legal.situation import link_situation, situation_plan


class LegalService:
    def __init__(self, ostis, interpreter=None):
        self.ostis = ostis
        self.interpreter = interpreter

    def lookup_concepts(self, term, mode):
        if mode == "baseline":
            return self.ostis.search([term], use_agent=False)
        return self.query(term, mode, use_agent=False)

    def query(self, query, mode, *, use_agent=True):
        started = time.monotonic()
        interpretation = None
        situation = None
        maritime = maritime_registration(query)
        vocabulary = []
        topic_markers = {}
        if mode == "llm" and use_agent:
            # OSTIS проверяется ДО передачи текста локальной модели.
            self.ostis.ready()
        if mode == "llm" or maritime:
            catalog = self.ostis.vocabulary()
            vocabulary = catalog["terms"]
            topic_markers = catalog.get("topic_markers", {})
        exact = normalize_search_term(query_phrase(query))
        blocked_reason = None
        direct_terms = []
        topic_terms = []
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
            if exact not in vocabulary:
                normalized_phrase = matching_text(exact or "")
                exact = next(
                    (term for term in vocabulary if matching_text(term) == normalized_phrase), None
                )
            if exact:
                vocabulary = [exact]
            interpret = (
                self.interpreter.interpret if use_agent else self.interpreter.interpret_directory
            )
            interpretation = interpret(query, vocabulary=vocabulary)
            situation = situation_plan(
                interpretation, query, vocabulary, topic_markers=topic_markers if use_agent else {}
            )
            explicit = literal_terms(query, vocabulary)
            if use_agent and not exact:
                topic_terms = matched_topic_terms(query, topic_markers)
            if exact:
                direct_terms = [exact]
            else:
                # Псевдонимы тем прочитаны из SC-памяти и совпали с исходным текстом.
                direct_terms = topic_terms.copy()
                if interpretation.intent != "definition" and not is_definition_question(query):
                    direct_terms.extend(explicit)
            terms = list(
                dict.fromkeys(
                    [
                        *topic_terms,
                        *explicit,
                        *interpretation.search_terms,
                        *(term for item in situation["items"] for term in item["terms"]),
                    ]
                )
            )[:16]
            if not situation["search_allowed"]:
                blocked_reason = "insufficient_context"
                terms = []
                interpretation.needs_clarification = True
                interpretation.missing_information = situation["clarification_questions"]
        else:
            terms = extract_terms(query)
        relevance_error = None
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
            result = (
                self.ostis.search(terms) if use_agent else self.ostis.search(terms, use_agent=False)
            )
            if topic_terms:
                result["trace"].insert(
                    0, {"method": "sc_situation_topic", "status": "matched", "terms": topic_terms}
                )
            if mode == "llm":
                relevance_error = filter_sources(
                    query, result, self.interpreter, direct_terms=direct_terms
                )
        for match in result["matches"]:
            title = normalize_search_term(match.get("title", ""))
            match["source_exists"] = True
            match["source_relevant"] = True if exact and exact == title else None
            match["legal_applicability"] = None
        evidence = [m for m in result["matches"] if m.get("excerpt")]
        guidance = (
            [match["case_guidance"] for match in result["matches"] if match.get("case_guidance")]
            if use_agent
            else []
        )
        answer = (
            "\n\n".join(m["excerpt"] for m in evidence[:4])
            if evidence
            else "Подтверждённых сведений по запросу не найдено."
        )
        if guidance:
            answer = "\n\n".join(
                [point["text"] for case in guidance for point in case["provisions"]]
                + [check for case in guidance for check in case["checks"]]
            )
        if blocked_reason == "outside_confirmed_scope":
            answer = "В загруженной базе нет подтверждённых сведений о регистрации морских судов."
        elif blocked_reason == "insufficient_context":
            answer = "Для поиска опишите обстоятельства ситуации и свой вопрос."
        elif relevance_error and not evidence:
            answer = "Не удалось проверить связь найденных материалов с вопросом. Повторите запрос."
        return {
            "query": query,
            "mode": mode,
            "interpretation": interpretation.model_dump() if interpretation else None,
            "search_terms": terms,
            "situation": link_situation(situation, result["matches"]) if situation else None,
            **result,
            "answer": {
                "text": answer,
                "status": "grounded" if evidence or guidance else "no_evidence",
                "guidance": guidance,
            },
            "runtime": {
                "ostis_connected": True,
                "llm_used": interpretation is not None,
                "mock": False,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            },
        }
