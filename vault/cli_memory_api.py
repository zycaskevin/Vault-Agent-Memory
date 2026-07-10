"""CLI helpers for Vault Memory API operational checks."""

from __future__ import annotations

import argparse
from typing import Any, Callable

from .memory_provider_parity import provider_adapter_parity_report


def add_memory_api_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("memory-api", help="Vault Memory API operational checks")
    memory_api_sub = parser.add_subparsers(dest="memory_api_action")

    p = memory_api_sub.add_parser(
        "parity-report",
        help="Compare legacy Gateway results with provider-backed preview adapters",
    )
    p.add_argument("--agent-id", required=True, help="Agent id used for read-policy checks")
    p.add_argument("--search-query", action="append", default=[], help="Search query probe; may be repeated")
    p.add_argument("--read-range", action="append", default=[], help="Read probe as MEMORY_ID:START-END; may be repeated")
    p.add_argument("--limit", type=int, default=10, help="Search result limit for every search probe")
    p.add_argument("--include-private", action="store_true", help="Allow owner/allow-list private reads for this agent")
    p.add_argument(
        "--max-sensitivity",
        choices=["low", "medium", "high", "restricted"],
        default="low",
        help="Highest sensitivity readable by this agent",
    )
    p.add_argument("--json", action="store_true", help="輸出 JSON")
    p.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")


def cmd_memory_api(
    args: Any,
    *,
    find_project_dir: Callable[[], Any],
    json_print: Callable[..., None],
) -> None:
    action = getattr(args, "memory_api_action", "")
    if action != "parity-report":
        print("用法: vault memory-api parity-report --agent-id AGENT [--search-query TEXT] [--read-range ID:START-END]")
        return

    search_probes = [
        {"query": str(query or ""), "limit": int(getattr(args, "limit", 10) or 10)}
        for query in getattr(args, "search_query", [])
    ]
    read_probes = [_parse_read_range_probe(value) for value in getattr(args, "read_range", [])]
    if not search_probes and not read_probes:
        payload = {
            "status": "error",
            "ok": False,
            "error": "parity_probe_required",
            "message": "Provide at least one --search-query or --read-range probe.",
            "safety": {
                "changes_default_authority": False,
                "returns_raw_memory_content": False,
                "returns_raw_query_text": False,
            },
        }
    elif any("error" in probe for probe in read_probes):
        payload = {
            "status": "error",
            "ok": False,
            "error": "invalid_read_range",
            "read_range_errors": [probe for probe in read_probes if "error" in probe],
            "safety": {
                "changes_default_authority": False,
                "returns_raw_memory_content": False,
                "returns_raw_query_text": False,
            },
        }
    else:
        payload = provider_adapter_parity_report(
            find_project_dir(),
            agent_id=getattr(args, "agent_id", "") or "",
            search_probes=search_probes,
            read_probes=read_probes,
            include_private=bool(getattr(args, "include_private", False)),
            max_sensitivity=getattr(args, "max_sensitivity", "low") or "low",
        )

    if getattr(args, "json", False) or getattr(args, "pretty", False):
        json_print(payload, pretty=bool(getattr(args, "pretty", False)))
        return
    _print_parity_report(payload)


def _parse_read_range_probe(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    try:
        memory_raw, range_raw = text.split(":", 1)
        start_raw, end_raw = range_raw.split("-", 1)
        memory_id = int(memory_raw)
        line_start = int(start_raw)
        line_end = int(end_raw)
    except (TypeError, ValueError):
        return {"input": text, "error": "expected MEMORY_ID:START-END"}
    return {"memory_id": memory_id, "line_start": line_start, "line_end": line_end}


def _print_parity_report(payload: dict[str, Any]) -> None:
    print("Vault Memory API provider parity report")
    print(f"  status: {payload.get('status', '')}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary:
        print(f"  search: {summary.get('search_matches', 0)}/{summary.get('search_probes', 0)}")
        print(f"  read: {summary.get('read_matches', 0)}/{summary.get('read_probes', 0)}")
        print(f"  mismatches: {summary.get('mismatches', 0)}")
    if payload.get("error"):
        print(f"  error: {payload.get('error')}")
        print(f"  message: {payload.get('message', '')}")
