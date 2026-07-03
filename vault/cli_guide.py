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
        "docs/quickstart.md",
        "docs/agent_first_usage.md",
        "docs/gateway_security.md",
        "docs/mcp_tool_reference.md",
        "docs/cli_reference.md",
        "docs/agent_install.md",
    ]
    quickstart_5_minute = [
        "0:00 Install `vault-for-llm[mcp]` in your project environment.",
        "1:00 Run `vault quickstart` and answer the four setup questions.",
        "2:00 Ask your agent to run the generated local smoke check.",
        "3:00 Open `vault daily-report` to review what changed.",
        "5:00 Search one known phrase with `vault search \"query\" --json`.",
    ]
    faq = [
        {"q": "Do I need to learn every CLI command?", "a": "No. Start with `vault quickstart`, `vault daily-report`, and `vault search`."},
        {"q": "Does quickstart remove setup-agent?", "a": "No. `setup-agent` stays available for advanced templates and operator flags."},
        {"q": "Can Vault work without cloud services?", "a": "Yes. Core memory uses local SQLite and Markdown."},
        {"q": "Does Gateway write active knowledge?", "a": "No. Gateway writes create review candidates first."},
        {"q": "Where do uncertain memories go?", "a": "They stay in the daily report for review instead of entering active memory automatically."},
        {"q": "Should I use Obsidian on day one?", "a": "Only if you already use it. You can connect it later."},
        {"q": "Is Supabase required?", "a": "No. It is optional sharing infrastructure for hosted readers or remote candidates."},
        {"q": "How do I fix a missing vault.db?", "a": "Run `vault init --project-dir <project>` or point commands at the correct project with `--project-dir`."},
        {"q": "How long can search queries be?", "a": "Keep queries under 1000 characters. Store long source text first, then search short phrases."},
        {"q": "How do I expose Gateway safely?", "a": "Keep token auth on, use TLS or a trusted reverse proxy, restrict network access, and review audit logs."},
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
            {"intent": "faq", "use": "Answer common first-run and safety questions"},
        ],
        "everyday_entrypoints": _filter_by_intent(everyday, intent),
        "agent_mcp_profiles": agent,
        "maintenance_entrypoints": _filter_by_intent(maintenance, intent),
        "quickstart_5_minute": quickstart_5_minute,
        "faq": faq,
        "docs": docs,
        "next_action": "Copy the agent_install_prompt into your agent. It should run `vault quickstart`, install agent-assisted governed-auto mode, and show the daily report.",
    }
    if mode == "human":
        keys = ["ok", "mode", "intent", "message", "intent_shortcuts", "everyday_entrypoints", "docs", "next_action"]
        if intent == "install":
            keys.insert(4, "agent_install_prompt")
            keys.insert(5, "consumer_install_contract")
            keys.insert(6, "quickstart_5_minute")
            keys.insert(7, "faq")
        if intent == "faq":
            keys = ["ok", "mode", "intent", "message", "faq", "docs", "next_action"]
        if intent in {"skills", "maintenance"}:
            keys.insert(-2, "maintenance_entrypoints")
        return {key: payload[key] for key in keys}
    if mode == "agent":
        keys = ["ok", "mode", "intent", "message", "agent_mcp_profiles", "docs", "next_action"]
        if intent == "install":
            keys.insert(4, "consumer_install_contract")
            keys.insert(5, "quickstart_5_minute")
            keys.insert(6, "faq")
        if intent == "faq":
            keys = ["ok", "mode", "intent", "message", "faq", "docs", "next_action"]
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

    print("Vault Agent Memory guide")
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
        print("5-minute quickstart:")
        for step in payload.get("quickstart_5_minute", []):
            print(f"  - {step}")
        print()
        print("FAQ:")
        for item in payload.get("faq", [])[:10]:
            print(f"  - {item['q']} {item['a']}")
        print()
        print(f"Next: {payload['next_action']}")
        return
    if intent == "faq" and payload.get("faq"):
        print("FAQ:")
        for item in payload["faq"]:
            print(f"  - {item['q']} {item['a']}")
        print()
        print("Docs:")
        for doc in payload["docs"]:
            print(f"  - {doc}")
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
    if intent == "faq":
        return []
    return [item for item in items if item.get("intent") == intent]


def _consumer_install_prompt() -> str:
    return "\n".join(
        [
            "Install Vault Agent Memory for this project with vault-for-llm.",
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
