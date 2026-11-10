"""Настоящий HTTP-smoke: локальный сайт и ожидаемое состояние зависимостей."""

import argparse
import json
import re
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-offline", action="store_true")
    options = parser.parse_args()
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:5000", timeout=20, trust_env=False) as connection:
        for route in (
            "/",
            "/requests",
            "/directory",
            "/auth",
            "/reg",
            "/verification",
            "/recover",
            "/forum",
            "/news",
            "/templates",
        ):
            response = connection.get(route)
            checks.append(
                {
                    "route": route,
                    "http_status": response.status_code,
                    "pass": response.status_code == 200,
                }
            )
        ready = connection.get("/health/ready")
        page = connection.get("/requests")
        token = re.search(r'name="csrf-token" content="([^"]+)"', page.text)[1]
        result = connection.post(
            "/api/legal/query",
            json={"query": "арендное жилье", "mode": "baseline"},
            headers={"X-CSRFToken": token},
        )
        if options.expect_offline:
            checks.append(
                {
                    "route": "/api/legal/query",
                    "http_status": result.status_code,
                    "pass": result.status_code == 503 and "answer" not in result.json(),
                }
            )
        else:
            checks.append(
                {
                    "route": "/api/legal/query",
                    "http_status": result.status_code,
                    "pass": result.status_code == 200
                    and result.json()["answer"]["status"] == "grounded",
                }
            )
    report = {
        "scope": "real_http",
        "mock": False,
        "expected_offline": options.expect_offline,
        "readiness_http_status": ready.status_code,
        "readiness": ready.json(),
        "checks": checks,
    }
    path = Path(__file__).resolve().parents[1] / "docs/evidence/http-smoke.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if all(check["pass"] for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
