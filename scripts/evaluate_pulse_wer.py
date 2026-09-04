"""Derive normalized Pulse WER from the retained fixed-audio LiveKit logs."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.wer import WordErrors, normalize_transcript, word_errors


def pulse_hypothesis(path: Path) -> str:
    """Concatenate non-overlapping Pulse final segments in event order."""
    segments: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            attributes = record.get("attributes", {})
            if (
                record.get("event") == "user_input_transcribed"
                and attributes.get("is_final") is True
            ):
                transcript = str(attributes.get("transcript", "")).strip()
                if transcript:
                    segments.append(transcript)
    return " ".join(segments)


def identify_run(path: Path, fixtures: dict[str, str]) -> tuple[str, str] | None:
    config_match = re.search(r"recorded-r([012])(?:-|_)", path.name)
    if not config_match:
        return None
    fixture_id = next((name for name in fixtures if name in path.name), None)
    if fixture_id is None:
        return None
    return f"R{config_match.group(1)}", fixture_id


def combine_errors(items: list[WordErrors]) -> WordErrors:
    return WordErrors(
        substitutions=sum(item.substitutions for item in items),
        deletions=sum(item.deletions for item in items),
        insertions=sum(item.insertions for item in items),
        reference_words=sum(item.reference_words for item in items),
    )


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_report(path: Path, records: list[dict[str, Any]]) -> None:
    by_config: dict[str, list[WordErrors]] = defaultdict(list)
    by_fixture: dict[str, list[WordErrors]] = defaultdict(list)
    all_errors: list[WordErrors] = []
    for record in records:
        errors = WordErrors(
            substitutions=record["substitutions"],
            deletions=record["deletions"],
            insertions=record["insertions"],
            reference_words=record["reference_words"],
        )
        by_config[record["config"]].append(errors)
        by_fixture[record["fixture"]].append(errors)
        all_errors.append(errors)

    overall = combine_errors(all_errors)
    lines = [
        "# Pulse Fixed-Audio Word Error Rate",
        "",
        "## Method",
        "",
        f"- {len(records)} retained replays of three fixed human recordings",
        "- Reference transcripts: `tests/audio/manifest.json`",
        "- Hypotheses: Pulse `is_final=true` segments concatenated in event order",
        "- Normalization: lowercase, punctuation removed, and equivalent single-digit",
        "  forms normalized (for example, `sixth` and `6th` both become `6`)",
        "- Formula: `(substitutions + deletions + insertions) / reference words`",
        "",
        "## Result by endpointing configuration",
        "",
        "| Config | Runs | Ref. words | Substitutions | Deletions | Insertions | WER |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for config in sorted(by_config):
        errors = combine_errors(by_config[config])
        lines.append(
            f"| {config} | {len(by_config[config])} | {errors.reference_words} | "
            f"{errors.substitutions} | {errors.deletions} | {errors.insertions} | "
            f"{percent(errors.wer)} |"
        )
    lines.extend(
        [
            (
                f"| **Overall** | **{len(records)}** | **{overall.reference_words}** | "
                f"**{overall.substitutions}** | **{overall.deletions}** | "
                f"**{overall.insertions}** | **{percent(overall.wer)}** |"
            ),
            "",
            "## Result by fixture",
            "",
            "| Fixture | Runs | Ref. words | Errors | WER |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for fixture in sorted(by_fixture):
        errors = combine_errors(by_fixture[fixture])
        lines.append(
            f"| `{fixture}` | {len(by_fixture[fixture])} | {errors.reference_words} | "
            f"{errors.errors} | {percent(errors.wer)} |"
        )

    failures = [record for record in records if record["errors"]]
    lines.extend(["", "## Runs containing errors", ""])
    for record in failures:
        lines.extend(
            [
                (
                    f"- **{record['config']} / `{record['fixture']}` / repetition "
                    f"{record['repetition']} — {percent(record['wer'])}:**"
                ),
                f"  reference: “{record['reference']}”",
                f"  Pulse: “{record['hypothesis']}”",
            ]
        )
    if not failures:
        lines.append("No normalized word errors were observed.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                f"Pulse's descriptive normalized WER on this tiny fixed set was "
                f"**{percent(overall.wer)}** ({overall.errors}/{overall.reference_words} "
                "word errors). Most runs were exact after normalization; retained errors were"
            ),
            "name variation (`Caller` → `Coller`/`Collur`) and one `appointment` →",
            "`in a point` recognition.",
            "",
            "This table is an STT sanity check, not evidence that an endpointing setting",
            "caused better or worse lexical accuracy. R0–R2 changed finalization behavior,",
            "the sample has only two repetitions per fixture/configuration, and the same",
            "Pulse model was used throughout. Endpointing selection therefore remains based",
            "on turn fragmentation and latency.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("tests/audio/manifest.json"))
    parser.add_argument("--jsonl-dir", type=Path, default=Path("results/jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/evaluations"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fixtures = {
        Path(item["file"]).stem: item["expected_transcript"]
        for item in manifest["fixtures"]
    }
    grouped_paths: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for path in sorted(args.jsonl_dir.glob("session-recorded-*.jsonl")):
        identity = identify_run(path, fixtures)
        if identity is not None:
            grouped_paths[identity].append(path)

    records: list[dict[str, Any]] = []
    for (config, fixture), paths in sorted(grouped_paths.items()):
        for repetition, path in enumerate(paths, start=1):
            reference = fixtures[fixture]
            hypothesis = pulse_hypothesis(path)
            errors = word_errors(reference, hypothesis)
            records.append(
                {
                    "config": config,
                    "fixture": fixture,
                    "repetition": repetition,
                    "source": str(path.as_posix()),
                    "reference": reference,
                    "hypothesis": hypothesis,
                    "normalized_reference": normalize_transcript(reference),
                    "normalized_hypothesis": normalize_transcript(hypothesis),
                    "reference_words": errors.reference_words,
                    "substitutions": errors.substitutions,
                    "deletions": errors.deletions,
                    "insertions": errors.insertions,
                    "errors": errors.errors,
                    "wer": errors.wer,
                }
            )

    if len(records) != 18:
        raise RuntimeError(f"Expected 18 retained R0–R2 runs; found {len(records)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / "pulse-wer-runs.jsonl"
    report_path = args.output_dir / "pulse-wer-summary.md"
    with raw_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "record_type": "metadata",
                    "created_at": datetime.now(UTC).isoformat(),
                    "run_count": len(records),
                    "normalization": (
                        "lowercase, punctuation removed, equivalent single-digit and "
                        "single-digit ordinal forms normalized"
                    ),
                }
            )
            + "\n"
        )
        for record in records:
            handle.write(json.dumps({"record_type": "result", **record}) + "\n")
    write_report(report_path, records)
    print(f"Wrote {raw_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
