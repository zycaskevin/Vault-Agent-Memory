"""Compact agent-first CLI guide."""

from __future__ import annotations

from typing import Callable, Any


def guide_payload(mode: str = "human", intent: str = "all") -> dict:
    """Return the compact agent-first command guide."""
    install_prompt = _consumer_install_prompt()
    install_contract = {
        "audience": "consumer",
        "memory_mode": "governed-auto",
        "human_questions": [
            "Language: Traditional Chinese, Simplified Chinese, or English?",
            "Vault layout: independent vault or shared vault?",
            "Connections: Obsidian, Supabase, both, or neither?",
            "Daily report time.",
        ],
        "agent_must_do": [
            "Run `vault quickstart` for the guided agent-assisted installer.",
            "Keep advanced flags hidden unless the user asks.",
            "Enable daily report generation.",
            "Allow only low-risk, sourced, gate-passing memories to enter automatically.",
            "Leave strategy, private, sensitive, conflicting, or low-trust memories in the daily report.",
            "Finish with a smoke check and show the daily report or GUI link.",
        ],
    }
    everyday = [
        {
            "intent": "install",
            "command": "vault quickstart",
            "purpose": "Guided install for agent-assisted builders. The agent asks only the small setup questions.",
        },
        {
            "intent": "daily",
            "command": "vault daily-report",
            "purpose": "Show the one-minute memory report for humans: what changed and which few items need a decision.",
        },
        {
            "intent": "daily",
            "command": "vault guide",
            "purpose": "Show the small recommended entrypoints and where advanced commands live.",
        },
        {
            "intent": "daily",
            "command": "vault gui",
            "purpose": "Open the local console for browsing documents, tasks, graph, and review queues.",
        },
        {
            "intent": "daily",
            "command": "vault search \"query\"",
            "purpose": "Find relevant reviewed knowledge.",
        },
        {
            "intent": "remember",
            "command": "vault remember \"Title\" --content \"...\" --reason \"...\"",
            "purpose": "Propose memory as a reviewable candidate instead of writing active knowledge directly.",
        },
        {
            "intent": "task",
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
            "intent": "maintenance",
            "command": "vault automation cycle --write-workspace",
            "purpose": "Run the closed-loop memory workspace for the next agent.",
        },
        {
            "intent": "maintenance",
            "command": "vault memory pipeline --write-candidates --write-report",
            "purpose": "Capture conversation lessons into gated candidates and write a receipt.",
        },
        {
            "intent": "maintenance",
            "command": "vault memory reflection --write-candidates",
            "purpose": "Run report-first Dream/reflection and write consolidation suggestions only.",
        },
        {
            "intent": "skills",
            "command": "vault skill upgrade-plan --installed-file installed-skills.json",
            "purpose": "Compare runtime Skill versions with the Vault registry without installing anything.",
        },
        {
            "intent": "maintenance",
            "command": "vault security doctor",
            "purpose": "Check GUI token and MCP identity hardening.",
        },
        {
            "intent": "maintenance",
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
        "intent": intent,
        "message": "Most agent-assisted builders should ask their agent to install and operate Vault. Daily use should be a short report, not a CLI lesson.",
        "agent_install_prompt": install_prompt,
        "consumer_install_contract": install_contract,
        "intent_shortcuts": [
            {"intent": "install", "use": "Set up or connect an agent"},
            {"intent": "daily", "use": "Search, browse, and continue normal work"},
            {"intent": "remember", "use": "Propose durable memory safely"},
            {"intent": "task", "use": "Continue a task without polluting long-term memory"},
            {"intent": "review", "use": "Review candidates, tasks, and Skill sync plans"},
            {"intent": "skills", "use": "Inspect Skill upgrades without runtime writes"},
            {"intent": "maintenance", "use": "Run scheduled curation and health checks"},
        ],
        "everyday_entrypoints": _filter_by_intent(everyday, intent),
        "agent_mcp_profiles": agent,
        "maintenance_entrypoints": _filter_by_intent(maintenance, intent),
        "docs": docs,
        "next_action": "Copy the agent_install_prompt into your agent. It should run `vault quickstart`, install agent-assisted governed-auto mode, and show the daily report.",
    }
    if mode == "human":
        keys = ["ok", "mode", "intent", "message", "intent_shortcuts", "everyday_entrypoints", "docs", "next_action"]
        if intent == "install":
            keys.insert(4, "agent_install_prompt")
            keys.insert(5, "consumer_install_contract")
        if intent in {"skills", "maintenance"}:
            keys.insert(-2, "maintenance_entrypoints")
        return {key: payload[key] for key in keys}
    if mode == "agent":
        keys = ["ok", "mode", "intent", "message", "agent_mcp_profiles", "docs", "next_action"]
        if intent == "install":
            keys.insert(4, "consumer_install_contract")
        return {key: payload[key] for key in keys}
    if mode == "maintenance":
        return {key: payload[key] for key in ["ok", "mode", "intent", "message", "maintenance_entrypoints", "docs", "next_action"]}
    return payload


def cmd_guide(args: Any, *, json_print: Callable[[dict, bool], None]) -> None:
    """Print a compact guide for the agent-first CLI surface."""
    mode = getattr(args, "mode", "human") or "human"
    intent = getattr(args, "intent", "all") or "all"
    payload = guide_payload(mode, intent)
    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, getattr(args, "pretty", False))
        return

    print("Vault-for-LLM guide")
    print()
    print(payload["message"])
    print()
    if intent == "install" and payload.get("agent_install_prompt"):
        print("Copy this to your agent:")
        print()
        print(payload["agent_install_prompt"])
        print()
        contract = payload.get("consumer_install_contract", {})
        if contract:
            print("The agent should ask only:")
            for question in contract.get("human_questions", []):
                print(f"  - {question}")
            print()
        print(f"Next: {payload['next_action']}")
        return

    print("Intent shortcuts:")
    for item in payload.get("intent_shortcuts", []):
        print(f"  - {item['intent']}: {item['use']}")
    print()
    if payload.get("everyday_entrypoints"):
        print("For humans, keep the surface small:")
        for item in payload["everyday_entrypoints"]:
            print(f"  - {item['command']}: {item['purpose']}")
        print()
    if payload.get("agent_mcp_profiles"):
        print("For agents, prefer MCP profiles:")
        for item in payload["agent_mcp_profiles"]:
            print(f"  - {item['profile']}: {item['purpose']}")
        print()
    if payload.get("maintenance_entrypoints"):
        print("For maintenance and automation:")
        for item in payload["maintenance_entrypoints"]:
            print(f"  - {item['command']}: {item['purpose']}")
        print()
    print("Docs:")
    for doc in payload["docs"]:
        print(f"  - {doc}")
    print()
    print(f"Next: {payload['next_action']}")


def _filter_by_intent(items: list[dict], intent: str) -> list[dict]:
    if intent in {"", "all", "review"}:
        return items
    return [item for item in items if item.get("intent") == intent]


def _consumer_install_prompt() -> str:
    return "\n".join(
        [
            "Install Vault-for-LLM for this project.",
            "Use the agent-assisted governed-auto memory mode.",
            "Run `vault quickstart` unless I ask for advanced setup-agent flags.",
            "Do not show advanced CLI flags unless I ask.",
            "Ask me only:",
            "1. Which language should Vault use: Traditional Chinese, Simplified Chinese, or English?",
            "2. Should this be an independent vault or a shared vault for multiple agents?",
            "3. Should Vault connect to Obsidian, Supabase, both, or neither?",
            "4. What time should the daily memory report run?",
            "After setup, run a smoke check and show me the daily report or local GUI link.",
            "Daily use should be: safe memories can be kept automatically; uncertain memories go into the report for my review.",
        ]
    )
