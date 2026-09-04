from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

_SENSITIVE_KEY_PARTS = ("api_key", "api_secret", "authorization", "phone_number")
_JSON_PHONE_PATTERN = re.compile(r'("phone_number"\s*:\s*")[^"]*(")', re.IGNORECASE)
_PYTHON_PHONE_PATTERN = re.compile(r"('phone_number'\s*:\s*')[^']*(')", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]+")
_LONG_DIGIT_PATTERN = re.compile(r"(?<!\d)(\d{3})\d{3,}(\d{4})(?!\d)")


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact secrets and phone numbers before they reach disk."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if "last_four" not in normalized and any(
                sensitive in normalized for sensitive in _SENSITIVE_KEY_PARTS
            ):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    if isinstance(value, str):
        value = _JSON_PHONE_PATTERN.sub(r'\1[REDACTED]\2', value)
        value = _PYTHON_PHONE_PATTERN.sub(r"\1[REDACTED]\2", value)
        value = _BEARER_PATTERN.sub(r"\1[REDACTED]", value)
        return _LONG_DIGIT_PATTERN.sub(r"\1***\2", value)
    return value


@dataclass
class MetricEvent:
    event: str
    monotonic_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    attributes: dict[str, Any] = field(default_factory=dict)


class JsonlMetricSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(self, event: MetricEvent) -> None:
        payload = asdict(event)
        payload["attributes"] = redact_sensitive_data(payload["attributes"])
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
