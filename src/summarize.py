from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any

METRIC_FIELDS = {
    "eou_metrics": ["end_of_utterance_delay", "transcription_delay"],
    "llm_metrics": ["ttft", "duration", "tokens_per_second"],
    "tts_metrics": ["ttfb", "duration", "audio_duration"],
    "stt_metrics": ["audio_duration", "acquire_time"],
}


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile of an empty list")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def summarize_events(path: Path) -> dict[str, Any]:
    configuration: dict[str, Any] = {}
    collected: dict[str, dict[str, list[float]]] = {
        metric_type: {field: [] for field in fields}
        for metric_type, fields in METRIC_FIELDS.items()
    }
    counters = {
        "final_transcripts": 0,
        "interim_transcripts": 0,
        "conversation_messages": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "tool_batches": 0,
        "errors": 0,
    }

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        name = event["event"]
        attributes = event.get("attributes", {})

        if name == "configuration":
            configuration = attributes
        elif name == "user_input_transcribed":
            key = "final_transcripts" if attributes.get("is_final") else "interim_transcripts"
            counters[key] += 1
        elif name == "conversation_item_added":
            counters["conversation_messages"] += 1
            role = attributes.get("item", {}).get("role")
            if role == "user":
                counters["user_messages"] += 1
            elif role == "assistant":
                counters["assistant_messages"] += 1
        elif name == "function_tools_executed":
            counters["tool_batches"] += 1
        elif name == "error":
            counters["errors"] += 1
        elif name == "metrics_collected":
            metric = attributes.get("metrics", {})
            metric_type = metric.get("type")
            if metric_type not in collected:
                continue
            for field in METRIC_FIELDS[metric_type]:
                value = metric.get(field)
                if isinstance(value, int | float) and value >= 0:
                    collected[metric_type][field].append(float(value))

    summaries: dict[str, dict[str, dict[str, float | int]]] = {}
    for metric_type, fields in collected.items():
        metric_summary: dict[str, dict[str, float | int]] = {}
        for field, values in fields.items():
            if not values:
                continue
            metric_summary[field] = {
                "count": len(values),
                "mean": round(statistics.fmean(values), 4),
                "p50": round(statistics.median(values), 4),
                "p95": round(_percentile(values, 0.95), 4),
            }
        if metric_summary:
            summaries[metric_type] = metric_summary

    return {
        "source": str(path),
        "configuration": configuration,
        "counters": counters,
        "metrics_seconds": summaries,
    }


def write_flat_csv(summary: dict[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for metric_type, fields in summary["metrics_seconds"].items():
        for field, values in fields.items():
            rows.append({"metric_type": metric_type, "field": field, **values})

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["metric_type", "field", "count", "mean", "p50", "p95"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize one voice-agent JSONL run")
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--csv", dest="csv_path", type=Path)
    args = parser.parse_args()

    summary = summarize_events(args.input)
    rendered = json.dumps(summary, indent=2, ensure_ascii=False)
    print(rendered)

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(rendered + "\n", encoding="utf-8")
    if args.csv_path:
        write_flat_csv(summary, args.csv_path)


if __name__ == "__main__":
    main()
