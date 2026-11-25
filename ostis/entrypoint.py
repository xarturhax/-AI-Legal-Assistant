"""Сборка настоящей KB в записываемой копии read-only исходников."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

LEGAL_TEXT_REFERENCE = re.compile(r'"file://(text/[^"\r\n]+\.html?)"', re.IGNORECASE)


def embed_legal_texts(root: Path) -> None:
    """Store local upstream legal text in SC links before building the memory."""
    legal = root / "knowledge-base" / "legal"
    embedded = missing = 0
    for source in legal.rglob("*.scs"):
        original = source.read_text(encoding="utf-8")

        def inline(match):
            nonlocal embedded, missing
            file = (source.parent / match[1]).resolve()
            if not file.is_relative_to(legal) or not file.is_file():
                missing += 1
                return match[0]
            text = file.read_text(encoding="utf-8-sig").strip()
            if not text:
                missing += 1
                return match[0]
            embedded += 1
            return "[" + text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]") + "]"

        result = LEGAL_TEXT_REFERENCE.sub(inline, original)
        if result != original:
            source.write_text(result, encoding="utf-8")
    print(f"Тексты актов: загружено {embedded}, файлов нет или они пусты: {missing}", flush=True)


def build_knowledge_base(source: Path, binaries: Path, config: Path) -> int:
    source = source.resolve(strict=True)
    # GWFTranslator записывает *.gwf.generated.scs рядом с исходным .gwf.
    # Весь каталог сохраняет относительные пути repo.path и вложенных ресурсов.
    with TemporaryDirectory(prefix="legal-kb-build-") as temporary:
        writable = Path(temporary) / "sources"
        root = source if source.is_dir() else source.parent
        shutil.copytree(root, writable, ignore=shutil.ignore_patterns(".git"))
        embed_legal_texts(writable)
        additions = Path(__file__).with_name("knowledge-additions")
        if additions.is_dir() and (writable / "knowledge-base/legal").is_dir():
            shutil.copytree(additions, writable / "knowledge-base/legal/themis", dirs_exist_ok=True)
        build_source = writable if source.is_dir() else writable / source.name
        print(f"Сборка KB во временной копии: {build_source}", flush=True)
        result = subprocess.run(
            [str(binaries / "sc-builder"), "--clear", "-c", str(config), "-i", str(build_source)],
            check=False,
        )
        return result.returncode


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("source", nargs="?", default=os.getenv("KB_PATH", "/knowledge-base"))
        parser.add_argument("-b", default=os.getenv("BINARY_PATH", "/app/sc-machine/bin"))
        parser.add_argument("-c", default=os.getenv("CONFIG_PATH", "/config/legislation.ini"))
        arguments = parser.parse_args(sys.argv[2:])
        return build_knowledge_base(Path(arguments.source), Path(arguments.b), Path(arguments.c))
    # Штатный upstream запускает настоящий sc-machine и все его расширения.
    os.execv("/bin/bash", ["/bin/bash", "/app/scripts/docker_entrypoint.sh", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
