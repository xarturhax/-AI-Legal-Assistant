"""Первичная установка Linux. Никаких очищений существующей KB."""

import json
import os
import subprocess

from prepare_env import ROOT, prepare_environment


def run(*arguments, check=True):
    return subprocess.run(arguments, cwd=ROOT, check=check)


def compose(*arguments, check=True):
    return run("docker", "compose", *arguments, check=check)


def main():
    run("docker", "info")
    prepare_environment()
    pin = json.loads((ROOT / "ostis/upstream.lock.json").read_text())
    checkout = ROOT / "ostis/upstream"
    if not checkout.exists():
        run("git", "clone", "--no-checkout", pin["url"], str(checkout))
        run("git", "-C", str(checkout), "checkout", "--detach", pin["sha"])
    revision = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if (
        revision != pin["sha"]
        or subprocess.check_output(
            ["git", "-C", str(checkout), "status", "--porcelain"], text=True
        ).strip()
    ):
        raise SystemExit("Upstream отличается от pin или изменён. Файлы не перезаписывались.")
    run("git", "-C", str(checkout), "submodule", "update", "--init", "--recursive")
    for path, sha in pin["submodules"].items():
        actual = subprocess.check_output(
            ["git", "-C", str(checkout / path), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != sha:
            raise SystemExit("SHA подмодуля не совпал: " + path)
    compose("config", "--quiet")
    compose("build", "machine", "app")
    marked = compose(
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "/bin/sh",
        "machine",
        "-c",
        "test -f /kb.bin/.legal-kb-ready",
        check=False,
    )
    if marked.returncode == 1:
        compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "/app/.venv/bin/python3",
            "machine",
            "-c",
            "import pathlib,sys; sys.exit(any(pathlib.Path('/kb.bin').iterdir()))",
        )
        compose("run", "--rm", "--no-deps", "machine", "build")
        compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "/bin/sh",
            "machine",
            "-c",
            "touch /kb.bin/.legal-kb-ready",
        )
    elif marked.returncode:
        raise SystemExit("Не удалось проверить KB. Сборка отменена.")
    compose("up", "-d", "--wait", "ollama")
    values = dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    compose(
        "exec",
        "-T",
        "ollama",
        "ollama",
        "pull",
        os.getenv("OLLAMA_MODEL", values.get("OLLAMA_MODEL", "qwen3:4b-instruct")),
    )
    compose("run", "--rm", "--no-deps", "app", "python", "-m", "app", "db-upgrade")
    print("Установка завершена. Запуск: docker compose up -d --wait")


if __name__ == "__main__":
    main()
