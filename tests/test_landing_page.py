from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "docs" / "landing" / "index.html"


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value)


def test_landing_page_contains_core_story() -> None:
    html = LANDING.read_text(encoding="utf-8")

    required = [
        "Agents need memory governance, not just RAG.",
        "Agent 不只需要 RAG，更需要記憶治理。",
        "Agent 不只需要 RAG，更需要记忆治理。",
        "Install Vault-for-LLM for this project.",
        "請為這個專案安裝 Vault-for-LLM",
        "请为这个项目安装 Vault-for-LLM",
        "Use consumer mode with governed-auto memory.",
        "Claude Code",
        "Codex",
        "Hermes",
        "Daily Memory Report",
        "Accept Obsidian",
        "Accept Vault",
        "Keep both",
        "vault demo agent-governance --json",
    ]
    for text in required:
        assert text in html


def test_landing_page_has_trilingual_switcher_and_flow_animation() -> None:
    html = LANDING.read_text(encoding="utf-8")

    required = [
        'data-lang="en"',
        'data-lang="zh-Hant"',
        'data-lang="zh-CN"',
        "const translations =",
        "connector-map",
        "flow-line",
        "@keyframes flowDash",
        "prefers-reduced-motion",
        "arch-flow",
    ]
    for text in required:
        assert text in html


def test_landing_page_links_stay_local_and_resolve() -> None:
    parser = _LinkParser()
    parser.feed(LANDING.read_text(encoding="utf-8"))

    assert parser.links
    for href in parser.links:
        if href.startswith("#"):
            assert f'id="{href[1:]}"' in LANDING.read_text(encoding="utf-8")
            continue
        assert not href.startswith(("http://", "https://"))
        target = (LANDING.parent / href).resolve()
        assert str(target).startswith(str(ROOT.resolve()))
        assert target.exists(), href
