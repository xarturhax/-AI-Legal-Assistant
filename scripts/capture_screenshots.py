"""Снимки настоящего HTTP-приложения через установленный Chromium, без макетов."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-ostis-unavailable", action="store_true")
    options = parser.parse_args()
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if os.name == "nt":
        chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    if not chrome or not Path(chrome).is_file():
        raise SystemExit("SKIPPED: установленный Chromium не найден.")
    target = ROOT / "docs/screenshots"
    target.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".cache/browser-evidence"
    profile.mkdir(parents=True, exist_ok=True)
    pages = [("home", "/", 200), ("requests", "/requests", 200)]
    if options.expect_ostis_unavailable:
        pages.append(
            ("ostis-unavailable", "/directory?" + urlencode({"term": "арендное жилье"}), 503)
        )
    results = []
    with httpx.Client(timeout=20, trust_env=False) as connection:
        for label, route, expected_status in pages:
            url = "http://127.0.0.1:5000" + route
            response = connection.get(url)
            if response.status_code != expected_status:
                raise SystemExit(
                    f"FAIL: {route}, HTTP {response.status_code}, ожидался {expected_status}"
                )
            started = time.time()
            path = target / f"{label}.png"
            process = subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-gpu-sandbox",
                    "--in-process-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--user-data-dir={profile}",
                    f"--screenshot={path}",
                    "--window-size=1440,1000",
                    url,
                ],
                capture_output=True,
                timeout=30,
            )
            success = process.returncode == 0 and path.is_file() and path.stat().st_mtime >= started
            results.append(
                {
                    "route": route,
                    "http_status": response.status_code,
                    "status": "PASS" if success else "FAIL",
                    "screenshot": str(path.relative_to(ROOT)),
                }
            )
    report = {
        "scope": "real_http_browser_pages",
        "hybrid_stack_verified": False,
        "mock": False,
        "results": results,
    }
    (ROOT / "docs/evidence/browser-smoke.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if all(row["status"] == "PASS" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
