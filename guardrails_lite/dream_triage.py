"""DL-6 local-model-assisted Dream triage packet builder.

The packet is prompt-only and local-model-ready.  It intentionally does not call
Ollama/vLLM or any network endpoint; it only packages safe metadata already
present in Dream review reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ALLOWED_DECISIONS = ["approved", "merge_suggested", "discarded", "blocked", "ask_arthur"]


def build_local_model_triage_packet(
    review_report: dict[str, Any],
    *,
    model: str = "qwen3.6:35b",
    max_items: int = 20,
) -> dict[str, Any]:
    """Build a redacted prompt packet for optional local-model triage."""
    _validate_review_report_safe(review_report)
    items = list((review_report.get("reviewer_ux") or {}).get("action_items") or [])
    if max_items and max_items > 0:
        items = items[:max_items]
    safe_items = [_safe_triage_item(item) for item in items]
    return {
        "schema": "guardrails.dream.local_model_triage.v1",
        "report_only": True,
        "prompt_only": True,
        "local_model_only": True,
        "network_invoked": False,
        "formal_knowledge_written": False,
        "raw_written": False,
        "sync_invoked": False,
        "model": str(model or "qwen3.6:35b"),
        "date": review_report.get("date"),
        "counts": {
            "items": len(safe_items),
            "clear_items": sum(1 for item in safe_items if item["privacy_status"] == "clear"),
            "blocked_or_private_items": sum(1 for item in safe_items if item["privacy_status"] != "clear"),
        },
        "system_instructions": [
            "You are a local Guardrails Dream triage assistant.",
            "Use only the safe metadata in this packet.",
            "Do not promote, merge, delete, sync, or write formal knowledge.",
            "Do not infer private context from redacted fields.",
            "Return short reviewer-facing rationale per item.",
        ],
        "output_contract": {
            "allowed_decisions": list(_ALLOWED_DECISIONS),
            "must_include_reason": True,
            "max_reason_chars": 280,
        },
        "items": safe_items,
    }


def write_local_model_triage_packet(path: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_review_report_safe(report: dict[str, Any]) -> None:
    required_false = ["auto_promote", "formal_knowledge_written", "raw_written", "sync_invoked"]
    if report.get("report_only") is not True or any(report.get(key) is not False for key in required_false):
        raise ValueError("local model triage requires a report-only Dream review report")


def _safe_triage_item(item: dict[str, Any]) -> dict[str, Any]:
    privacy_status = _safe_text(item.get("privacy_status") or "unknown")
    recommended_action = _safe_action(item.get("recommended_action"))
    return {
        "number": int(item.get("number") or 0),
        "candidate_id": _safe_text(item.get("candidate_id")),
        "title": _safe_text(item.get("title")),
        "recommended_action": recommended_action,
        "suggested_decision": _safe_decision(item.get("suggested_decision")),
        "privacy_status": privacy_status,
        "dedupe_status": _safe_text(item.get("dedupe_status") or "unknown"),
        "allowed_decisions": list(_ALLOWED_DECISIONS),
        "triage_question": _triage_question(recommended_action, privacy_status),
    }


def _safe_action(value: Any) -> str:
    text = _safe_text(value or "review")
    return text if text in {"promote", "merge", "discard", "block", "ask_arthur", "review"} else "review"


def _safe_decision(value: Any) -> str:
    text = _safe_text(value or "ask_arthur")
    return text if text in _ALLOWED_DECISIONS else "ask_arthur"


def _safe_text(value: Any) -> str:
    text = str(value or "")
    return " ".join(text.replace("`", "'").replace("\r", " ").replace("\n", " ").split())


def _triage_question(action: str, privacy_status: str) -> str:
    if privacy_status != "clear":
        return "Explain why this item should remain blocked/private or require Arthur review."
    if action == "promote":
        return "Explain why this clear unique item is worth approving, using safe metadata only."
    if action == "merge":
        return "Explain whether this should be merged instead of added as a new knowledge item."
    if action == "discard":
        return "Explain why this candidate is not durable enough to keep."
    return "Explain the safest next reviewer decision."
