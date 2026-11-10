from pathlib import Path

import pytest
from app import config


@pytest.mark.mock
@pytest.mark.parametrize("layout", ["checkout", "container"])
@pytest.mark.parametrize("override", [False, True])
def test_catalog_path_in_checkout_and_shallow_container(layout, override, monkeypatch, tmp_path):
    # Только расположение модуля имитируется; Docker здесь не запускается.
    if layout == "container":
        application_root = Path(tmp_path.anchor) / "app"
        default_catalog = application_root / "documents/catalog.json"
    else:
        application_root = tmp_path / "project/backend"
        default_catalog = application_root.parent / "data/documents/catalog.json"
    monkeypatch.setattr(config, "__file__", str(application_root / "app/config.py"))
    monkeypatch.delenv("DOCUMENT_CATALOG", raising=False)
    configured_catalog = tmp_path / "explicit/catalog.json"
    if override:
        monkeypatch.setenv("DOCUMENT_CATALOG", str(configured_catalog))
    settings = config.configuration()
    assert Path(settings["DOCUMENT_CATALOG"]) == (
        configured_catalog if override else default_catalog
    )
