from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"^(authorization|api[-_]?key|x-api-key|access[-_]?token|"
    r"credential|secret)$",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/\-=]+")
_OPENROUTER_KEY = re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]+\b")


def _clean_secrets(secrets: Iterable[str]) -> tuple[str, ...]:
    return tuple(secret for secret in secrets if isinstance(secret, str) and secret)


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    sanitized = text
    for secret in sorted(_clean_secrets(secrets), key=len, reverse=True):
        sanitized = sanitized.replace(secret, REDACTED)
    sanitized = _BEARER.sub(f"Bearer {REDACTED}", sanitized)
    sanitized = _OPENROUTER_KEY.sub(REDACTED, sanitized)
    return sanitized


def redact(value: Any, secrets: Iterable[str] = ()) -> Any:
    known = _clean_secrets(secrets)
    if isinstance(value, str):
        return redact_text(value, known)
    if isinstance(value, list):
        return [redact(item, known) for item in value]
    if isinstance(value, tuple):
        return [redact(item, known) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _SENSITIVE_KEY.match(key_text):
                sanitized[key_text] = REDACTED
            else:
                sanitized[key_text] = redact(item, known)
        return sanitized
    return value


def secret_match_count(root: Path, secrets: Iterable[str]) -> int:
    needles = [secret.encode("utf-8") for secret in _clean_secrets(secrets)]
    if not needles:
        return 0
    matches = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if any(needle in data for needle in needles):
            matches += 1
    return matches
