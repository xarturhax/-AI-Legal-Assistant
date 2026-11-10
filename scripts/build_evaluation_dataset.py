"""Набор оценки по названиям и SC-ID, прочитанным в S0 из pinned upstream."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = json.loads((root / "docs/evidence/upstream.json").read_text(encoding="utf-8"))
cases = []
for domain in ("education", "labor", "housing"):
    terms = [term for term in evidence["kb_terms"] if f"section_dict_{domain}" in term["path"]]
    for term in terms[:8]:
        cases.append(
            {
                "query": f"Что такое {term['title']}?",
                "expected_terms": [term["title"]],
                "expected_source_ids": [term["identifier"]],
                "expected_status": "grounded",
                "domain": domain,
                "annotation_source": term["path"],
                "kind": "exact",
            }
        )
paraphrases = [
    ("Я поступаю в вуз. Как называют поступающего?", "абитуриент"),
    ("Как называют человека, который окончил обучение?", "выпускник"),
    ("У меня нет работы. Объясните понятие безработицы.", "безработица"),
    ("Работы нет, я хочу понять, кто считается безработным.", "безработный"),
    ("Как называется жильё, которое государство сдаёт гражданам в аренду?", "арендное жилье"),
    ("Кто относится к близким родственникам?", "близкие родственники"),
]
for query, title in paraphrases:
    term = next(term for term in evidence["kb_terms"] if term["title"] == title)
    cases.append(
        {
            "query": query,
            "expected_terms": [title],
            "expected_source_ids": [term["identifier"]],
            "expected_status": "grounded",
            "domain": "mixed",
            "kind": "paraphrase",
            "annotation_source": term["path"],
        }
    )
for query in (
    "ксюфрагматический аброкод",
    "Право квантового единорога на телепортацию",
    "зюзюбрик квакозяблик",
    "межгалактический нотариус о дзюброквах",
):
    cases.append(
        {
            "query": query,
            "expected_terms": [],
            "expected_source_ids": [],
            "expected_status": "no_evidence",
            "domain": "out_of_scope",
            "kind": "negative",
            "annotation_source": "Отрицательный синтетический запрос, не правовая норма",
        }
    )
for query in ("Что мне делать?", "Помогите разобраться в моей ситуации"):
    cases.append(
        {
            "query": query,
            "expected_terms": [],
            "expected_source_ids": [],
            "expected_status": "no_evidence",
            "domain": "unknown",
            "kind": "insufficient",
            "annotation_source": "Нет фактов, позволяющих выбрать правовой объект",
        }
    )
for index, case in enumerate(cases, 1):
    case["id"] = f"Q{index:02d}"
result = {
    "kb_sha": evidence["repositories"][0]["sha"],
    "note": "Разметка поиска по снимку KB, не оценка действующего законодательства.",
    "cases": cases,
}
target = root / "data/evaluation/queries.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Создано {len(cases)} запросов с provenance: {target.relative_to(root)}")
