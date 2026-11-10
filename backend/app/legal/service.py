import time

from app.legal.search_baseline import extract_terms, normalize_search_term, query_phrase


class LegalService:
    def __init__(self, ostis, interpreter=None):
        self.ostis = ostis
        self.interpreter = interpreter

    def query(self, query, mode):
        started = time.monotonic()
        interpretation = None
        if mode == "llm":
            # OSTIS проверяется ДО передачи текста локальной модели.
            self.ostis.ready()
            vocabulary = self.ostis.vocabulary()["terms"]
            exact = normalize_search_term(query_phrase(query))
            if exact in vocabulary:
                vocabulary = [exact]
            else:
                exact = None
            interpretation = self.interpreter.interpret(query, vocabulary=vocabulary)
            terms = [exact] if exact else interpretation.search_terms
        else:
            terms = extract_terms(query)
        result = self.ostis.search(terms)
        evidence = [m for m in result["matches"] if m.get("excerpt")]
        answer = (
            "\n\n".join(m["excerpt"] for m in evidence[:4])
            if evidence
            else "Подтверждённых сведений по запросу не найдено."
        )
        return {
            "query": query,
            "mode": mode,
            "interpretation": interpretation.model_dump() if interpretation else None,
            **result,
            "answer": {"text": answer, "status": "grounded" if evidence else "no_evidence"},
            "runtime": {
                "ostis_connected": True,
                "llm_used": mode == "llm",
                "mock": False,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            },
        }
