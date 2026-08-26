"""Deterministic memory curator proposal and promotion scaffolding."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .compiler import VaultCompiler, generate_summary, simple_aaak_compress
from .db import VaultDB, normalize_governance_metadata
from .memory_object import application_metadata_from_record
from .privacy import redact_secrets, scan_privacy

_VALID_LAYERS = {"L0", "L1", "L2", "L3"}
_VALID_STATUSES = {"pass", "warn", "fail"}
_NEAR_DUPLICATE_THRESHOLD = 0.82
_NEAR_TITLE_THRESHOLD = 0.75
_GENERIC_TITLES = {"note", "notes", "memory", "misc", "update", "todo", "untitled", "雜記", "筆記", "記憶"}
_QUALITY_SIGNALS = {
    "because", "caused", "fix", "fixed", "decision", "decided", "prefer", "avoid",
    "step", "error", "bug", "reason", "limit", "constraint", "解法", "修復", "原因",
    "決策", "偏好", "避免", "步驟", "錯誤", "限制", "因此",
}
_META_INSTRUCTION_PATTERNS = (
    r"^(?:請)?記住(?:這|那)?(?:段|個|件)?(?:內容|事情|資訊)?[。.!！]?$",
    r"^(?:please\s+)?remember\s+(?:this|that)(?:\s+(?:content|information))?[.!]?$",
    r"^(?:把|將)(?:這|那)(?:段|個|件)?(?:內容|事情|資訊)?(?:存|寫)(?:起來|進記憶|入庫)[。.!！]?$",
)
_DEICTIC_TERMS = (
    "這個", "這件事", "這段", "這些", "那個", "那件事", "那段", "那些", "它", "他們",
    "this", "that", "these", "those", "it", "they",
)
_DANGLING_ENDINGS = (":", "：", "-", "—", "–", ",", "，", ";", "；")
_OPAQUE_TITLE_RE = re.compile(
    r"(?:^|[\s_\-:#])(?:[0-9a-f]{8,64}|(?=[0-9a-z]{16,64}(?:$|[\s_\-:#]))(?=[0-9a-z]*[0-9])[0-9a-z]{16,64})(?:$|[\s_\-:#])",
    flags=re.IGNORECASE,
)
_SHORT_RULE_SIGNALS = (
    "must", "should", "always", "never", "only", "maximum", "minimum", "at most", "at least",
    "必須", "應", "只", "不得", "不要", "永遠", "最多", "至少", "上限", "下限",
)
_PROMOTION_REVIEW_TOKEN = object()


@dataclass(frozen=True)
class _PromotionReview:
    """Runtime-injected review result; never populated from public payloads."""

    kind: str
    review_ref: str
    actor_ref: str
    reason: str
    canonical_knowledge_id: int
    _token: object = field(repr=False, compare=False)


def _conflict_promotion_review(
    *,
    conflict_ref: str,
    actor_ref: str,
    reason: str,
    canonical_knowledge_id: int,
) -> _PromotionReview:
    """Create a bounded review result after the conflict runtime validates it."""
    conflict = str(conflict_ref or "").strip()
    actor = str(actor_ref or "").strip()
    review_reason = str(reason or "").strip()
    knowledge_id = int(canonical_knowledge_id or 0)
    if not conflict or not actor or not review_reason or knowledge_id <= 0:
        raise ValueError(
            "reviewed conflict promotion requires conflict, actor, reason, and canonical knowledge"
        )
    return _PromotionReview(
        kind="conflict_resolution",
        review_ref=conflict,
        actor_ref=actor,
        reason=review_reason,
        canonical_knowledge_id=knowledge_id,
        _token=_PROMOTION_REVIEW_TOKEN,
    )


def _review_allows_warnings(
    review: _PromotionReview | None,
    *,
    duplicate: dict,
    quality: dict,
) -> bool:
    """Allow only the duplicate selected by a validated conflict decision."""
    if not isinstance(review, _PromotionReview) or review._token is not _PROMOTION_REVIEW_TOKEN:
        return False
    if review.kind != "conflict_resolution" or quality["status"] != "pass":
        return False
    findings = duplicate.get("findings") or []
    expected = f"knowledge:{review.canonical_knowledge_id}"
    return bool(findings) and all(finding.get("span") == expected for finding in findings)


def normalize_title(title: str) -> str:
    return " ".join((title or "").strip().split())


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split()).casefold()


def content_hash(content: str) -> str:
    return hashlib.sha256(normalize_text(content).encode("utf-8")).hexdigest()[:16]


def _similarity_tokens(text: str) -> set[str]:
    normalized = normalize_text(text)
    words = set(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
    compact = re.sub(r"\s+", "", normalized)
    if len(compact) >= 3:
        words.update(compact[i:i + 3] for i in range(len(compact) - 2))
    return {token for token in words if token}


def text_similarity(left: str, right: str) -> float:
    """Deterministic token/character n-gram Jaccard similarity."""
    a = _similarity_tokens(left)
    b = _similarity_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def safe_slug(title: str) -> str:
    slug = re.sub(r"[^\w\-.]+", "-", normalize_title(title).lower(), flags=re.UNICODE).strip("-._")
    return slug or "memory"


def normalize_metadata(
    title: str,
    content: str,
    *,
    layer: str = "L3",
    category: str = "general",
    tags: str | list[str] = "",
    trust: float = 0.5,
    source: str = "memory",
    source_ref: str = "",
    reason: str = "",
    scope: str = "project",
    sensitivity: str = "low",
    owner_agent: str = "",
    allowed_agents: str | list[str] = "",
    memory_type: str = "knowledge",
    expires_at: str = "",
    valid_from: str = "",
    valid_until: str = "",
    supersedes_id: int | str | None = None,
    application_metadata: dict[str, Any] | None = None,
) -> dict:
    if isinstance(tags, list):
        tags_s = ",".join(str(t).strip() for t in tags if str(t).strip())
    else:
        tags_s = ",".join(t.strip() for t in str(tags or "").split(",") if t.strip())
    norm_layer = str(layer or "L3").strip().upper()
    if norm_layer not in _VALID_LAYERS:
        norm_layer = "L3"
    try:
        trust_f = max(0.0, min(1.0, float(trust)))
    except (TypeError, ValueError):
        trust_f = 0.5
    governance = normalize_governance_metadata(
        scope=scope,
        sensitivity=sensitivity,
        owner_agent=owner_agent,
        allowed_agents=allowed_agents,
        memory_type=memory_type,
        expires_at=expires_at,
        valid_from=valid_from,
        valid_until=valid_until,
        supersedes_id=supersedes_id,
    )
    if application_metadata is None:
        application_metadata_i: dict[str, Any] = {}
    elif not isinstance(application_metadata, dict):
        raise ValueError("application_metadata must be a JSON object")
    else:
        try:
            application_metadata_i = json.loads(
                json.dumps(application_metadata, ensure_ascii=False, sort_keys=True)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("application_metadata must contain JSON values") from exc
    return {
        "title": normalize_title(title),
        "content": (content or "").strip(),
        "layer": norm_layer,
        "category": (category or "general").strip() or "general",
        "tags": tags_s,
        "trust": trust_f,
        "source": (source or "memory").strip() or "memory",
        "source_ref": (source_ref or "").strip(),
        "reason": (reason or "").strip(),
        "application_metadata": application_metadata_i,
        **governance,
    }


def metadata_gate(meta: dict) -> dict:
    findings = []
    if not meta.get("title"):
        findings.append({"type": "title", "severity": "fail", "span": "[EMPTY]"})
    if not meta.get("content"):
        findings.append({"type": "content", "severity": "fail", "span": "[EMPTY]"})
    if not meta.get("reason"):
        findings.append({"type": "reason", "severity": "warn", "span": "[EMPTY]"})
    status = "fail" if any(f["severity"] == "fail" for f in findings) else "warn" if findings else "pass"
    return {"status": status, "findings": findings}


def quality_gate(meta: dict) -> dict:
    """Evaluate candidate semantics without treating provenance text as content.

    The result remains backward compatible with the original ``status`` and
    ``findings`` keys while exposing typed, additive semantic quality fields.
    This gate does not infer a person, identity, or relationship model.
    """
    findings: list[dict[str, Any]] = []
    title = normalize_title(meta.get("title", ""))
    content = str(meta.get("content", "") or "").strip()
    tags = str(meta.get("tags", "") or "").strip()
    lower_blob = normalize_text(f"{title} {content} {tags}")
    normalized_content = normalize_text(content)
    title_key = normalize_text(title)

    question_only = bool(content) and content.rstrip().endswith(("?", "？"))
    meta_instruction_only = any(re.fullmatch(pattern, content.strip(), flags=re.IGNORECASE) for pattern in _META_INSTRUCTION_PATTERNS)
    dangling_punctuation = bool(content) and content.rstrip().endswith(_DANGLING_ENDINGS)
    deictic_terms = [
        term
        for term in _DEICTIC_TERMS
        if (
            term in normalized_content
            if not term.isascii()
            else re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized_content)
        )
    ]
    deictic_without_anchor = bool(deictic_terms) and len(normalized_content) <= 36
    opaque_title = bool(_OPAQUE_TITLE_RE.search(title_key))
    short_complete_rule = (
        6 <= len(content) < 40
        and content.rstrip().endswith((".", "。", "!", "！"))
        and any(signal in normalized_content for signal in _SHORT_RULE_SIGNALS)
        and not question_only
        and not meta_instruction_only
        and not dangling_punctuation
        and not deictic_without_anchor
    )
    standalone_statement = (
        len(content) >= 40
        and content.rstrip().endswith((".", "。", "!", "！"))
        and not question_only
        and not meta_instruction_only
        and not dangling_punctuation
        and not deictic_without_anchor
    )

    if len(content) < 40 and not short_complete_rule:
        findings.append({"type": "content_too_short", "severity": "warn", "span": content[:40] or "[EMPTY]"})
    if title_key in _GENERIC_TITLES:
        findings.append({"type": "generic_title", "severity": "warn", "span": title or "[EMPTY]"})
    if opaque_title:
        findings.append({"type": "opaque_title", "severity": "warn", "field": "title"})
    if not tags:
        findings.append({"type": "missing_tags", "severity": "warn", "span": "[EMPTY]"})
    if (
        not short_complete_rule
        and not standalone_statement
        and not any(signal in lower_blob for signal in _QUALITY_SIGNALS)
    ):
        findings.append({"type": "low_context", "severity": "warn", "span": content[:80] or "[EMPTY]"})
    if question_only:
        findings.append({"type": "question_only", "severity": "warn", "field": "content"})
    if meta_instruction_only:
        findings.append({"type": "meta_instruction_only", "severity": "warn", "field": "content"})
    if dangling_punctuation:
        findings.append({"type": "dangling_punctuation", "severity": "warn", "field": "content"})
    if deictic_without_anchor:
        findings.append({"type": "deictic_without_anchor", "severity": "warn", "field": "content"})

    blocking_semantic_types = {
        "question_only", "meta_instruction_only", "dangling_punctuation",
        "deictic_without_anchor", "opaque_title",
    }
    finding_types = {finding["type"] for finding in findings}
    status = "warn" if findings else "pass"
    return {
        "status": status,
        "disposition": "review_required" if findings else "accept",
        "policy": "semantic-quality",
        "findings": findings,
        "semantic_completeness": "incomplete" if finding_types & blocking_semantic_types else "complete",
        "authorship_state": "unknown",
        "decision_state": "question" if question_only else "unknown",
        "context_dependency": "anchor_required" if deictic_without_anchor else "standalone",
        "future_utility": "low" if meta_instruction_only else "uncertain" if "low_context" in finding_types else "useful",
        "title_quality": "opaque" if opaque_title else "generic" if title_key in _GENERIC_TITLES else "readable",
    }


def duplicate_gate(db: VaultDB, title: str, content: str, *, exclude_candidate_id: str | None = None) -> dict:
    nt = normalize_text(title)
    nc = normalize_text(content)
    ch = content_hash(content)
    findings: list[dict[str, Any]] = []

    for row in db.conn.execute("SELECT id, title, content_raw, content_hash FROM knowledge").fetchall():
        if normalize_text(row["title"]) == nt:
            findings.append({"type": "active_title", "severity": "warn", "span": f"knowledge:{row['id']}"})
        if normalize_text(row["content_raw"]) == nc or (row["content_hash"] and row["content_hash"] == ch):
            findings.append({"type": "active_content", "severity": "warn", "span": f"knowledge:{row['id']}"})
        elif text_similarity(content, row["content_raw"]) >= _NEAR_DUPLICATE_THRESHOLD:
            findings.append({"type": "active_near_duplicate", "severity": "warn", "span": f"knowledge:{row['id']}"})
        elif text_similarity(title, row["title"]) >= _NEAR_TITLE_THRESHOLD:
            findings.append({"type": "active_near_title", "severity": "warn", "span": f"knowledge:{row['id']}"})

    params: list[Any] = []
    query = "SELECT id, title, content FROM memory_candidates WHERE status IN ('candidate','approved')"
    if exclude_candidate_id:
        query += " AND id != ?"
        params.append(exclude_candidate_id)
    for row in db.conn.execute(query, params).fetchall():
        if normalize_text(row["title"]) == nt:
            findings.append({"type": "candidate_title", "severity": "warn", "span": f"candidate:{row['id']}"})
        if normalize_text(row["content"]) == nc or content_hash(row["content"]) == ch:
            findings.append({"type": "candidate_content", "severity": "warn", "span": f"candidate:{row['id']}"})
        elif text_similarity(content, row["content"]) >= _NEAR_DUPLICATE_THRESHOLD:
            findings.append({"type": "candidate_near_duplicate", "severity": "warn", "span": f"candidate:{row['id']}"})
        elif text_similarity(title, row["title"]) >= _NEAR_TITLE_THRESHOLD:
            findings.append({"type": "candidate_near_title", "severity": "warn", "span": f"candidate:{row['id']}"})

    return {"status": "warn" if findings else "pass", "findings": findings}


def _gate_payload(
    privacy: dict,
    duplicate: dict,
    metadata: dict,
    quality: dict,
    *,
    application_metadata: dict[str, Any] | None = None,
) -> dict:
    payload = {"privacy": privacy, "duplicate": duplicate, "metadata": metadata, "quality": quality}
    if application_metadata:
        payload["application_metadata"] = application_metadata
    return payload


def _all_gates_pass(result: dict) -> bool:
    gates = result.get("gates") or {}
    return all(gates.get(name) == "pass" for name in ("privacy", "duplicate", "metadata", "quality"))


def _record_candidate_feedback(
    db: VaultDB,
    candidate: dict,
    *,
    outcome: str,
    reason: str,
    score: float,
    knowledge_id: int | None = None,
    gates: dict | None = None,
) -> None:
    """Best-effort feedback event for automation learning."""
    try:
        db.record_memory_feedback(
            {
                "candidate_id": candidate.get("id", ""),
                "knowledge_id": knowledge_id,
                "source": candidate.get("source", ""),
                "source_ref": candidate.get("source_ref", ""),
                "memory_type": candidate.get("memory_type", "knowledge"),
                "category": candidate.get("category", ""),
                "outcome": outcome,
                "score": score,
                "reason": reason,
                "payload_json": {
                    "title": candidate.get("title", ""),
                    "privacy_status": candidate.get("privacy_status", ""),
                    "duplicate_status": candidate.get("duplicate_status", ""),
                    "quality_status": candidate.get("quality_status", ""),
                    "gates": gates or {},
                },
            }
        )
    except Exception:
        # Feedback should never block the primary memory workflow.
        return


def review_candidate(
    db: VaultDB,
    candidate_id: str,
    *,
    outcome: str,
    reason: str = "",
    score: float | None = None,
) -> dict:
    """Record a non-promotion review outcome for a memory candidate."""
    normalized_outcome = str(outcome or "").strip().lower()
    if normalized_outcome not in {"rejected", "blocked"}:
        raise ValueError("candidate review outcome must be rejected or blocked")
    candidate = db.get_memory_candidate(candidate_id)
    if not candidate:
        raise KeyError(f"candidate not found: {candidate_id}")
    if candidate.get("status") == "promoted":
        return {
            "status": "already_promoted",
            "candidate_id": candidate_id,
            "outcome": "promoted",
            "promoted_knowledge_id": candidate.get("promoted_knowledge_id"),
            "candidate": candidate,
        }

    review_reason = reason.strip() or f"candidate review marked {normalized_outcome}"
    if score is None:
        score_value = 0.0 if normalized_outcome == "rejected" else 0.25
    else:
        try:
            score_value = max(0.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            score_value = 0.0
    db.update_memory_candidate(candidate_id, status=normalized_outcome)
    reviewed = db.get_memory_candidate(candidate_id) or candidate
    _record_candidate_feedback(
        db,
        reviewed,
        outcome=normalized_outcome,
        reason=review_reason,
        score=score_value,
    )
    return {
        "status": normalized_outcome,
        "candidate_id": candidate_id,
        "outcome": normalized_outcome,
        "score": score_value,
        "reason": review_reason,
        "candidate": reviewed,
        "next_action": "Run vault automation eval or vault automation cycle so future curation can learn from this review.",
    }


def create_candidate(db: VaultDB, **kwargs) -> dict:
    meta = normalize_metadata(**kwargs)
    privacy = scan_privacy(
        "\n".join(
            [
                meta["title"],
                meta["content"],
                meta["source_ref"],
                meta["reason"],
                meta["owner_agent"],
                meta["allowed_agents"],
                json.dumps(meta["application_metadata"], ensure_ascii=False, sort_keys=True),
            ]
        )
    )
    duplicate = duplicate_gate(db, meta["title"], meta["content"])
    metadata = metadata_gate(meta)
    quality = quality_gate(meta)
    rejected = privacy["status"] == "fail" or metadata["status"] == "fail"
    stored_meta = dict(meta)
    if privacy["status"] == "fail":
        for field in ("title", "content", "source_ref", "reason"):
            stored_meta[field] = redact_secrets(stored_meta.get(field, ""))
        stored_meta["application_metadata"] = {}
    gates = _gate_payload(
        privacy,
        duplicate,
        metadata,
        quality,
        application_metadata=stored_meta.get("application_metadata"),
    )
    candidate_id = f"mem_{uuid.uuid4().hex[:12]}"
    candidate = {
        "id": candidate_id,
        **stored_meta,
        "status": "rejected" if rejected else "candidate",
        "privacy_status": privacy["status"],
        "duplicate_status": duplicate["status"],
        "quality_status": quality["status"],
        "gate_payload_json": json.dumps(gates, ensure_ascii=False, sort_keys=True),
    }
    db.add_memory_candidate(candidate)
    if rejected:
        _record_candidate_feedback(
            db,
            candidate,
            outcome="rejected",
            reason="candidate failed privacy or metadata gate before review",
            score=0.0,
            gates=gates,
        )
    result = {
        "status": "rejected" if rejected else "candidate_created",
        "candidate_id": candidate_id,
        "knowledge_id": None,
        "gates": {"privacy": privacy["status"], "duplicate": duplicate["status"], "metadata": metadata["status"], "quality": quality["status"]},
        "gate_payload": gates,
    }
    if not rejected and duplicate["status"] == "pass" and quality["status"] == "pass":
        result["next_action"] = {"tool": "vault_memory_promote", "arguments": {"candidate_id": candidate_id, "confirm": True}}
    elif not rejected:
        result["next_action"] = {
            "tool": "vault_memory_review",
            "arguments": {"candidate_id": candidate_id},
            "reason": "Resolve quality or duplicate warnings before promotion.",
        }
    return result


def propose_memory(db: VaultDB, mode: str = "candidate", **kwargs) -> dict:
    project_dir = kwargs.pop("project_dir", None)
    result = create_candidate(db, **kwargs)
    if mode == "promote_if_safe" and result["status"] == "candidate_created" and _all_gates_pass(result):
        promoted = promote_candidate(db, result["candidate_id"], confirm=True, project_dir=project_dir)
        result.update({"status": "promoted", "knowledge_id": promoted["knowledge_id"], "promotion": promoted})
    elif mode == "promote_if_safe" and result["status"] == "candidate_created":
        result["auto_promotion"] = {
            "status": "skipped",
            "reason": "promote_if_safe requires privacy, duplicate, metadata, and quality gates to pass",
        }
    return result


def _unique_raw_path(project_dir: Path, title: str) -> Path:
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    base = safe_slug(title)
    path = raw_dir / f"{base}.md"
    idx = 2
    while path.exists():
        path = raw_dir / f"{base}-{idx}.md"
        idx += 1
    return path


def promote_candidate(
    db: VaultDB,
    candidate_id: str,
    *,
    confirm: bool = False,
    project_dir: str | Path | None = None,
    compile: bool = True,
    build_map: bool = True,
    _runtime_review: _PromotionReview | None = None,
) -> dict:
    if not confirm:
        raise ValueError("promotion requires confirm=True")
    candidate = db.get_memory_candidate(candidate_id)
    if not candidate:
        raise KeyError(f"candidate not found: {candidate_id}")
    if candidate["status"] == "promoted" and candidate.get("promoted_knowledge_id"):
        return {"status": "already_promoted", "candidate_id": candidate_id, "knowledge_id": candidate["promoted_knowledge_id"], "candidate": candidate}
    if candidate["status"] == "rejected":
        return {"status": "blocked", "candidate_id": candidate_id, "knowledge_id": None, "candidate": candidate}

    candidate_application_metadata = application_metadata_from_record(candidate)
    privacy = scan_privacy(
        "\n".join(
            [
                candidate["title"],
                candidate["content"],
                candidate["source_ref"],
                candidate["reason"],
                candidate.get("owner_agent", ""),
                candidate.get("allowed_agents", ""),
                json.dumps(candidate_application_metadata, ensure_ascii=False, sort_keys=True),
            ]
        )
    )
    duplicate = duplicate_gate(db, candidate["title"], candidate["content"], exclude_candidate_id=candidate_id)
    metadata = metadata_gate(candidate)
    quality = quality_gate(candidate)
    gates = _gate_payload(
        privacy,
        duplicate,
        metadata,
        quality,
        application_metadata=(
            candidate_application_metadata if privacy["status"] != "fail" else {}
        ),
    )
    if privacy["status"] == "fail" or metadata["status"] == "fail":
        db.update_memory_candidate(candidate_id, status="rejected", privacy_status=privacy["status"], duplicate_status=duplicate["status"], quality_status=quality["status"], gate_payload_json=json.dumps(gates, ensure_ascii=False, sort_keys=True))
        blocked_candidate = db.get_memory_candidate(candidate_id) or candidate
        _record_candidate_feedback(
            db,
            blocked_candidate,
            outcome="blocked",
            reason="promotion blocked by privacy or metadata gate",
            score=0.0,
            gates=gates,
        )
        return {"status": "blocked", "candidate_id": candidate_id, "knowledge_id": None, "gates": gates}

    warning_gates = [
        name
        for name, result in (("duplicate", duplicate), ("quality", quality))
        if result["status"] != "pass"
    ]
    review_applied = bool(warning_gates) and _review_allows_warnings(
        _runtime_review,
        duplicate=duplicate,
        quality=quality,
    )
    if warning_gates and not review_applied:
        db.update_memory_candidate(
            candidate_id,
            privacy_status=privacy["status"],
            duplicate_status=duplicate["status"],
            quality_status=quality["status"],
            gate_payload_json=json.dumps(gates, ensure_ascii=False, sort_keys=True),
        )
        return {
            "status": "review_required",
            "candidate_id": candidate_id,
            "knowledge_id": None,
            "warning_gates": warning_gates,
            "gates": gates,
            "next_action": "Resolve the warnings or choose the canonical memory before promotion.",
        }

    root = Path(project_dir) if project_dir is not None else db.db_path.parent
    raw_path = _unique_raw_path(root, candidate["title"])
    source_file = str(raw_path.relative_to(root / "raw"))
    frontmatter = {
        "title": candidate["title"],
        "layer": candidate["layer"],
        "category": candidate["category"],
        "tags": candidate["tags"],
        "trust": candidate["trust"],
        "source": source_file,
        "memory_candidate_id": candidate_id,
        "scope": candidate.get("scope", "project"),
        "sensitivity": candidate.get("sensitivity", "low"),
        "owner_agent": candidate.get("owner_agent", ""),
        "allowed_agents": candidate.get("allowed_agents", "[]"),
        "memory_type": candidate.get("memory_type", "knowledge"),
        "expires_at": candidate.get("expires_at", ""),
        "valid_from": candidate.get("valid_from", ""),
        "valid_until": candidate.get("valid_until", ""),
        "supersedes_id": candidate.get("supersedes_id"),
    }
    raw_path.write_text(f"---\n{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n---\n\n{candidate['content']}\n", encoding="utf-8")

    knowledge_id: int | None = None
    if compile:
        compiler = VaultCompiler(root, db=db, embed_provider=None)
        compiler.compile(dry_run=False)
        row = db.conn.execute("SELECT id FROM knowledge WHERE source = ? ORDER BY id DESC LIMIT 1", (source_file,)).fetchone()
        knowledge_id = int(row["id"]) if row else None
    if knowledge_id is None:
        knowledge_id = db.add_knowledge(
            title=candidate["title"],
            content_raw=candidate["content"],
            content_aaak=simple_aaak_compress(candidate["title"], candidate["content"]),
            summary=generate_summary(candidate["content"], title=candidate["title"]),
            layer=candidate["layer"],
            category=candidate["category"],
            tags=candidate["tags"],
            trust=float(candidate["trust"]),
            source=source_file,
            scope=candidate.get("scope", "project"),
            sensitivity=candidate.get("sensitivity", "low"),
            owner_agent=candidate.get("owner_agent", ""),
            allowed_agents=candidate.get("allowed_agents", "[]"),
            memory_type=candidate.get("memory_type", "knowledge"),
            expires_at=candidate.get("expires_at", ""),
            valid_from=candidate.get("valid_from", ""),
            valid_until=candidate.get("valid_until", ""),
            supersedes_id=candidate.get("supersedes_id"),
        )
        if build_map:
            VaultCompiler(root, db=db, embed_provider=None)._refresh_document_map(knowledge_id)

    db.update_memory_candidate(candidate_id, status="promoted", privacy_status=privacy["status"], duplicate_status=duplicate["status"], quality_status=quality["status"], gate_payload_json=json.dumps(gates, ensure_ascii=False, sort_keys=True), promoted_knowledge_id=knowledge_id)
    promoted_candidate = db.get_memory_candidate(candidate_id) or candidate
    _record_candidate_feedback(
        db,
        promoted_candidate,
        outcome="promoted",
        reason="candidate promoted into active knowledge",
        score=1.0,
        knowledge_id=knowledge_id,
        gates=gates,
    )
    result = {
        "status": "promoted",
        "candidate_id": candidate_id,
        "knowledge_id": knowledge_id,
        "raw_path": str(raw_path),
        "gates": {"privacy": privacy["status"], "duplicate": duplicate["status"], "metadata": metadata["status"], "quality": quality["status"]},
        "knowledge": db.get_knowledge(knowledge_id),
        "candidate": db.get_memory_candidate(candidate_id),
    }
    if review_applied and _runtime_review is not None:
        result["review"] = {
            "kind": _runtime_review.kind,
            "review_ref": _runtime_review.review_ref,
            "actor_ref": _runtime_review.actor_ref,
            "canonical_knowledge_id": _runtime_review.canonical_knowledge_id,
        }
    return result
