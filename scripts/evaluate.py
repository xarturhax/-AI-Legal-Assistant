"""Оценка без вымышленных live-метрик; недоступный стек даёт SKIPPED и exit 2."""

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))

from app.errors import ServiceError
from app.evaluation import percentile, precision_recall_f1, term_counts
from app.legal.search_baseline import extract_terms
from app.legal.service import LegalService
from app.llm.interpreter import OllamaInterpreter
from app.ostis.client import OstisClient


def evaluate(dataset, terms_only, *, progress=False):
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "kb_sha": dataset["kb_sha"],
        "kb_sha_role": "dataset_annotation",
        "runtime_kb_version": "unknown",
        "mock": False,
        "scope": "baseline_terms_only" if terms_only else "live_stack",
        "models": {},
        "results": [],
    }
    service = LegalService(
        OstisClient(os.getenv("OSTIS_WS_URL", "ws://127.0.0.1:8090/ws_json")),
        OllamaInterpreter(
            os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct"),
        ),
    )
    if not terms_only:
        failures = []
        try:
            service.ostis.ready()
        except ServiceError as error:
            failures.append(error.code)
        if failures:
            report.update(status="SKIPPED", reason=failures, metrics=None)
            return report
        report["models"]["ollama"] = service.interpreter.model
    summaries = {}
    for mode in ["baseline"] if terms_only else ["baseline", "llm"]:
        if mode == "llm" and not service.interpreter.ready():
            summaries[mode] = {"status": "SKIPPED", "reason": "llm_unavailable"}
            continue
        tp = fp = fn = references = unsupported = expected_hits = errors = timeouts = 0
        candidates = linked = 0
        times = []
        request_times = []
        for case in dataset["cases"]:
            start = time.perf_counter()
            row = {"case": case["id"], "mode": mode, "query": case["query"]}
            try:
                if terms_only:
                    terms, result = extract_terms(case["query"]), None
                else:
                    result = service.query(case["query"], mode)
                    row["request_seconds"] = result["runtime"]["elapsed_seconds"]
                    request_times.append(row["request_seconds"])
                    terms = (
                        result["search_terms"] if mode == "llm" else extract_terms(case["query"])
                    )
                    row["answer_status"] = result["answer"]["status"]
                    row["status_matches_gold"] = row["answer_status"] == case["expected_status"]
                    row["returned_source_ids"] = [m["sc_identifier"] for m in result["matches"]]
                    situation = result.get("situation") or {}
                    row["needs_clarification"] = situation.get("needs_clarification")
                    row["clarification_questions"] = situation.get("clarification_questions", [])
                    row["assessment_status"] = situation.get("assessment_status")
                    row["interpretation"] = result.get("interpretation")
                    row["trace"] = result.get("trace", [])
                    source_hit = bool(
                        set(row["returned_source_ids"]) & set(case["expected_source_ids"])
                    )
                    row["behavior_matches_gold"] = (
                        row["status_matches_gold"]
                        and (source_hit if case["expected_source_ids"] else not result["matches"])
                        and (
                            not case.get("expected_clarification")
                            or mode != "llm"
                            or bool(row["needs_clarification"] and row["clarification_questions"])
                        )
                    )
                    linked += len(set(result["linked_terms"]))
                    for match in result["matches"]:
                        references += 1
                        expected_hits += match["sc_identifier"] in case["expected_source_ids"]
                        source = service.ostis.source(match["id"])
                        if (
                            not source
                            or source["sc_address"] != match["sc_address"]
                            or match["excerpt"] not in source["text"]
                        ):
                            unsupported += 1
                row.update(status="PASS", predicted_terms=terms)
                counts = term_counts(terms, case["expected_terms"])
                tp, fp, fn = tp + counts[0], fp + counts[1], fn + counts[2]
                candidates += len(terms)
            except ServiceError as error:
                row.update(status="FAIL", error=error.code)
                errors += 1
                timeouts += error.code.endswith("timeout")
            duration = time.perf_counter() - start
            row["seconds"] = duration
            times.append(duration)
            report["results"].append(row)
            if progress:
                print(
                    f"{mode} {case['id']}: {row['status']} ({duration:.2f} с)",
                    file=sys.stderr,
                    flush=True,
                )
        summaries[mode] = {
            "term_micro": precision_recall_f1(tp, fp, fn),
            "counts": {"tp": tp, "fp": fp, "fn": fn},
            "cases": len(dataset["cases"]),
            "failures": errors,
            "p50_seconds": percentile(times, 0.5),
            "p95_seconds": percentile(times, 0.95),
            "request_p50_seconds": percentile(request_times, 0.5),
            "request_p95_seconds": percentile(request_times, 0.95),
            "timeout_rate": timeouts / len(times),
            "linked_candidate_fraction": linked / candidates
            if candidates and not terms_only
            else None,
            "unsupported_reference_fraction": unsupported / references
            if references and not errors
            else None,
            "expected_source_precision": expected_hits / references if references else None,
            "references": references if not terms_only else None,
            "status_agreement_fraction": sum(
                row.get("status_matches_gold", False)
                for row in report["results"]
                if row["mode"] == mode
            )
            / len(dataset["cases"])
            if not terms_only
            else None,
        }
    report.update(
        status=(
            "FAIL"
            if any(row["status"] == "FAIL" for row in report["results"])
            else "SKIPPED"
            if any(v.get("status") == "SKIPPED" for v in summaries.values())
            else "PASS"
        ),
        metrics=summaries,
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--terms-only", action="store_true", help="Только извлечение baseline, без SC-поиска и LLM"
    )
    parser.add_argument("--output", type=Path, default=root / "reports/evaluation.json")
    parser.add_argument("--dataset", type=Path, default=root / "data/evaluation/queries.json")
    parser.add_argument("--progress", action="store_true", help="Показывать ход проверки")
    options = parser.parse_args()
    dataset = json.loads(options.dataset.read_text(encoding="utf-8"))
    report = evaluate(dataset, options.terms_only, progress=options.progress)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "scope": report["scope"],
                "reason": report.get("reason"),
                "output": str(options.output),
            },
            ensure_ascii=False,
        )
    )
    return 2 if report["status"] == "SKIPPED" else 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
