from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_default_pytest_surface_excludes_preserved_subject_identity_controls():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]

    assert addopts == ["--ignore-glob=tests/test_subject*.py"]
