from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .summarize import summarize_events


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text or "—"


def _content(item: dict[str, Any]) -> str:
    parts = item.get("content", [])
    if isinstance(parts, str):
        return parts
    if not isinstance(parts, list):
        return str(parts)
    return " ".join(str(part) for part in parts if isinstance(part, str))


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return events


def render_markdown_report(path: Path) -> str:
    events = _load_events(path)
    summary = summarize_events(path)
    config = summary["configuration"]
    counters = summary["counters"]

    started = next((event for event in events if event["event"] == "session_started"), None)
    closed = next((event for event in reversed(events) if event["event"] == "session_closed"), None)
    messages = [
        event.get("attributes", {}).get("item", {})
        for event in events
        if event["event"] == "conversation_item_added"
        and event.get("attributes", {}).get("item", {}).get("type") == "message"
    ]
    tool_events = [
        event.get("attributes", {})
        for event in events
        if event["event"] == "function_tools_executed"
    ]
    errors = [event.get("attributes", {}) for event in events if event["event"] == "error"]

    label = config.get("eval_run_label") or "unlabelled"
    room = (started or {}).get("attributes", {}).get("room_name", "unknown")
    close_attrs = (closed or {}).get("attributes", {})
    close_reason = close_attrs.get("reason", "missing marker (legacy or interrupted run)")

    lines = [
        f"# Voice Agent Run Report — {_cell(label)}",
        "",
        "## Run identity",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source | `{path.name}` |",
        f"| Room | {_cell(room)} |",
        f"| Started (UTC) | {_cell((started or {}).get('timestamp'))} |",
        f"| Close reason | {_cell(close_reason)} |",
        f"| Application errors | {counters['errors']} |",
        "",
        "## Exact system configuration",
        "",
        "| Parameter | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| `{key}` | {_cell(value)} |" for key, value in config.items())

    lines.extend(
        [
            "",
            "## Event counts",
            "",
            "| Event | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(f"| {key.replace('_', ' ').title()} | {value} |" for key, value in counters.items())

    lines.extend(
        [
            "",
            "## Calculated metrics",
            "",
            "All durations are in seconds and are calculated from the captured LiveKit events.",
            "",
            "| Component | Metric | n | Mean | Median (p50) | p95 |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for metric_type, fields in summary["metrics_seconds"].items():
        for field, values in fields.items():
            lines.append(
                "| "
                + " | ".join(
                    [
                        metric_type.replace("_metrics", "").upper(),
                        field.replace("_", " "),
                        _cell(values["count"]),
                        _cell(values["mean"]),
                        _cell(values["p50"]),
                        _cell(values["p95"]),
                    ]
                )
                + " |"
            )

    lines.extend(["", "## Conversation", ""])
    if messages:
        for index, item in enumerate(messages, 1):
            role = str(item.get("role", "unknown")).title()
            interruption = " (interrupted)" if item.get("interrupted") else ""
            lines.extend([f"**{index}. {role}{interruption}:** {_content(item)}", ""])
    else:
        lines.extend(["No committed conversation messages were captured.", ""])

    lines.extend(["## Tool executions", ""])
    if tool_events:
        tool_index = 0
        for batch in tool_events:
            outputs = {
                output.get("call_id"): output
                for output in batch.get("function_call_outputs", [])
            }
            for call in batch.get("function_calls", []):
                tool_index += 1
                output = outputs.get(call.get("call_id"), {})
                lines.extend(
                    [
                        f"### {tool_index}. `{_cell(call.get('name'))}`",
                        "",
                        f"- Arguments: `{_cell(call.get('arguments'))}`",
                        f"- Result: `{_cell(output.get('output'))}`",
                        f"- Error: {_cell(output.get('is_error', False))}",
                        "",
                    ]
                )
    else:
        lines.extend(["No tools were executed.", ""])

    lines.extend(["## Errors", ""])
    if errors:
        for error in errors:
            lines.append(f"- `{_cell(json.dumps(error, ensure_ascii=False))}`")
    else:
        lines.append("No application errors were captured.")

    lines.extend(
        [
            "",
            "## Instrumentation notes",
            "",
            "- `is_final` is a Pulse transcript-segment boundary, not necessarily a complete user turn.",
            "- Committed user messages represent LiveKit turn decisions.",
            "- Raw turn-detector probability is not exposed by the installed LiveKit public session API.",
            "- Structured secrets and phone numbers are redacted before the JSONL file is written.",
            "- Spoken digit words may remain in transcripts; use fictional evaluation data.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(input_path: Path, output_path: Path) -> Path:
    """Render one JSONL session into a human-readable Markdown report."""
    rendered = render_markdown_report(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a readable Markdown run report")
    parser.add_argument("input", type=Path, help="Session JSONL file")
    parser.add_argument("--output", type=Path, help="Markdown destination")
    args = parser.parse_args()

    if args.output:
        output = args.output
    elif args.input.parent.name == "jsonl":
        output = args.input.parent.parent / "reports" / args.input.with_suffix(".md").name
    else:
        output = args.input.with_suffix(".md")
    print(write_markdown_report(args.input, output))


if __name__ == "__main__":
    main()
