from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import history_privacy_scan


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_public_governance_collector_phrase_is_narrowly_allowlisted(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Synthetic Test")
    _git(repo, "config", "user.email", "synthetic@example.invalid")

    public_doc = (
        repo
        / ".agentic-sdd-governance"
        / "collectors"
        / "browser-playwright.md"
    )
    public_doc.parent.mkdir(parents=True)
    lower_term = f"private{chr(32)}user"
    exact_public_line = (
        "Do not share the raw trace when it includes typed credentials, DOM "
        f"content, cookies, storage, or {lower_term} data."
    )
    private_term = lower_term.title()
    public_doc.write_text(
        exact_public_line
        + "\n"
        + exact_public_line.replace(lower_term, private_term)
        + "\n "
        + exact_public_line
        + "\n"
        + exact_public_line
        + " changed\n",
        encoding="utf-8",
    )
    private_doc = repo / "docs" / "private.md"
    private_doc.parent.mkdir()
    private_doc.write_text(exact_public_line + "\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "synthetic fixture")

    monkeypatch.setattr(history_privacy_scan, "PRIVATE_TERMS", [private_term])
    findings = history_privacy_scan.scan_terms(repo)

    assert {
        finding.location.split(":", 1)[1] for finding in findings
    } == {
        ".agentic-sdd-governance/collectors/browser-playwright.md:2",
        ".agentic-sdd-governance/collectors/browser-playwright.md:3",
        ".agentic-sdd-governance/collectors/browser-playwright.md:4",
        "docs/private.md:1",
    }
