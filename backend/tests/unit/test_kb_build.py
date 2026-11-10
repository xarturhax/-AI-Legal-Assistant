"""Регрессии GWF-сборки: настоящий sc-builder проверяется отдельно на Docker."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.mock


def entrypoint():
    path = Path(__file__).resolve().parents[3] / "ostis/entrypoint.py"
    spec = importlib.util.spec_from_file_location("ostis_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("builder_exit_code", [0, 1])
def test_gwf_build_uses_writable_copy_and_preserves_original(
    tmp_path, monkeypatch, builder_exit_code
):
    original = tmp_path / "upstream"
    legal = original / "knowledge-base/legal"
    legal.mkdir(parents=True)
    (original / "repo.path").write_text("knowledge-base\n", encoding="utf-8")
    gwf = legal / "question_model.gwf"
    gwf.write_text("test-only-gwf", encoding="utf-8")
    (original / ".git").mkdir()
    (original / ".git/config").write_text("test-only-git", encoding="utf-8")
    config, binaries = tmp_path / "runtime.ini", tmp_path / "bin"
    staged_paths = []

    def builder(command, **kwargs):
        assert command[:5] == [str(binaries / "sc-builder"), "--clear", "-c", str(config), "-i"]
        staged_repo = Path(command[5])
        staged_paths.append(staged_repo.parent)
        assert staged_repo.read_bytes() == (original / "repo.path").read_bytes()
        assert not (staged_repo.parent / ".git").exists()
        staged_gwf = staged_repo.parent / "knowledge-base/legal/question_model.gwf"
        assert staged_gwf.read_bytes() == gwf.read_bytes()
        staged_gwf.with_suffix(".gwf.generated.scs").write_text(
            "test-only-output", encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, builder_exit_code)

    monkeypatch.setattr(subprocess, "run", builder)
    assert (
        entrypoint().build_knowledge_base(original / "repo.path", binaries, config)
        == builder_exit_code
    )
    assert gwf.read_text(encoding="utf-8") == "test-only-gwf"
    assert not list(original.rglob("*.generated.scs"))
    assert staged_paths and all(not path.exists() for path in staged_paths)
