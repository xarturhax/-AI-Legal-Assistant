import importlib.util
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.mock


def verifier():
    path = Path(__file__).resolve().parents[3] / "ostis/verify_runtime.py"
    spec = importlib.util.spec_from_file_location("verify_ostis_image", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sdk_fixture(tmp_path):
    # Только файловая тестовая фикстура. Настоящие ELF/SDK в этом тесте не запускаются.
    prefix, extensions = tmp_path / "sdk", tmp_path / "extensions"
    paths = [
        prefix / "bin/sc-machine",
        prefix / "bin/sc-builder",
        prefix / "include/sc-memory/sc_memory_headers.hpp",
        prefix / "lib/cmake/sc-machine/sc-machine-config.cmake",
        extensions / "libuser_request_module.so",
    ]
    paths += [extensions / f"libtest_fixture_{index}.so" for index in range(13)]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return prefix, extensions


def test_missing_shared_library_stops_image_verification(tmp_path, monkeypatch):
    module = verifier()
    prefix, extensions = sdk_fixture(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a, 0, stdout="libglib-2.0.so.0 => not found\n", stderr=""
        ),
    )
    with pytest.raises(RuntimeError, match="динамические зависимости"):
        module.verify_installation(prefix, extensions)


def test_wrong_engine_version_stops_image_verification(tmp_path, monkeypatch):
    module = verifier()
    prefix, extensions = sdk_fixture(tmp_path)

    def run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="sc-machine 0.9.0" if "--version" in command else "resolved",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError, match="не подтвердил версию"):
        module.verify_installation(prefix, extensions)
