import json
from pathlib import Path

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
