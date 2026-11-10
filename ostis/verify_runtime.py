"""Проверка настоящих ELF-библиотек/SDK в собранном Linux-образе OSTIS."""

import os
import subprocess
from pathlib import Path


def verify_installation(
    prefix=Path("/app/sc-machine"), extensions=Path("/app/build/Release/extensions")
):
    required = (
        prefix / "bin/sc-machine",
        prefix / "bin/sc-builder",
        prefix / "include/sc-memory/sc_memory_headers.hpp",
        prefix / "lib/cmake/sc-machine/sc-machine-config.cmake",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"В официальном SDK отсутствует обязательный файл: {path}")
    modules = list(extensions.glob("*.so"))
    if len(modules) < 14 or not any("user_request_module" in path.name for path in modules):
        raise RuntimeError("Не собраны все 14 исходных групп C++-агентов OSTIS.")
    # LD_LIBRARY_PATH также передаётся проверкам, запущенным вне Dockerfile ENV.
    environment = {**os.environ, "LD_LIBRARY_PATH": str(prefix / "lib")}
    libraries = list((prefix / "lib").rglob("*.so*")) + modules
    for path in [prefix / "bin/sc-machine", prefix / "bin/sc-builder", *libraries]:
        result = subprocess.run(
            ["ldd", str(path)], capture_output=True, text=True, env=environment, timeout=15
        )
        output = result.stdout + result.stderr
        if result.returncode or "not found" in output:
            raise RuntimeError(f"Не разрешены динамические зависимости {path}:\n{output}")
    version = subprocess.run(
        [str(prefix / "bin/sc-machine"), "--version"],
        capture_output=True,
        text=True,
        env=environment,
        check=True,
        timeout=15,
    )
    if "0.10.0" not in version.stdout:
        raise RuntimeError("Официальный бинарник не подтвердил версию sc-machine 0.10.0.")
    print(
        f"OSTIS runtime: PASS, SDK 0.10.0, групп C++-агентов: {len(modules)}; "
        "live KB/WS ещё не проверены."
    )


if __name__ == "__main__":
    verify_installation()
