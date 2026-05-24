"""Deterministic privacy scanner for Guardrails local write paths.

The scanner is intentionally conservative and report-oriented.  Findings include
rule identifiers, severity, action, field paths, and redacted previews only; raw
secret/PII values are never copied into findings or audit summaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import hashlib
import re
from typing import Any

_OUTCOME_ORDER = {"clear": 0, "redact_required": 1, "private_only": 2, "blocked": 3}
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

_PLACEHOLDER_MARKERS = (
    "<TOKEN>",
    "<TOKEN_PLACEHOLDER>",
    "<API_KEY>",
    "<SECRET>",
    "YOUR_TOKEN",
    "YOUR_API_KEY",
    "REDACTED",
    "PLACEHOLDER",
    "EXAMPLE",
)

_DOC_MARKERS = (
    "example",
    "examples",
    "placeholder",
    "pattern",
    "patterns",
    "docs",
    "documentation",
    "look like",
    "looks like",
    "do not paste",
)

_SECRET_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "openai_api_key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        "[REDACTED_SECRET:openai_api_key]",
    ),
    (
        "github_token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
        "[REDACTED_SECRET:github_token]",
    ),
    (
        "pypi_token",
        re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}\b"),
        "[REDACTED_SECRET:pypi_token]",
    ),
    (
        "bearer_token",
        re.compile(r"\bBearer\s+(?!<TOKEN>|TOKEN\b|REDACTED\b)[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE),
        "Bearer [REDACTED_SECRET:bearer_token]",
    ),
    (
        "private_key_block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        "credential_assignment",
        re.compile(
            r"\b(?:api[_-]?key|token|secret|password)\s*=\s*(?!<|REDACTED|TOKEN\b)[A-Za-z0-9._~+/=-]{20,}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_SECRET:credential_assignment]",
    ),
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
_CUSTOMER_MARKERS_RE = re.compile(r"\b(customer|client|patient|crm|appointment|treatment|filler|botox|payment)\b", re.IGNORECASE)
_PRIVATE_LIFE_RE = re.compile(r"\b(marriage|divorce|children|family conflict|intimate|private life)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PrivacyFinding:
    """A safe finding descriptor.  It never contains raw matched values."""

    kind: str
    severity: str
    action: str
    rule_id: str
    field_path: str
    preview: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrivacyScanResult:
    """Privacy scan result with safe, dict-convertible fields."""

    outcome: str
    findings: list[PrivacyFinding]
    redacted_text: Any
    audit_summary: dict[str, Any]
    can_store_draft: bool
    can_promote_shared: bool
    can_sync_remote: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "findings": [finding.to_dict() for finding in self.findings],
            "redacted_text": self.redacted_text,
            "audit_summary": self.audit_summary,
            "can_store_draft": self.can_store_draft,
            "can_promote_shared": self.can_promote_shared,
            "can_sync_remote": self.can_sync_remote,
        }


def scan_text(text: str, *, context: dict | None = None) -> PrivacyScanResult:
    """Scan a single text value and return a safe result."""
    result = scan_entry({"text": text}, context=context)
    redacted_text = result.redacted_text.get("text", "") if isinstance(result.redacted_text, dict) else ""
    return PrivacyScanResult(
        outcome=result.outcome,
        findings=result.findings,
        redacted_text=redacted_text,
        audit_summary=result.audit_summary,
        can_store_draft=result.can_store_draft,
        can_promote_shared=result.can_promote_shared,
        can_sync_remote=result.can_sync_remote,
    )


def scan_entry(entry: dict, *, context: dict | None = None) -> PrivacyScanResult:
    """Recursively scan a candidate-like entry.

    Strings nested inside dict/list structures are scanned with their field path.
    Non-string scalar values are ignored to avoid accidental binary/raw payload
    expansion in scanner output.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict")

    redacted = copy.deepcopy(entry)
    findings: list[PrivacyFinding] = []
    for path_tokens, field_path, value in _iter_strings(entry):
        redacted_value, value_findings = _scan_string(value, field_path, context or {})
        findings.extend(value_findings)
        _set_path(redacted, path_tokens, redacted_value)
    key_findings: list[PrivacyFinding] = []
    redacted = _redact_sensitive_keys(redacted, key_findings, context or {})
    findings.extend(key_findings)

    outcome = _aggregate_outcome(findings)
    audit_summary = _audit_summary(outcome, findings)
    return PrivacyScanResult(
        outcome=outcome,
        findings=findings,
        redacted_text=redacted,
        audit_summary=audit_summary,
        can_store_draft=outcome != "blocked",
        can_promote_shared=outcome in {"clear", "redact_required"},
        can_sync_remote=outcome == "clear",
    )


def _scan_string(text: str, field_path: str, context: dict[str, Any]) -> tuple[str, list[PrivacyFinding]]:
    redacted = text
    findings: list[PrivacyFinding] = []

    for rule_id, pattern, replacement in _SECRET_RULES:
        matches = [match for match in pattern.finditer(text) if not _is_placeholder_or_doc_example(text, match)]
        if not matches:
            continue
        redacted = pattern.sub(lambda match, repl=replacement: match.group(0) if _is_placeholder_or_doc_example(text, match) else repl, redacted)
        for _match in matches:
            findings.append(
                PrivacyFinding(
                    kind="secret",
                    severity="critical",
                    action="block",
                    rule_id=rule_id,
                    field_path=field_path,
                    preview=replacement,
                    message="credential-like value detected; raw value withheld",
                )
            )

    customer_context = bool(_CUSTOMER_MARKERS_RE.search(text))
    email_matches = [match for match in _EMAIL_RE.finditer(text) if not _is_placeholder_or_doc_example(text, match)]
    phone_matches = [match for match in _PHONE_RE.finditer(text) if not _is_placeholder_or_doc_example(text, match)]

    if customer_context and (email_matches or phone_matches or _looks_like_customer_name(text)):
        redacted = "[REDACTED_PRIVATE_CONTEXT]"
        findings.append(
            PrivacyFinding(
                kind="crm",
                severity="high",
                action="private_only",
                rule_id="customer_context",
                field_path=field_path,
                preview="[REDACTED_PRIVATE_CONTEXT]",
                message="customer/private operational context detected; raw details withheld",
            )
        )
    else:
        if email_matches:
            redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
            findings.extend(
                PrivacyFinding(
                    kind="pii",
                    severity="medium",
                    action="redact",
                    rule_id="email_address",
                    field_path=field_path,
                    preview="[REDACTED_EMAIL]",
                    message="email-like value detected; raw value withheld",
                )
                for _match in email_matches
            )
        if phone_matches:
            redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
            findings.extend(
                PrivacyFinding(
                    kind="pii",
                    severity="medium",
                    action="redact",
                    rule_id="phone_number",
                    field_path=field_path,
                    preview="[REDACTED_PHONE]",
                    message="phone-like value detected; raw value withheld",
                )
                for _match in phone_matches
            )

    if _PRIVATE_LIFE_RE.search(text) and not _is_transformed_rule(text):
        redacted = "[REDACTED_PRIVATE_CONTEXT]"
        findings.append(
            PrivacyFinding(
                kind="life_profile",
                severity="high",
                action="private_only",
                rule_id="private_life_context",
                field_path=field_path,
                preview="[REDACTED_PRIVATE_CONTEXT]",
                message="private-life context detected; raw details withheld",
            )
        )

    return redacted, findings


def _iter_strings(value: Any, path_tokens: list[Any] | None = None, safe_parts: list[str] | None = None):
    path_tokens = path_tokens or []
    safe_parts = safe_parts or []
    if isinstance(value, str):
        yield path_tokens, _format_safe_path(safe_parts), value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_strings(
                child,
                [*path_tokens, key],
                [*safe_parts, _safe_key_segment(str(key))],
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_strings(child, [*path_tokens, index], [*safe_parts, f"[{index}]"])


def _safe_key_segment(key: str) -> str:
    digest = hashlib.sha256(key.encode()).hexdigest()[:10]
    return f"field:{digest}"


def _format_safe_path(safe_parts: list[str]) -> str:
    path = ""
    for part in safe_parts:
        if part.startswith("["):
            path += part
        elif path:
            path += f".{part}"
        else:
            path = part
    return path


def _set_path(root: Any, path_tokens: list[Any], value: str) -> None:
    if not path_tokens:
        return
    current = root
    for part in path_tokens[:-1]:
        current = current[part]
    current[path_tokens[-1]] = value


def _redact_sensitive_keys(value: Any, findings: list[PrivacyFinding], context: dict[str, Any], safe_path: str = "") -> Any:
    if isinstance(value, dict):
        redacted_dict: dict[Any, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            key_safe_path = f"{safe_path}.{_safe_key_segment(key_text)}.__key__" if safe_path else f"{_safe_key_segment(key_text)}.__key__"
            redacted_key_text, key_findings = _scan_string(key_text, key_safe_path, context)
            findings.extend(key_findings)
            if key_findings:
                digest = hashlib.sha256(key_text.encode()).hexdigest()[:8]
                new_key = f"{redacted_key_text}#{digest}"
            else:
                new_key = key
            child_path = key_safe_path.removesuffix(".__key__")
            redacted_dict[new_key] = _redact_sensitive_keys(child, findings, context, child_path)
        return redacted_dict
    if isinstance(value, list):
        return [
            _redact_sensitive_keys(child, findings, context, f"{safe_path}[{index}]" if safe_path else f"[{index}]")
            for index, child in enumerate(value)
        ]
    return value


def _is_placeholder_or_doc_example(text: str, match: re.Match[str]) -> bool:
    matched = match.group(0)
    upper = matched.upper()
    if "..." in matched or any(marker in upper for marker in _PLACEHOLDER_MARKERS):
        return True
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].casefold()
    return any(marker in line for marker in _DOC_MARKERS) and (
        "..." in line or "<token" in line or "placeholder" in line or "pattern" in line
    )


def _looks_like_customer_name(text: str) -> bool:
    return bool(re.search(r"\b(customer|client|patient)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text))


def _is_transformed_rule(text: str) -> bool:
    lowered = text.casefold()
    return "do not store raw" in lowered or "generalized" in lowered or "collaboration rule" in lowered


def _aggregate_outcome(findings: list[PrivacyFinding]) -> str:
    outcome = "clear"
    for finding in findings:
        if finding.action == "block":
            candidate = "blocked"
        elif finding.action == "private_only":
            candidate = "private_only"
        elif finding.action == "redact":
            candidate = "redact_required"
        else:
            candidate = "clear"
        if _OUTCOME_ORDER[candidate] > _OUTCOME_ORDER[outcome]:
            outcome = candidate
    return outcome


def _audit_summary(outcome: str, findings: list[PrivacyFinding]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    severities: list[str] = []
    for finding in findings:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
        by_rule[finding.rule_id] = by_rule.get(finding.rule_id, 0) + 1
        severities.append(finding.severity)
    max_severity = "low"
    if severities:
        max_severity = max(severities, key=lambda severity: _SEVERITY_ORDER.get(severity, 0))
    return {
        "outcome": outcome,
        "finding_count": len(findings),
        "by_kind": dict(sorted(by_kind.items())),
        "by_rule": dict(sorted(by_rule.items())),
        "max_severity": max_severity if findings else "none",
    }
