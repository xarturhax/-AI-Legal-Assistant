"""Сборка настоящей KB в записываемой копии read-only исходников."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def build_knowledge_base(source: Path, binaries: Path, config: Path) -> int:
    source = source.resolve(strict=True)
    # GWFTranslator записывает *.gwf.generated.scs рядом с исходным .gwf.
    # Весь каталог сохраняет относительные пути repo.path и вложенных ресурсов.
    with TemporaryDirectory(prefix="legal-kb-build-") as temporary:
        writable = Path(temporary) / "sources"
        root = source if source.is_dir() else source.parent
        shutil.copytree(root, writable, ignore=shutil.ignore_patterns(".git"))
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
