"""B7 report-only queue export.

This module is intentionally deterministic, local, and read-only.  It only emits
safe metadata handles for review queues; it never promotes drafts, merges rows,
or exports raw knowledge content.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_CONVERGENCE_THRESHOLD = 0.8
DEFAULT_FRESHNESS_THRESHOLD = 0.8
_SAFE_REVIEW_ACTIONS = {
    "review_duplicate",
    "review_convergence",
    "review_freshness",
    "repair_provenance",
    "ask_arthur",
}


_SAFE_KNOWLEDGE_COLUMNS = """
    id, title, layer, category, tags, trust, content_hash, source,
    created_at, updated_at, convergence_status, convergence_score,
    convergence_checked_at, last_verified, freshness
"""


def build_b7_report(
    db_path: str | Path = "guardrails.db",
    raw_dir: str | Path | None = None,
    compiled_dir: str | Path | None = None,
    limit: int | None = None,
    convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
    freshness_threshold: float = DEFAULT_FRESHNESS_THRESHOLD,
) -> dict[str, Any]:
    """Build a deterministic B7 review queue report from safe metadata only."""
    db_path = Path(db_path)
    project_dir = db_path.parent if db_path.parent != Path("") else Path.cwd()
    raw_dir = Path(raw_dir) if raw_dir is not None else project_dir / "raw"
    compiled_dir = Path(compiled_dir) if compiled_dir is not None else project_dir / "compiled"

    rows = _load_knowledge_rows(db_path)
    node_counts = _load_node_counts(db_path)

    items: list[dict[str, Any]] = []
    items.extend(_duplicate_title_items(rows))
    items.extend(_duplicate_content_hash_items(rows))
    items.extend(_convergence_items(rows, convergence_threshold))
    items.extend(_freshness_items(rows, freshness_threshold))
    items.extend(_provenance_gap_items(rows, raw_dir, compiled_dir, node_counts))

    items = sorted(items, key=_item_sort_key)
    if limit is not None and limit > 0:
        items = items[:limit]

    counts_by_issue_type: dict[str, int] = {}
    for item in items:
        counts_by_issue_type[item["issue_type"]] = counts_by_issue_type.get(item["issue_type"], 0) + 1

    return {
        "schema": "guardrails.b7.report.v1",
        "report_only": True,
        "auto_promote": False,
        "destructive_merge": False,
        "private_public_sync": False,
        "remote_overwrite": False,
        "thresholds": {
            "convergence_score": convergence_threshold,
            "freshness": freshness_threshold,
        },
        "counts": {
            "knowledge_rows": len(rows),
            "items": len(items),
            "by_issue_type": dict(sorted(counts_by_issue_type.items())),
        },
        "items": items,
    }


def write_b7_report(path: str | Path, report: dict[str, Any]) -> None:
    """Write report JSON with stable key ordering and UTF-8 encoding."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Guardrails DB not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_knowledge_rows(db_path: Path) -> list[dict[str, Any]]:
    with _connect_readonly(db_path) as conn:
        rows = conn.execute(f"SELECT {_SAFE_KNOWLEDGE_COLUMNS} FROM knowledge ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def _load_node_counts(db_path: Path) -> dict[int, int]:
    with _connect_readonly(db_path) as conn:
        try:
            rows = conn.execute(
                "SELECT knowledge_id, COUNT(*) AS node_count FROM knowledge_nodes GROUP BY knowledge_id"
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    return {int(row["knowledge_id"]): int(row["node_count"]) for row in rows}


def _duplicate_title_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        normalized = normalize_title(row.get("title", ""))
        if normalized:
            groups.setdefault(normalized, []).append(row)

    items: list[dict[str, Any]] = []
    for normalized_title, group in sorted(groups.items()):
        if len(group) <= 1:
            continue
        items.append(
            _review_item(
                {
                    "issue_type": "duplicate_title",
                    "safe_reason": "same normalized title across multiple knowledge rows",
                    "recommended_action": "review_duplicate",
                    "normalized_title": normalized_title,
                    "knowledge_ids": [int(row["id"]) for row in group],
                    "titles": _title_refs(group),
                    "count": len(group),
                    "source_refs": _source_refs_for_group(group),
                }
            )
        )
    return items


def _duplicate_content_hash_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        content_hash = str(row.get("content_hash") or "").strip()
        if content_hash:
            groups.setdefault(content_hash, []).append(row)

    items: list[dict[str, Any]] = []
    for content_hash, group in sorted(groups.items()):
        if len(group) <= 1:
            continue
        items.append(
            _review_item(
                {
                    "issue_type": "duplicate_content_hash",
                    "safe_reason": "same non-empty content_hash across multiple knowledge rows",
                    "recommended_action": "review_duplicate",
                    "content_hash": content_hash,
                    "knowledge_ids": [int(row["id"]) for row in group],
                    "titles": _title_refs(group),
                    "count": len(group),
                    "source_refs": _source_refs_for_group(group),
                }
            )
        )
    return items


def _convergence_items(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("convergence_status") or "unknown")
        score = row.get("convergence_score")
        low_score = score is None or float(score) < threshold
        incomplete = status != "complete"
        if not (incomplete or low_score):
            continue
        items.append(
            _review_item(
                {
                    "issue_type": "low_convergence",
                    "safe_reason": "convergence_status is not complete or convergence_score is below threshold",
                    "recommended_action": "review_convergence",
                    "knowledge_id": int(row["id"]),
                    "title": row.get("title", ""),
                    "convergence_status": status,
                    "convergence_score": score,
                    "threshold": threshold,
                    "source_refs": _source_refs_for_row(row),
                }
            )
        )
    return items


def _freshness_items(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        freshness = row.get("freshness")
        freshness_value = 1.0 if freshness is None else float(freshness)
        if freshness_value >= threshold:
            continue
        items.append(
            _review_item(
                {
                    "issue_type": "stale_freshness",
                    "safe_reason": "freshness is below threshold",
                    "recommended_action": "review_freshness",
                    "knowledge_id": int(row["id"]),
                    "title": row.get("title", ""),
                    "freshness": freshness_value,
                    "threshold": threshold,
                    "last_verified": row.get("last_verified", ""),
                    "source_refs": _source_refs_for_row(row),
                }
            )
        )
    return items


def _provenance_gap_items(
    rows: list[dict[str, Any]],
    raw_dir: Path,
    compiled_dir: Path,
    node_counts: dict[int, int],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        kid = int(row["id"])
        raw_handle = _raw_handle(row, raw_dir)
        compiled_handle = _compiled_handle(row, compiled_dir)
        node_count = int(node_counts.get(kid, 0))
        missing = {
            "raw": not raw_handle["exists"],
            "compiled": not compiled_handle["exists"],
            "document_map_nodes": node_count == 0,
        }
        if not any(missing.values()):
            continue
        items.append(
            _review_item(
                {
                    "issue_type": "provenance_gap",
                    "safe_reason": "knowledge row has missing raw/compiled path handle or Document Map nodes",
                    "recommended_action": "repair_provenance",
                    "knowledge_id": kid,
                    "title": row.get("title", ""),
                    "missing": missing,
                    "has_raw": raw_handle["exists"],
                    "has_compiled": compiled_handle["exists"],
                    "has_document_map_nodes": node_count > 0,
                    "node_count": node_count,
                    "source_refs": [
                        {"kind": "db", "handle": f"knowledge:{kid}", "exists": True},
                        raw_handle,
                        compiled_handle,
                        {
                            "kind": "document_map",
                            "handle": f"knowledge_nodes:{kid}",
                            "exists": node_count > 0,
                            "count": node_count,
                        },
                    ],
                }
            )
        )
    return items


def normalize_title(title: str) -> str:
    """Normalize titles for exact/case/spacing duplicate detection."""
    normalized = unicodedata.normalize("NFKC", title or "")
    normalized = normalized.casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def _compiled_handle(row: dict[str, Any], compiled_dir: Path) -> dict[str, Any]:
    layer = str(row.get("layer") or "L3")
    category = str(row.get("category") or "general")
    safe_title = str(row.get("title") or "untitled").replace("/", "-").replace(" ", "_")
    path = compiled_dir / f"{layer}-{category}" / f"{safe_title}.md"
    return {
        "kind": "compiled",
        "handle": _safe_display_path(path),
        "exists": path.exists(),
    }


def _raw_handle(row: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    source = str(row.get("source") or "").strip()
    if not source:
        return {"kind": "raw", "handle": "", "exists": False, "source": ""}

    source_path = Path(source)
    if source_path.is_absolute():
        path = source_path
    elif source_path.parts and source_path.parts[0] == raw_dir.name:
        path = raw_dir.parent / source_path
    else:
        path = raw_dir / source_path

    return {
        "kind": "raw",
        "handle": _safe_display_path(path),
        "exists": path.exists(),
        "source": source,
    }


def _source_refs_for_group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for row in rows:
        refs.extend(_source_refs_for_row(row))
    return refs


def _source_refs_for_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    refs = [{"kind": "db", "handle": f"knowledge:{int(row['id'])}", "exists": True}]
    source = str(row.get("source") or "").strip()
    if source:
        refs.append({"kind": "source", "handle": source, "exists": None})
    return refs


def _title_refs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": int(row["id"]), "title": row.get("title", "")} for row in rows]


def _safe_display_path(path: Path) -> str:
    return path.as_posix()


def _review_item(item: dict[str, Any]) -> dict[str, Any]:
    action = item.get("recommended_action")
    if action not in _SAFE_REVIEW_ACTIONS:
        raise ValueError(f"unsafe B7 action: {action}")
    return item


def _item_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    ids = item.get("knowledge_ids")
    if ids:
        first_id = min(int(value) for value in ids)
    else:
        first_id = int(item.get("knowledge_id") or 0)
    return (str(item.get("issue_type") or ""), first_id, json.dumps(item, sort_keys=True, ensure_ascii=False))
