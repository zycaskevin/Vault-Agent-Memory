"""Fail-closed public-safety validation for JSON-like values."""

from __future__ import annotations

import base64
import binascii
import math
import re
from typing import Any
from urllib.parse import unquote, unquote_plus, urlsplit

_ERROR = "public-safety validation failed"

_FORBIDDEN_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "access_key",
    "private_key",
    "client_secret",
    "refresh_token",
    "access_token",
    "aws_secret_access_key",
    "credential",
    "capability_secret",
    "raw",
    "raw_evidence",
    "content_raw",
    "private_path",
    "absolute_path",
    "authorization",
}

_PATH_PATTERNS = (
    re.compile(r"//+(?=[^\s])"),
    re.compile(r"(?<![A-Za-z0-9._~/-])/(?!/)[^/\s]"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"),
    re.compile(r"(?<!\\)\\{2}(?=[^\s])"),
    re.compile(r"(?<![A-Za-z0-9+.-])file:(?:/{1,3}|\\{2})", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_])~[\\/]"),
)

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        r"(?:^|[^A-Za-z0-9])(?:gh[pousr]_|github_pat_|glpat-|"
        r"(?:sk|rk)_(?:live|test)_|pk_live_|whsec_|"
        r"(?:xoxb|xoxp|xoxa|xoxr)-|ya29\.|1//)"
        r"[A-Za-z0-9._-]+",
        re.IGNORECASE,
    ),
    re.compile(r"(?:^|[^A-Za-z0-9])(?:AKIA|ASIA)[A-Za-z0-9]{16,}(?![A-Za-z0-9])"),
    re.compile(r"(?:^|[^A-Za-z0-9])(?:AIza|GOCSPX-)[A-Za-z0-9._-]+"),
    re.compile(r"(?:^|[^A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(
        r"(?:^|[^A-Za-z0-9])[A-Za-z0-9_-]{8,}\."
        r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    ),
    re.compile(
        r"(?:^|[^A-Za-z0-9])(?:token|secret|password|passwd|api[._-]?key|"
        r"access[._-]?key|private[._-]?key|credential|client[._-]?secret|"
        r"refresh[._-]?token|aws[._-]?secret[._-]?access[._-]?key)"
        r"(?![A-Za-z0-9])\s*[:=](?=.)",
        re.IGNORECASE | re.DOTALL,
    ),
)

_BASIC_CARRIER_PATTERN = re.compile(
    r"(?:^|[^A-Za-z0-9])Basic[ \t]+([A-Za-z0-9+/]+={0,2})"
    r"(?![A-Za-z0-9+/=])",
    re.IGNORECASE,
)

_BEARER_CARRIER_PATTERN = re.compile(
    r"(?:^|[^A-Za-z0-9])Bearer(\s+|[._:-])([A-Za-z0-9._~+/=-]{8,})",
    re.IGNORECASE,
)
_HTTP_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_ASSIGNMENT_PATTERN = re.compile(
    r"(?:^|[^A-Za-z0-9_.\-/\[\]:])([A-Za-z][A-Za-z0-9_.\-/\[\]: ]{1,96}?)"
    r"\s*[:=](?=\s*\S)"
)
_QUOTED_ASSIGNMENT_PATTERN = re.compile(
    r"(?:^|[^A-Za-z0-9_])['\"]([^'\"]{1,128})['\"]\s*[:=](?=\s*\S)"
)
_BRACKET_ASSIGNMENT_PATTERN = re.compile(r"\[['\"]([^'\"]{1,128})['\"]\]\s*=")
_URL_LOCAL_PATH_PATTERN = re.compile(
    r"(?:^|[=&#?;:\s])(?:/(?:home|tmp|var|etc|root|Users)\b|~[\\/]|[A-Za-z]:[\\/]|file:(?:/{1,3}|\\{2}))",
    re.IGNORECASE,
)


class PublicSafetyError(ValueError):
    """Raised when a value is unsafe for a public artifact."""


def _reject() -> None:
    raise PublicSafetyError(_ERROR)


def _contains_basic_credential(value: str) -> bool:
    for match in _BASIC_CARRIER_PATTERN.finditer(value):
        encoded_candidate = match.group(1)
        padded = encoded_candidate + "=" * (-len(encoded_candidate) % 4)
        try:
            decoded = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            continue
        if b":" in decoded:
            return True
    return False


def _contains_bearer_credential(value: str) -> bool:
    for match in _BEARER_CARRIER_PATTERN.finditer(value):
        separator = match.group(1)
        candidate = match.group(2)
        if separator.strip() or any(character.isdigit() or not character.isalpha() for character in candidate):
            return True
    return False


def _contains_http_userinfo(value: str) -> bool:
    for match in _HTTP_URL_PATTERN.finditer(value):
        try:
            parsed = urlsplit(match.group(0))
            if parsed.scheme.lower() not in {"http", "https"}:
                continue
            userinfo, separator, _ = parsed.netloc.rpartition("@")
            username_present = parsed.username is not None
        except ValueError:
            return True
        if separator and (username_present or ":" in unquote(userinfo)):
            return True
    return False


def _without_http_urls(value: str) -> str:
    return _HTTP_URL_PATTERN.sub("", value)


def _contains_forbidden_assignment(value: str) -> bool:
    for candidate in _assignment_key_candidates(_without_http_urls(value)):
        if _key_is_forbidden(candidate):
            return True
    for match in _HTTP_URL_PATTERN.finditer(value):
        try:
            parsed = urlsplit(match.group(0))
        except ValueError:
            continue
        for component in (parsed.query, parsed.fragment):
            decoded = unquote_plus(component)
            if _contains_sensitive_url_component(decoded):
                return True
    return False


def _assignment_key_candidates(value: str) -> list[str]:
    candidates = [match.group(1) for match in _ASSIGNMENT_PATTERN.finditer(value)]
    candidates.extend(match.group(1) for match in _QUOTED_ASSIGNMENT_PATTERN.finditer(value))
    candidates.extend(match.group(1) for match in _BRACKET_ASSIGNMENT_PATTERN.finditer(value))
    return candidates


def _contains_sensitive_url_component(value: str) -> bool:
    return (
        _contains_basic_credential(value)
        or _contains_bearer_credential(value)
        or any(_key_is_forbidden(candidate) for candidate in _assignment_key_candidates(value))
        or any(pattern.search(value) for pattern in _SECRET_PATTERNS)
        or _URL_LOCAL_PATH_PATTERN.search(value) is not None
    )


def _scan_string(value: str) -> None:
    if "\x00" in value:
        _reject()
    local_path_text = _without_http_urls(value)
    if (
        _contains_basic_credential(value)
        or _contains_bearer_credential(value)
        or _contains_http_userinfo(value)
        or _contains_forbidden_assignment(value)
        or _PATH_PATTERNS[0].search(local_path_text)
        or any(pattern.search(local_path_text) for pattern in _PATH_PATTERNS[1:])
        or any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    ):
        _reject()


def _normalize_key(key: str) -> str:
    separated = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")


def _key_is_forbidden(key: str) -> bool:
    normalized = _normalize_key(key)
    compact = normalized.replace("_", "")
    return any(
        normalized == forbidden
        or normalized.endswith("_" + forbidden)
        or compact == forbidden.replace("_", "")
        or compact.endswith(forbidden.replace("_", ""))
        for forbidden in _FORBIDDEN_KEYS
    )


def validate_public_safe(value: Any) -> None:
    """Reject secret-shaped or local-only content in a JSON-like value."""
    pending = [(False, value)]
    active_containers: set[int] = set()
    while pending:
        exiting, current = pending.pop()
        if exiting:
            active_containers.remove(id(current))
            continue

        current_type = type(current)
        if current_type in (dict, list):
            identity = id(current)
            if identity in active_containers:
                _reject()
            active_containers.add(identity)
            pending.append((True, current))

        if current_type is dict:
            for key, child in current.items():
                if type(key) is not str:
                    _reject()
                if _key_is_forbidden(key):
                    _reject()
                _scan_string(key)
                pending.append((False, child))
        elif current_type is list:
            pending.extend((False, child) for child in current)
        elif current_type is str:
            _scan_string(current)
        elif current is None or current_type in (bool, int):
            continue
        elif current_type is float:
            if not math.isfinite(current):
                _reject()
        else:
            _reject()
