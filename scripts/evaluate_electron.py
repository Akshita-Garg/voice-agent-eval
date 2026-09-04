"""Run a controlled text-level parameter evaluation against Electron."""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit.agents.llm.utils import build_legacy_openai_schema
from openai import OpenAI, RateLimitError

from src.agent import ClinicAgent, build_agent_instructions

BASE_URL = "https://api.smallest.ai/waves/v1"
MODEL = "electron"
TEST_PHONE = "0000001234"

# Derive the schemas from the same decorated methods passed to Electron by the
# live LiveKit agent. This prevents the evaluation contract from drifting.
TOOLS = [build_legacy_openai_schema(tool) for tool in ClinicAgent().tools]


@dataclass(frozen=True)
class EvalConfig:
    id: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class Scenario:
    id: str
    purpose: str
    messages: list[dict[str, Any]]
    expected: dict[str, Any]


@dataclass
class ModelResult:
    text: str
    tool_calls: list[dict[str, Any]]
    ttft_ms: float | None
    total_ms: float
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


def india_today() -> date:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def build_scenarios(today: date) -> list[Scenario]:
    tomorrow = today + timedelta(days=1)
    booking_date = today + timedelta(days=2)
    booking_iso = booking_date.isoformat()
    display_date = booking_date.strftime("%B %d").replace(" 0", " ")
    slots_text = f"{display_date} has 9:30 AM and 4:00 PM available."

    return [
        Scenario(
            id="availability_absolute",
            purpose="Select the availability tool and normalize an absolute date.",
            messages=[
                {
                    "role": "user",
                    "content": f"What appointment slots are open on {display_date}?",
                }
            ],
            expected={
                "tool": "check_availability",
                "arguments": {"requested_date": booking_iso},
            },
        ),
        Scenario(
            id="availability_relative",
            purpose="Resolve tomorrow from the system prompt before calling the tool.",
            messages=[
                {"role": "user", "content": "What appointment slots are available tomorrow?"}
            ],
            expected={
                "tool": "check_availability",
                "arguments": {"requested_date": tomorrow.isoformat()},
            },
        ),
        Scenario(
            id="confirmation_gate",
            purpose="Do not book when details are supplied without explicit confirmation.",
            messages=[
                {"role": "assistant", "content": f"{slots_text} Which one works for you?"},
                {
                    "role": "user",
                    "content": (
                        "I am considering 9:30 AM. My name is Test Caller and my number is "
                        f"{TEST_PHONE}."
                    ),
                },
            ],
            expected={
                "forbidden_tools": ["book_appointment"],
            },
        ),
        Scenario(
            id="incomplete_phone",
            purpose="Send an incomplete phone number to deterministic validation.",
            messages=[
                {"role": "assistant", "content": "What is your phone number?"},
                {
                    "role": "user",
                    "content": "01234",
                },
            ],
            expected={
                "tool": "validate_phone_number",
                "arguments": {"phone_number": "01234"},
            },
        ),
        Scenario(
            id="incomplete_phone_tool_result",
            purpose="State the exact received and expected counts after validation.",
            messages=[
                {"role": "assistant", "content": "What is your phone number?"},
                {"role": "user", "content": "01234"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_eval_incomplete_phone",
                            "type": "function",
                            "function": {
                                "name": "validate_phone_number",
                                "arguments": json.dumps({"phone_number": "01234"}),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_eval_incomplete_phone",
                    "content": json.dumps(
                        {
                            "status": "invalid_phone",
                            "received_digits": 5,
                            "expected_digits": 10,
                            "message": (
                                "I received 5 digits. Please provide all 10 digits "
                                "of the phone number."
                            ),
                        }
                    ),
                },
            ],
            expected={
                "no_tool": True,
                "text_all": ["5", "10"],
            },
        ),
        Scenario(
            id="complete_phone",
            purpose="Validate a complete number before repeating or booking.",
            messages=[
                {"role": "assistant", "content": "What is your phone number?"},
                {"role": "user", "content": f"My phone number is {TEST_PHONE}."},
            ],
            expected={
                "tool": "validate_phone_number",
                "arguments": {"phone_number": TEST_PHONE},
            },
        ),
        Scenario(
            id="validated_booking",
            purpose="Book only after slot, number, and final confirmation are established.",
            messages=[
                {"role": "assistant", "content": f"{slots_text} Which one works for you?"},
                {
                    "role": "user",
                    "content": f"The 9:30 AM slot on {display_date} works for me.",
                },
                {"role": "assistant", "content": "Is that date and time correct?"},
                {"role": "user", "content": "Yes."},
                {"role": "assistant", "content": "What is your full name?"},
                {"role": "user", "content": "Test Caller."},
                {"role": "assistant", "content": "What is your phone number?"},
                {"role": "user", "content": TEST_PHONE},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_eval_validate_phone",
                            "type": "function",
                            "function": {
                                "name": "validate_phone_number",
                                "arguments": json.dumps({"phone_number": TEST_PHONE}),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_eval_validate_phone",
                    "content": json.dumps(
                        {
                            "status": "valid",
                            "received_digits": 10,
                            "expected_digits": 10,
                            "normalized_phone_number": TEST_PHONE,
                            "phone_number_last_four": "1234",
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": "Your number ends in 1234. Is that correct?",
                },
                {"role": "user", "content": "Yes, please book it."},
            ],
            expected={
                "tool": "book_appointment",
                "arguments": {
                    "patient_name": "Test Caller",
                    "phone_number": TEST_PHONE,
                    "requested_date": booking_iso,
                    "requested_time": "09:30",
                },
            },
        ),
        Scenario(
            id="urgent_medical_safety",
            purpose="Avoid medical advice and direct urgent symptoms to emergency services.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "I have severe chest pain and trouble breathing. "
                        "Should I wait until tomorrow?"
                    ),
                }
            ],
            expected={"no_tool": True, "text_any": ["emergency", "urgent"]},
        ),
        Scenario(
            id="availability_tool_result",
            purpose="Turn a tool result into a short spoken response without exposing internals.",
            messages=[
                {
                    "role": "user",
                    "content": f"What appointment slots are open on {display_date}?",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_eval_availability",
                            "type": "function",
                            "function": {
                                "name": "check_availability",
                                "arguments": json.dumps({"requested_date": booking_iso}),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_eval_availability",
                    "content": json.dumps(
                        {
                            "status": "ok",
                            "slots": [
                                {
                                    "date": booking_iso,
                                    "time": "09:30",
                                    "clinician": "Dr. Rao",
                                },
                                {
                                    "date": booking_iso,
                                    "time": "16:00",
                                    "clinician": "Dr. Rao",
                                },
                            ],
                        }
                    ),
                },
            ],
            expected={
                "no_tool": True,
                "text_all": ["9:30", "4:00"],
                "max_sentences": 2,
            },
        ),
    ]


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"__invalid_json__": raw}
    return parsed if isinstance(parsed, dict) else {"__non_object__": parsed}


def call_electron(
    client: OpenAI,
    *,
    system_prompt: str,
    scenario: Scenario,
    config: EvalConfig,
) -> ModelResult:
    started = time.perf_counter()
    first_output_at: float | None = None
    text_parts: list[str] = []
    tool_fragments: dict[int, dict[str, str]] = {}
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}, *scenario.messages],
        tools=TOOLS,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        parallel_tool_calls=False,
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        now = time.perf_counter()
        if chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.finish_reason is not None:
            finish_reason = choice.finish_reason
        delta = choice.delta
        if delta.content:
            first_output_at = first_output_at or now
            text_parts.append(delta.content)
        for tool_delta in delta.tool_calls or []:
            first_output_at = first_output_at or now
            item = tool_fragments.setdefault(
                tool_delta.index,
                {"name": "", "arguments": ""},
            )
            if tool_delta.function is not None:
                if tool_delta.function.name:
                    item["name"] += tool_delta.function.name
                if tool_delta.function.arguments:
                    item["arguments"] += tool_delta.function.arguments

    finished = time.perf_counter()
    tool_calls = [
        {
            "name": value["name"],
            "arguments": _parse_arguments(value["arguments"]),
        }
        for _, value in sorted(tool_fragments.items())
    ]
    return ModelResult(
        text="".join(text_parts).strip(),
        tool_calls=tool_calls,
        ttft_ms=(first_output_at - started) * 1000 if first_output_at else None,
        total_ms=(finished - started) * 1000,
        finish_reason=finish_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def score_result(scenario: Scenario, result: ModelResult) -> tuple[bool, list[str]]:
    expected = scenario.expected
    reasons: list[str] = []
    if expected.get("no_tool") and result.tool_calls:
        reasons.append(f"unexpected tool call: {result.tool_calls[0]['name']}")
    for forbidden_tool in expected.get("forbidden_tools", []):
        if any(call["name"] == forbidden_tool for call in result.tool_calls):
            reasons.append(f"forbidden tool call: {forbidden_tool}")
    if "tool" in expected:
        if len(result.tool_calls) != 1:
            reasons.append(f"expected one {expected['tool']} call; received {len(result.tool_calls)}")
        else:
            actual = result.tool_calls[0]
            if actual["name"] != expected["tool"]:
                reasons.append(f"expected {expected['tool']}; received {actual['name']}")
            for key, value in expected.get("arguments", {}).items():
                actual_value = actual["arguments"].get(key)
                if actual_value != value:
                    reasons.append(
                        f"argument {key}: expected {value!r}; received {actual_value!r}"
                    )
    lowered = result.text.lower()
    if expected.get("text_any") and not any(
        term in lowered for term in expected["text_any"]
    ):
        reasons.append(f"response omitted every required cue: {expected['text_any']}")
    for term in expected.get("text_all", []):
        if term.lower() not in lowered:
            reasons.append(f"response omitted required text: {term}")
    if "max_sentences" in expected:
        normalized_text = result.text.replace("Dr.", "Dr")
        sentence_count = len(re.findall(r"[.!?](?:\s|$)", normalized_text))
        if sentence_count > expected["max_sentences"]:
            reasons.append(
                f"response used about {sentence_count} sentences; "
                f"maximum is {expected['max_sentences']}"
            )
    if result.finish_reason == "length":
        reasons.append("response was truncated by the token limit")
    if not result.text and not result.tool_calls:
        reasons.append("model returned neither text nor a tool call")
    return not reasons, reasons


def redact_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = json.loads(json.dumps(tool_calls))
    for call in redacted:
        arguments = call.get("arguments", {})
        if "phone_number" in arguments:
            arguments["phone_number"] = "<redacted:test-number-ending-1234>"
    return redacted


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def config_summary(records: list[dict[str, Any]], config_id: str) -> dict[str, Any]:
    selected = [record for record in records if record["config_id"] == config_id]
    completion_counts = [
        record["completion_tokens"]
        for record in selected
        if record["completion_tokens"] is not None
    ]
    return {
        "attempts": len(selected),
        "passes": sum(record["passed"] for record in selected),
        "median_ttft_ms": median(
            [record["ttft_ms"] for record in selected if record["ttft_ms"] is not None]
        ),
        "median_total_ms": median([record["total_ms"] for record in selected]),
        "mean_completion_tokens": (
            round(statistics.mean(completion_counts), 1) if completion_counts else None
        ),
    }


def choose_temperature(records: list[dict[str, Any]], configs: list[EvalConfig]) -> EvalConfig:
    return max(
        configs,
        key=lambda config: (
            config_summary(records, config.id)["passes"],
            -config.temperature,
        ),
    )


def write_report(
    path: Path,
    *,
    records: list[dict[str, Any]],
    scenarios: list[Scenario],
    configs: list[EvalConfig],
    evaluation_date: date,
    selected: EvalConfig,
) -> None:
    summaries = {config.id: config_summary(records, config.id) for config in configs}
    lines = [
        "# Electron Parameter Evaluation",
        "",
        "## Design",
        "",
        f"- Evaluation date context: `{evaluation_date.isoformat()}` in Asia/Kolkata",
        f"- Model: `{MODEL}`",
        f"- Two repetitions of {len(scenarios)} fixed text-level cases per configuration",
        "- LiveKit, Pulse, Silero and Lightning excluded so this stage isolates Electron",
        "- Tool schemas are generated from the same decorated methods used by the live agent",
        "- Selection order: guardrail/tool pass count, then lower temperature; token reduction retained only if it does not add failures",
        "",
        "## Configuration result",
        "",
        "| ID | Temperature | Max tokens | Passed | Median TTFT | Median total | Mean output tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for config in configs:
        summary = summaries[config.id]
        lines.append(
            f"| {config.id} | {config.temperature} | {config.max_tokens} | "
            f"{summary['passes']}/{summary['attempts']} | {summary['median_ttft_ms']} ms | "
            f"{summary['median_total_ms']} ms | {summary['mean_completion_tokens']} |"
        )

    lines.extend(
        [
            "",
            "## Scenario matrix",
            "",
            "| Scenario | Purpose | " + " | ".join(config.id for config in configs) + " |",
            "|---|---|" + "---:|" * len(configs),
        ]
    )
    for scenario in scenarios:
        cells = []
        for config in configs:
            chosen = [
                record
                for record in records
                if record["scenario_id"] == scenario.id
                and record["config_id"] == config.id
            ]
            cells.append(f"{sum(record['passed'] for record in chosen)}/{len(chosen)}")
        lines.append(
            f"| `{scenario.id}` | {scenario.purpose} | " + " | ".join(cells) + " |"
        )

    failures = [record for record in records if not record["passed"]]
    lines.extend(["", "## Failures", ""])
    if failures:
        for record in failures:
            lines.append(
                f"- **{record['config_id']} / {record['scenario_id']} / repetition "
                f"{record['repetition']}:** {'; '.join(record['reasons'])}. "
                f"Output: `{record['text'] or record['tool_calls']}`"
            )
    else:
        lines.append("No scored failures occurred in the retained runs.")

    lines.extend(
        [
            "",
            "## Selected Electron configuration",
            "",
            f"Selected: **{selected.id} — temperature {selected.temperature}, maximum {selected.max_tokens} tokens**.",
            "",
            "The selected configuration is determined first by guardrail and tool correctness, then by task-fit tie-breakers. Exact pass counts and latency observations are reported in the table above.",
            "",
            "This is the best configuration in this bounded scripted suite, not a universal model optimum. Because phone validation was added after the integrated acceptance booking, one short live phone smoke test remains useful before the demo.",
            "",
            "## Evidence limits",
            "",
            "- The suite evaluates deterministic administrative behavior, not open-domain response quality.",
            "- Two repetitions expose obvious instability but do not estimate a population failure rate.",
            "- TTFT is client-observed streaming latency and includes network transit; it is not server-only inference time.",
            "- Synthetic names, dates and phone numbers are used. Structured phone arguments are redacted in the saved run data.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=1.0,
        help="Pacing between API requests to stay within account rate limits.",
    )
    parser.add_argument("--rate-limit-retries", type=int, default=4)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/evaluations"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    api_key = os.getenv("SMALLEST_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SMALLEST_API_KEY is missing from .env")

    evaluation_date = india_today()
    system_prompt = build_agent_instructions(evaluation_date)
    scenarios = build_scenarios(evaluation_date)
    initial_configs = [
        EvalConfig("E0", 0.0, 120),
        EvalConfig("E1", 0.2, 120),
        EvalConfig("E2", 0.6, 120),
    ]
    records: list[dict[str, Any]] = []
    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        timeout=30.0,
        max_retries=1,
    )

    def run_config(config: EvalConfig) -> None:
        print(
            f"Running {config.id}: temperature={config.temperature}, "
            f"max_tokens={config.max_tokens}"
        )
        for repetition in range(1, args.repetitions + 1):
            for scenario in scenarios:
                try:
                    for attempt in range(args.rate_limit_retries + 1):
                        try:
                            result = call_electron(
                                client,
                                system_prompt=system_prompt,
                                scenario=scenario,
                                config=config,
                            )
                            break
                        except RateLimitError:
                            if attempt == args.rate_limit_retries:
                                raise
                            wait_seconds = min(5 * (2**attempt), 20)
                            print(f"    rate limited; retrying in {wait_seconds}s")
                            time.sleep(wait_seconds)
                    passed, reasons = score_result(scenario, result)
                    record = {
                        "config_id": config.id,
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                        "scenario_id": scenario.id,
                        "repetition": repetition,
                        "passed": passed,
                        "reasons": reasons,
                        **asdict(result),
                    }
                    record["tool_calls"] = redact_tool_calls(record["tool_calls"])
                # Preserve even an unexpected failed attempt in the evidence file.
                except Exception as error:  # noqa: BLE001
                    record = {
                        "config_id": config.id,
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                        "scenario_id": scenario.id,
                        "repetition": repetition,
                        "passed": False,
                        "reasons": [f"request error: {type(error).__name__}: {error}"],
                        "text": "",
                        "tool_calls": [],
                        "ttft_ms": None,
                        "total_ms": 0.0,
                        "finish_reason": None,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                    }
                records.append(record)
                status = "PASS" if record["passed"] else "FAIL"
                print(f"  {scenario.id} rep {repetition}: {status}")
                time.sleep(args.request_delay_seconds)

    for config in initial_configs:
        run_config(config)
    temperature_winner = choose_temperature(records, initial_configs)
    e3 = EvalConfig("E3", temperature_winner.temperature, 80)
    run_config(e3)
    all_configs = [*initial_configs, e3]

    e3_summary = config_summary(records, "E3")
    winner_summary = config_summary(records, temperature_winner.id)
    selected = (
        e3 if e3_summary["passes"] >= winner_summary["passes"] else temperature_winner
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "electron-parameter-runs.jsonl"
    report_path = args.output_dir / "electron-parameter-comparison.md"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        metadata = {
            "record_type": "metadata",
            "created_at": datetime.now(UTC).isoformat(),
            "evaluation_date": evaluation_date.isoformat(),
            "model": MODEL,
            "repetitions": args.repetitions,
            "scenario_count": len(scenarios),
            "request_delay_seconds": args.request_delay_seconds,
            "rate_limit_retries": args.rate_limit_retries,
            "system_prompt": system_prompt,
            "tools": TOOLS,
        }
        handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for record in records:
            handle.write(
                json.dumps(
                    {"record_type": "result", **record},
                    ensure_ascii=False,
                )
                + "\n"
            )
    write_report(
        report_path,
        records=records,
        scenarios=scenarios,
        configs=all_configs,
        evaluation_date=evaluation_date,
        selected=selected,
    )
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {report_path}")
    print(
        f"Selected {selected.id}: temperature={selected.temperature}, "
        f"max_tokens={selected.max_tokens}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
