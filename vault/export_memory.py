"""Read-only Markdown and JSON exports for active Vault knowledge."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


UNSAFE_FILENAME = re.compile(r"[\\/:*?\"<>|]+")


def export_memory_markdown(
    *,
    project_dir: str | Path,
    bundle_dir: str | Path,
    category: str | None = None,
    tag: str | None = None,
    layer: str | None = None,
    limit: int | None = None,
    min_trust: float = 0.0,
    include_private: bool = False,
    include_restricted: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export active knowledge as one Markdown file per memory plus a manifest."""
    rows, skipped_by_tag = _select_rows(
        project_dir=project_dir,
        category=category,
        tag=tag,
        layer=layer,
        limit=limit,
        min_trust=min_trust,
        include_private=include_private,
        include_restricted=include_restricted,
    )
    destination = Path(bundle_dir)
    entries: list[dict[str, Any]] = []
    paths: list[str] = []

    for row in rows:
        rel = _markdown_path(row)
        path = destination / rel
        paths.append(str(path))
        entries.append(_manifest_entry(row, path=rel))
        if dry_run:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_markdown(row), encoding="utf-8")

    manifest_path = destination / "manifest.json"
    paths.insert(0, str(manifest_path))
    manifest = _manifest_payload(
        project_dir=project_dir,
        bundle_dir=destination,
        format="markdown",
        matched=len(rows),
        written=0 if dry_run else len(rows) + 1,
        dry_run=dry_run,
        filters=_filters(category, tag, layer, limit, min_trust, include_private, include_restricted),
        skipped_by_tag=skipped_by_tag,
        entries=entries,
    )
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    return {
        "status": "preview" if dry_run else "ok",
        "format": "markdown",
        "dry_run": dry_run,
        "bundle_dir": str(destination),
        "matched": len(rows),
        "written": 0 if dry_run else len(rows) + 1,
        "paths": paths,
        "manifest": manifest,
        "skipped": manifest["skipped"],
        "next_action": "Inspect the Markdown files, then import selected notes with vault import <file> if needed.",
    }


def export_memory_json(
    *,
    project_dir: str | Path,
    bundle_dir: str | Path,
    category: str | None = None,
    tag: str | None = None,
    layer: str | None = None,
    limit: int | None = None,
    min_trust: float = 0.0,
    include_private: bool = False,
    include_restricted: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export active knowledge as a portable JSON snapshot."""
    rows, skipped_by_tag = _select_rows(
        project_dir=project_dir,
        category=category,
        tag=tag,
        layer=layer,
        limit=limit,
        min_trust=min_trust,
        include_private=include_private,
        include_restricted=include_restricted,
    )
    destination = Path(bundle_dir)
    json_path = destination / "knowledge.json"
    manifest_path = destination / "manifest.json"
    paths = [str(manifest_path), str(json_path)]
    knowledge = [_json_row(row) for row in rows]
    manifest = _manifest_payload(
        project_dir=project_dir,
        bundle_dir=destination,
        format="json",
        matched=len(rows),
        written=0 if dry_run else 2,
        dry_run=dry_run,
        filters=_filters(category, tag, layer, limit, min_trust, include_private, include_restricted),
        skipped_by_tag=skipped_by_tag,
        entries=[_manifest_entry(row, path="knowledge.json") for row in rows],
    )
    snapshot = {
        "schema": "vault.memory.export.v1",
        "format": "json",
        "exported_at": manifest["exported_at"],
        "source_project": manifest["source_project"],
        "filters": manifest["filters"],
        "counts": {"knowledge": len(knowledge)},
        "knowledge": knowledge,
    }
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    return {
        "status": "preview" if dry_run else "ok",
        "format": "json",
        "dry_run": dry_run,
        "bundle_dir": str(destination),
        "matched": len(rows),
        "written": 0 if dry_run else 2,
        "paths": paths,
        "manifest": manifest,
        "snapshot": snapshot if dry_run else {"path": str(json_path), "counts": snapshot["counts"]},
        "skipped": manifest["skipped"],
        "next_action": "Use knowledge.json as a machine-readable backup, or transform it before candidate-first import.",
    }


def _select_rows(
    *,
    project_dir: str | Path,
    category: str | None,
    tag: str | None,
    layer: str | None,
    limit: int | None,
    min_trust: float,
    include_private: bool,
    include_restricted: bool,
) -> tuple[list[dict[str, Any]], int]:
    project_path = Path(project_dir)
    db_path = project_path / "vault.db"
    with _connect_readonly(db_path) as conn:
        rows = _load_rows(
            conn,
            category=category,
            layer=layer,
            min_trust=min_trust,
            include_private=include_private,
            include_restricted=include_restricted,
        )

    skipped_by_tag = 0
    if tag:
        before = len(rows)
        rows = [row for row in rows if tag in _split_tags(row.get("tags"))]
        skipped_by_tag = before - len(rows)
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    return rows, skipped_by_tag


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"vault.db not found at {db_path}")
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_rows(
    conn: sqlite3.Connection,
    *,
    category: str | None,
    layer: str | None,
    min_trust: float,
    include_private: bool,
    include_restricted: bool,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM knowledge WHERE trust >= ? AND COALESCE(status, 'active') != 'archived'"
    params: list[Any] = [min_trust]
    if category:
        query += " AND category = ?"
        params.append(category)
    if layer:
        query += " AND layer = ?"
        params.append(layer)
    if not include_private:
        query += " AND COALESCE(scope, 'project') != 'private'"
    if not include_restricted:
        query += " AND COALESCE(sensitivity, 'low') != 'restricted'"
    query += " ORDER BY id ASC"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def _render_markdown(row: dict[str, Any]) -> str:
    body = str(row.get("content_raw") or "").strip()
    title = str(row.get("title") or f"Vault #{row['id']}")
    if not body.startswith("#"):
        body = f"# {title}\n\n{body}" if body else f"# {title}"
    return f"{_frontmatter(row)}\n\n{body}\n"


def _frontmatter(row: dict[str, Any]) -> str:
    tags = "[" + ", ".join(_yaml_string(tag) for tag in _split_tags(row.get("tags"))) + "]"
    allowed_agents = "[" + ", ".join(_yaml_string(agent) for agent in _split_tags(row.get("allowed_agents"))) + "]"
    lines = [
        "---",
        f"vault_id: {row['id']}",
        f"title: {_yaml_string(row.get('title', ''))}",
        f"category: {_yaml_string(row.get('category', 'general'))}",
        f"tags: {tags}",
        f"layer: {_yaml_string(row.get('layer', 'L3'))}",
        f"trust: {float(row.get('trust') or 0):g}",
        f"source: {_yaml_string(row.get('source', ''))}",
        f"scope: {_yaml_string(row.get('scope', 'project'))}",
        f"sensitivity: {_yaml_string(row.get('sensitivity', 'low'))}",
        f"owner_agent: {_yaml_string(row.get('owner_agent', ''))}",
        f"allowed_agents: {allowed_agents}",
        f"memory_type: {_yaml_string(row.get('memory_type', 'knowledge'))}",
        f"expires_at: {_yaml_string(row.get('expires_at', ''))}",
        f"valid_from: {_yaml_string(row.get('valid_from', ''))}",
        f"valid_until: {_yaml_string(row.get('valid_until', ''))}",
        f"supersedes_id: {row.get('supersedes_id') or ''}",
        f"created_at: {_yaml_string(row.get('created_at', ''))}",
        f"updated_at: {_yaml_string(row.get('updated_at', ''))}",
        "---",
    ]
    return "\n".join(lines)


def _manifest_payload(
    *,
    project_dir: str | Path,
    bundle_dir: Path,
    format: str,
    matched: int,
    written: int,
    dry_run: bool,
    filters: dict[str, Any],
    skipped_by_tag: int,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "vault.memory.export.manifest.v1",
        "format": format,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_project": str(Path(project_dir)),
        "bundle_dir": str(bundle_dir),
        "dry_run": dry_run,
        "matched": matched,
        "written": written,
        "filters": filters,
        "skipped": {
            "tag_filter": skipped_by_tag,
            "private_scope_excluded": not filters["include_private"],
            "restricted_sensitivity_excluded": not filters["include_restricted"],
        },
        "entries": entries,
    }


def _manifest_entry(row: dict[str, Any], *, path: str) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "title": row.get("title", ""),
        "path": path,
        "category": row.get("category", "general"),
        "layer": row.get("layer", "L3"),
        "scope": row.get("scope", "project"),
        "sensitivity": row.get("sensitivity", "low"),
        "trust": row.get("trust", 0),
        "updated_at": row.get("updated_at", ""),
    }


def _filters(
    category: str | None,
    tag: str | None,
    layer: str | None,
    limit: int | None,
    min_trust: float,
    include_private: bool,
    include_restricted: bool,
) -> dict[str, Any]:
    return {
        "category": category,
        "tag": tag,
        "layer": layer,
        "limit": limit,
        "min_trust": min_trust,
        "include_private": include_private,
        "include_restricted": include_restricted,
    }


def _json_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["tags_list"] = _split_tags(row.get("tags"))
    payload["allowed_agents_list"] = _split_tags(row.get("allowed_agents"))
    return payload


def _markdown_path(row: dict[str, Any]) -> str:
    category = _safe_filename(str(row.get("category") or "general"), default="general")
    title = _safe_filename(str(row.get("title") or "untitled"), default="untitled")
    return f"knowledge/{category}/{int(row['id']):04d}-{title}.md"


def _safe_filename(value: str, *, default: str = "untitled") -> str:
    slug = UNSAFE_FILENAME.sub("-", str(value or "").strip())
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-._ ")
    return slug or default


def _split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.split(",") if part.strip()]


def _yaml_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)
