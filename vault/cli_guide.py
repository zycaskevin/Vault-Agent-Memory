"""Compact agent-first CLI guide."""

from __future__ import annotations

from typing import Callable, Any


def guide_payload(mode: str = "human") -> dict:
    """Return the compact agent-first command guide."""
    everyday = [
        {
            "command": "vault setup-agent",
            "purpose": "Guided install for humans and agents. Start here instead of memorizing flags.",
        },
        {
            "command": "vault guide",
            "purpose": "Show the small recommended entrypoints and where advanced commands live.",
        },
        {
            "command": "vault gui",
            "purpose": "Open the local console for browsing documents, tasks, graph, and review queues.",
        },
        {
            "command": "vault search \"query\"",
            "purpose": "Find relevant reviewed knowledge.",
        },
        {
            "command": "vault remember \"Title\" --content \"...\" --reason \"...\"",
            "purpose": "Propose memory as a reviewable candidate instead of writing active knowledge directly.",
        },
        {
            "command": "vault task start/update/handoff",
            "purpose": "Keep current work resumable without turning task notes into long-term memory.",
        },
    ]
    agent = [
        {
            "profile": "core",
            "purpose": "Daily startup and recall: status, activity, brief, handoff, search, bounded read, propose memory.",
        },
        {
            "profile": "review",
            "purpose": "Candidate review, transcript capture, Task Ledger, Skill read/sync inspection, Dream reports.",
        },
        {
            "profile": "maintenance",
            "purpose": "Explicit operator-led writes, cold-store lifecycle, Obsidian import, convergence, freshness.",
        },
        {
            "profile": "full",
            "purpose": "Trusted local operators and backwards compatibility only.",
        },
    ]
    maintenance = [
        {
            "command": "vault automation cycle --write-workspace",
            "purpose": "Run the closed-loop memory workspace for the next agent.",
        },
        {
            "command": "vault memory pipeline --write-candidates --write-report",
            "purpose": "Capture conversation lessons into gated candidates and write a receipt.",
        },
        {
            "command": "vault memory reflection --write-candidates",
            "purpose": "Run report-first Dream/reflection and write consolidation suggestions only.",
        },
        {
            "command": "vault security doctor",
            "purpose": "Check GUI token and MCP identity hardening.",
        },
        {
            "command": "vault doctor",
            "purpose": "Check local runtime dependencies.",
        },
    ]
    docs = [
        "docs/agent_first_usage.md",
        "docs/mcp_tool_reference.md",
        "docs/cli_reference.md",
        "docs/agent_install.md",
    ]
    payload = {
        "ok": True,
        "mode": mode,
        "message": "Humans should start with the small entrypoints. Agents and scheduled jobs should use MCP profiles and generated setup artifacts for the wider toolbox.",
        "everyday_entrypoints": everyday,
        "agent_mcp_profiles": agent,
        "maintenance_entrypoints": maintenance,
        "docs": docs,
        "next_action": "Run vault setup-agent for installation, or configure vault-mcp --tool-profile core for daily agent recall.",
    }
    if mode == "human":
        return {key: payload[key] for key in ["ok", "mode", "message", "everyday_entrypoints", "docs", "next_action"]}
    if mode == "agent":
        return {key: payload[key] for key in ["ok", "mode", "message", "agent_mcp_profiles", "docs", "next_action"]}
    if mode == "maintenance":
        return {key: payload[key] for key in ["ok", "mode", "message", "maintenance_entrypoints", "docs", "next_action"]}
    return payload


def cmd_guide(args: Any, *, json_print: Callable[[dict, bool], None]) -> None:
    """Print a compact guide for the agent-first CLI surface."""
    mode = getattr(args, "mode", "human") or "human"
    payload = guide_payload(mode)
    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, getattr(args, "pretty", False))
        return

    print("Vault-for-LLM guide")
    print()
    print(payload["message"])
    print()
    if "everyday_entrypoints" in payload:
        print("For humans, keep the surface small:")
        for item in payload["everyday_entrypoints"]:
            print(f"  - {item['command']}: {item['purpose']}")
        print()
    if "agent_mcp_profiles" in payload:
        print("For agents, prefer MCP profiles:")
        for item in payload["agent_mcp_profiles"]:
            print(f"  - {item['profile']}: {item['purpose']}")
        print()
    if "maintenance_entrypoints" in payload:
        print("For maintenance and automation:")
        for item in payload["maintenance_entrypoints"]:
            print(f"  - {item['command']}: {item['purpose']}")
        print()
    print("Docs:")
    for doc in payload["docs"]:
        print(f"  - {doc}")
    print()
    print(f"Next: {payload['next_action']}")
