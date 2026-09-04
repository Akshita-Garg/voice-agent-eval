from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.metrics import JsonlMetricSink, MetricEvent, redact_sensitive_data


class NonClosingStringIO(StringIO):
    def close(self) -> None:
        pass


def test_redacts_phone_number_in_nested_tool_arguments() -> None:
    value = {
        "arguments": '{"patient_name":"Test","phone_number":"0123456789"}',
        "output": {"phone_number": "0123456789", "phone_number_last_four": "6789"},
    }

    redacted = redact_sensitive_data(value)

    assert "0123456789" not in json.dumps(redacted)
    assert redacted["output"]["phone_number"] == "[REDACTED]"
    assert redacted["output"]["phone_number_last_four"] == "6789"


def test_sink_writes_redacted_payload() -> None:
    handle = NonClosingStringIO()
    path = Path("results/test-session.jsonl")

    with (
        patch.object(Path, "mkdir"),
        patch.object(Path, "open", return_value=handle),
    ):
        JsonlMetricSink(path).write(
            MetricEvent(
                event="function_tools_executed",
                monotonic_ms=1.0,
                attributes={"phone_number": "0123456789"},
            )
        )

    assert json.loads(handle.getvalue())["attributes"]["phone_number"] == "[REDACTED]"


def test_phone_configuration_is_not_mistaken_for_a_phone_value() -> None:
    value = {
        "phone_number_scope": "India-local",
        "phone_number_expected_digits": 10,
        "normalized_phone_number": "0123456789",
    }

    redacted = redact_sensitive_data(value)

    assert redacted["phone_number_scope"] == "India-local"
    assert redacted["phone_number_expected_digits"] == 10
    assert redacted["normalized_phone_number"] == "[REDACTED]"
