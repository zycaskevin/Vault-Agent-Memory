from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "docs" / "landing" / "index.html"
LANDING_DEMO = ROOT / "docs" / "landing" / "demo.html"


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
        "Use the agent-assisted governed-auto memory mode.",
        "Claude Code",
        "Codex",
        "Hermes",
        "Daily Memory Report",
        "Accept Obsidian",
        "Accept Vault",
        "Keep both",
        "vault demo agent-governance --json",
        "demo.html",
        "Rendered demo",
        "Technical runbook",
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


def test_landing_demo_page_contains_rendered_story() -> None:
    html = LANDING_DEMO.read_text(encoding="utf-8")

    required = [
        "See governed memory move between agents.",
        "看受治理的記憶如何在 Agent 之間流動。",
        "看受治理的记忆如何在 Agent 之间流动。",
        "Claude Code",
        "Codex / Hermes",
        "Candidate gate",
        "候選門禁",
        "候选门禁",
        "The story in five moves",
        "五步看懂這個故事",
        "五步看懂这个故事",
        "vault quickstart",
        "flow-path",
        "@keyframes flowDash",
        "prefers-reduced-motion",
    ]
    for text in required:
        assert text in html


def _assert_links_stay_local_and_resolve(page: Path) -> None:
    parser = _LinkParser()
    html = page.read_text(encoding="utf-8")
    parser.feed(html)

    assert parser.links
    for href in parser.links:
        if href.startswith("#"):
            assert f'id="{href[1:]}"' in html
            continue
        assert not href.startswith(("http://", "https://"))
        target = (page.parent / href).resolve()
        assert str(target).startswith(str(ROOT.resolve()))
        assert target.exists(), href


def test_landing_page_links_stay_local_and_resolve() -> None:
    _assert_links_stay_local_and_resolve(LANDING)


def test_landing_demo_page_links_stay_local_and_resolve() -> None:
    _assert_links_stay_local_and_resolve(LANDING_DEMO)
