import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.evaluation import percentile, precision_recall_f1, term_counts


def test_metrics_and_dataset_provenance():
    assert term_counts(["арендное жилье", " шум "], ["АРЕНДНОЕ ЖИЛЬЕ", "пропуск"]) == (1, 1, 1)
    assert precision_recall_f1(1, 1, 1) == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert percentile([0, 10], 0.95) == 9.5
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / "data/evaluation/queries.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "docs/evidence/upstream.json").read_text(encoding="utf-8"))
    known = {item["identifier"] for item in audit["kb_terms"]}
    assert len(data["cases"]) >= 30
    for case in data["cases"]:
        assert set(case["expected_source_ids"]) <= known


@pytest.mark.mock
def test_live_evaluation_still_runs_baseline_without_ollama(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    evaluate = runpy.run_path(str(root / "scripts/evaluate.py"))["evaluate"]

    def query(text, mode):
        assert mode == "baseline"
        return {
            "matches": [],
            "linked_terms": [],
            "answer": {"status": "no_evidence"},
            "runtime": {"elapsed_seconds": 0.1},
        }

    service = SimpleNamespace(
        ostis=SimpleNamespace(ready=lambda: True),
        interpreter=SimpleNamespace(ready=lambda: False, model="test-only"),
        query=query,
    )
    monkeypatch.setitem(evaluate.__globals__, "LegalService", lambda *args: service)
    result = evaluate(
        {
            "kb_sha": "test-only",
            "cases": [
                {
                    "id": "test-only",
                    "query": "неизвестно",
                    "expected_terms": [],
                    "expected_source_ids": [],
                    "expected_status": "no_evidence",
                }
            ],
        },
        False,
    )
    assert result["status"] == "SKIPPED"
    assert result["results"][0]["mode"] == "baseline"
    assert result["results"][0]["status"] == "PASS"
    assert result["metrics"]["llm"]["reason"] == "llm_unavailable"
