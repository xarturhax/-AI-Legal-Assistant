"""Статическая проверка инфраструктуры; не является live-проверкой Docker."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pin = json.loads((root / "ostis/upstream.lock.json").read_text(encoding="utf-8"))
assert len(pin["sha"]) == 40
for filename in ("setup.bat", "start.bat", "stop.bat", "rebuild-kb.bat", "cleanup.bat"):
    path = root / filename
    entrypoint = "cleanup_space.ps1" if filename == "cleanup.bat" else "manage.ps1"
    assert entrypoint in path.read_text(encoding="utf-8")
    raw = path.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""), (
        f"{filename}: для cmd.exe требуются окончания строк Windows CRLF"
    )
script = (root / "scripts/manage.ps1").read_text(encoding="utf-8")
assert "down -v" not in script
assert "REBUILD" in script and "backupName" in script
assert "storage = /kb.bin" in (root / "ostis/runtime.ini").read_text()
dockerfile = (root / "ostis/Dockerfile").read_text(encoding="utf-8")
assert "conan.ostis.net" not in dockerfile and "conan install" not in dockerfile
assert "releases/download/0.10.0/sc-machine-0.10.0-Linux.tar.gz" in dockerfile
assert "-DCMAKE_PREFIX_PATH=/app/sc-machine" in dockerfile
assert "COPY --from=builder /app/build/Release/extensions" in dockerfile
assert "RUN python3 /app/verify_runtime.py" in dockerfile
assert '"/app/entrypoint.py"' in dockerfile
assert "!ostis/entrypoint.py" in (root / ".dockerignore").read_text()
assert "./ostis/upstream:/knowledge-base:ro" in (root / "docker-compose.yml").read_text()
assert "curl --fail --location" in dockerfile
print("S1 static: PASS (Docker/WSL/сборка KB не проверены)")
