from datetime import date

from scripts.evaluate_electron import ModelResult, build_scenarios, score_result


def result(
    *,
    text: str = "",
    tool_calls: list | None = None,
    finish_reason: str = "stop",
) -> ModelResult:
    return ModelResult(
        text=text,
        tool_calls=tool_calls or [],
        ttft_ms=200.0,
        total_ms=400.0,
        finish_reason=finish_reason,
        prompt_tokens=100,
        completion_tokens=20,
    )


def scenario_by_id(scenario_id: str):
    return next(
        scenario
        for scenario in build_scenarios(date(2026, 9, 4))
        if scenario.id == scenario_id
    )


def test_absolute_availability_requires_exact_tool_arguments() -> None:
    scenario = scenario_by_id("availability_absolute")
    passed, reasons = score_result(
        scenario,
        result(
            tool_calls=[
                {
                    "name": "check_availability",
                    "arguments": {"requested_date": "2026-09-06"},
                }
            ]
        ),
    )
    assert passed
    assert reasons == []


def test_booking_gate_rejects_a_tool_call() -> None:
    scenario = scenario_by_id("confirmation_gate")
    passed, reasons = score_result(
        scenario,
        result(tool_calls=[{"name": "book_appointment", "arguments": {}}]),
    )
    assert not passed
    assert "forbidden tool call" in reasons[0]


def test_booking_gate_allows_phone_validation() -> None:
    scenario = scenario_by_id("confirmation_gate")
    passed, reasons = score_result(
        scenario,
        result(
            tool_calls=[
                {
                    "name": "validate_phone_number",
                    "arguments": {"phone_number": "0000001234"},
                }
            ]
        ),
    )
    assert passed
    assert reasons == []


def test_token_truncation_is_a_failure() -> None:
    scenario = scenario_by_id("urgent_medical_safety")
    passed, reasons = score_result(
        scenario,
        result(text="Contact emergency services.", finish_reason="length"),
    )
    assert not passed
    assert "truncated" in reasons[-1]


def test_doctor_abbreviation_does_not_count_as_an_extra_sentence() -> None:
    scenario = scenario_by_id("availability_tool_result")
    passed, reasons = score_result(
        scenario,
        result(
            text=(
                "We have 9:30 AM and 4:00 PM available with Dr. Rao. "
                "Which one works best for you?"
            )
        ),
    )
    assert passed
    assert reasons == []
