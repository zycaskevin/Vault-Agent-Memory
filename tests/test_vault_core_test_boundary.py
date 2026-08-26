from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_default_pytest_surface_excludes_preserved_subject_identity_controls():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pytest_config = pyproject.split("[tool.pytest.ini_options]", 1)[1]

    assert 'addopts = ["--ignore-glob=tests/test_subject*.py"]' in pytest_config
