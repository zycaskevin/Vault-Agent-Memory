"""DL-9 runtime-only historical trend store helpers.

The history store is intentionally count-only.  It records dashboard/monthly metric
snapshots as local JSONL runtime artifacts, never formal knowledge, raw knowledge,
or compiled source material.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ALLOWED_AGGREGATE_KEYS = {
    "schema",
    "count_only",
    "report_only",
    "contains_private_payload",
    "generated_at",
    "dream_candidates_total",
    "dream_candidates_ready_for_review",
    "dream_candidates_blocked",
    "dream_candidates_need_arthur",
    "last_dream_review_at",
    "librarian_open_duplicates",
    "librarian_open_stale",
    "librarian_open_low_convergence",
    "librarian_open_provenance_gaps",
    "librarian_review_items_total",
    "last_librarian_review_at",
}
_FORBIDDEN_PAYLOAD_KEYS = {
    "candidate_id",
    "candidate_ids",
    "knowledge_id",
    "knowledge_ids",
    "title",
    "proposed_title",
    "summary",
    "content_draft",
    "raw_content",
    "source_refs",
    "transcript",
    "private_context",
}
_ALLOWED_SNAPSHOT_KEYS = {
    "schema",
    "snapshot_date",
    "generated_at",
    "count_only",
    "report_only",
    "contains_private_payload",
    "source_schema",
    "source_generated_at",
    "last_dream_review_at",
    "last_librarian_review_at",
    "metrics",
}
_METRIC_KEYS = [
    "dream_candidates_total",
    "dream_candidates_ready_for_review",
    "dream_candidates_blocked",
    "dream_candidates_need_arthur",
    "librarian_open_duplicates",
    "librarian_open_stale",
    "librarian_open_low_convergence",
    "librarian_open_provenance_gaps",
    "librarian_review_items_total",
]
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def build_trend_snapshot(
    dashboard_aggregate: dict[str, Any],
    *,
    snapshot_date: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a count-only trend snapshot from a safe dashboard aggregate."""
    _validate_snapshot_date(snapshot_date)
    _validate_dashboard_aggregate(dashboard_aggregate)
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    _validate_iso_timestamp(generated_at, field="generated_at")
    metrics = {key: _coerce_count(dashboard_aggregate.get(key), field=key) for key in _METRIC_KEYS}
    return {
        "schema": "guardrails.report_history.snapshot.v1",
        "snapshot_date": snapshot_date,
        "generated_at": generated_at,
        "count_only": True,
        "report_only": True,
        "contains_private_payload": False,
        "source_schema": str(dashboard_aggregate.get("schema") or ""),
        "source_generated_at": str(dashboard_aggregate.get("generated_at") or ""),
        "last_dream_review_at": str(dashboard_aggregate.get("last_dream_review_at") or ""),
        "last_librarian_review_at": str(dashboard_aggregate.get("last_librarian_review_at") or ""),
        "metrics": metrics,
    }


def append_trend_snapshot(path: str | Path, snapshot: dict[str, Any]) -> None:
    """Append or replace a snapshot by `snapshot_date` in a local JSONL history file."""
    _validate_snapshot(snapshot)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_history_records(output_path)
    by_date = {str(record["snapshot_date"]): record for record in records}
    by_date[str(snapshot["snapshot_date"])] = snapshot
    ordered = [by_date[key] for key in sorted(by_date)]
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in ordered),
        encoding="utf-8",
    )
    tmp_path.replace(output_path)


def build_trend_summary(path: str | Path, *, window: int | None = None) -> dict[str, Any]:
    """Summarize the latest/previous count-only trend snapshots and numeric deltas."""
    records = _read_history_records(Path(path))
    records = sorted(records, key=lambda record: str(record["snapshot_date"]))
    if window is not None:
        records = records[-max(0, int(window)) :]
    latest = records[-1] if records else None
    previous = records[-2] if len(records) >= 2 else None
    return {
        "schema": "guardrails.report_history.summary.v1",
        "count_only": True,
        "report_only": True,
        "contains_private_payload": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history_records": len(records),
        "latest": _public_record(latest),
        "previous": _public_record(previous),
        "deltas": _deltas(previous, latest),
    }


def validate_history_path(project_dir: str | Path, history_path: str | Path) -> Path:
    """Ensure history stays outside project raw/compiled source-of-truth dirs."""
    project = Path(project_dir).expanduser().resolve()
    resolved = Path(history_path).expanduser().resolve()
    raw_dir = (project / "raw").resolve()
    compiled_dir = (project / "compiled").resolve()
    if _is_relative_to(resolved, raw_dir) or _is_relative_to(resolved, compiled_dir):
        raise ValueError("history path must not be under project raw/ or compiled/")
    return resolved


def _validate_dashboard_aggregate(aggregate: dict[str, Any]) -> None:
    if aggregate.get("schema") != "guardrails.dashboard.aggregate.v1":
        raise ValueError("unknown dashboard aggregate schema")
    if aggregate.get("count_only") is not True or aggregate.get("report_only") is not True:
        raise ValueError("dashboard aggregate must be count-only/report-only")
    if aggregate.get("contains_private_payload") is not False:
        raise ValueError("dashboard aggregate contains private payload")
    keys = set(aggregate)
    forbidden = sorted(keys & _FORBIDDEN_PAYLOAD_KEYS)
    if forbidden:
        raise ValueError(f"forbidden payload field in dashboard aggregate: {', '.join(forbidden)}")
    unknown = sorted(keys - _ALLOWED_AGGREGATE_KEYS)
    if unknown:
        raise ValueError(f"unknown dashboard aggregate metric: {', '.join(unknown)}")
    _validate_iso_timestamp(str(aggregate.get("generated_at") or ""), field="generated_at")
    _validate_optional_date(str(aggregate.get("last_dream_review_at") or ""), field="last_dream_review_at")
    _validate_optional_iso_timestamp(str(aggregate.get("last_librarian_review_at") or ""), field="last_librarian_review_at")
    for key in _METRIC_KEYS:
        _coerce_count(aggregate.get(key), field=key)


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema") != "guardrails.report_history.snapshot.v1":
        raise ValueError("unknown trend snapshot schema")
    if snapshot.get("count_only") is not True or snapshot.get("report_only") is not True:
        raise ValueError("trend snapshot must be count-only/report-only")
    if snapshot.get("contains_private_payload") is not False:
        raise ValueError("trend snapshot contains private payload")
    _validate_snapshot_date(str(snapshot.get("snapshot_date") or ""))
    keys = set(snapshot)
    forbidden = sorted(keys & _FORBIDDEN_PAYLOAD_KEYS)
    if forbidden:
        raise ValueError(f"forbidden payload field in trend snapshot: {', '.join(forbidden)}")
    unknown_keys = sorted(keys - _ALLOWED_SNAPSHOT_KEYS)
    if unknown_keys:
        raise ValueError(f"unknown trend snapshot field: {', '.join(unknown_keys)}")
    metrics = snapshot.get("metrics") or {}
    source_schema = str(snapshot.get("source_schema") or "")
    if source_schema != "guardrails.dashboard.aggregate.v1":
        raise ValueError("source_schema must be guardrails.dashboard.aggregate.v1")
    _validate_iso_timestamp(str(snapshot.get("generated_at") or ""), field="generated_at")
    _validate_optional_iso_timestamp(str(snapshot.get("source_generated_at") or ""), field="source_generated_at")
    _validate_optional_date(str(snapshot.get("last_dream_review_at") or ""), field="last_dream_review_at")
    _validate_optional_iso_timestamp(str(snapshot.get("last_librarian_review_at") or ""), field="last_librarian_review_at")
    unknown = sorted(set(metrics) - set(_METRIC_KEYS))
    if unknown:
        raise ValueError(f"unknown trend metric: {', '.join(unknown)}")
    for key in _METRIC_KEYS:
        _coerce_count(metrics.get(key), field=key)


def _validate_snapshot_date(value: str) -> None:
    if not _DATE_RE.fullmatch(value):
        raise ValueError("snapshot_date must be YYYY-MM-DD")
    datetime.strptime(value, "%Y-%m-%d")


def _validate_optional_date(value: str, *, field: str) -> None:
    if not value:
        return
    if not _DATE_RE.fullmatch(value):
        raise ValueError(f"{field} must be YYYY-MM-DD")
    datetime.strptime(value, "%Y-%m-%d")


def _validate_iso_timestamp(value: str, *, field: str) -> None:
    if not value:
        raise ValueError(f"{field} must be ISO timestamp")
    _parse_iso_timestamp(value, field=field)


def _validate_optional_iso_timestamp(value: str, *, field: str) -> None:
    if not value:
        return
    _parse_iso_timestamp(value, field=field)


def _parse_iso_timestamp(value: str, *, field: str) -> None:
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO timestamp") from exc


def _coerce_count(value: Any, *, field: str) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"metric must be an integer count: {field}")
    return value


def _read_history_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive parse detail
            raise ValueError(f"invalid history JSONL at line {line_no}: {exc.msg}") from exc
        _validate_snapshot(record)
        records.append(record)
    return records


def _public_record(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "snapshot_date": record["snapshot_date"],
        "generated_at": record.get("generated_at", ""),
        "metrics": {key: int((record.get("metrics") or {}).get(key) or 0) for key in _METRIC_KEYS},
    }


def _deltas(previous: dict[str, Any] | None, latest: dict[str, Any] | None) -> dict[str, int]:
    if not previous or not latest:
        return {key: 0 for key in _METRIC_KEYS}
    prev_metrics = previous.get("metrics") or {}
    latest_metrics = latest.get("metrics") or {}
    return {key: int(latest_metrics.get(key) or 0) - int(prev_metrics.get(key) or 0) for key in _METRIC_KEYS}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
