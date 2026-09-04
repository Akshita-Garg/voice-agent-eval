"""Evaluate Lightning speed and streaming-buffer settings with fixed phrases."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
import wave
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv
from livekit.plugins import smallestai

from src.config import AgentConfig


@dataclass(frozen=True)
class LightningConfig:
    id: str
    speed: float
    max_buffer_flush_ms: int


@dataclass(frozen=True)
class Phrase:
    id: str
    text: str
    listen_for: str


PHRASES = [
    Phrase(
        "greeting",
        "Hi, I'm Aisha from Stars Hollow. How can I help you with an appointment today?",
        "Aisha and Stars Hollow sound natural.",
    ),
    Phrase(
        "date_and_times",
        "We have September 6th available at 9:30 AM and 4:00 PM. Which time works best?",
        "September 6th, 9:30 AM, and 4:00 PM are unambiguous.",
    ),
    Phrase(
        "phone_digits",
        "I have your phone number ending in 1 2 3 4. Is that correct?",
        "The four digits remain distinct rather than running together.",
    ),
    Phrase(
        "booking_id",
        "Your appointment is confirmed. Your booking reference is A P T 7 F 3 K 9.",
        "Every letter and digit in A P T 7 F 3 K 9 is recoverable.",
    ),
    Phrase(
        "emergency",
        "Please contact your local emergency services immediately. This may be urgent.",
        "The safety message is clear and appropriately paced.",
    ),
    Phrase(
        "tool_filler",
        "Let me check the available times.",
        "The short filler does not sound rushed or sluggish.",
    ),
]


def pcm_duration_seconds(byte_count: int, sample_rate: int, channels: int = 1) -> float:
    return byte_count / (sample_rate * channels * 2)


def write_montage(
    path: Path,
    clips: list[bytes],
    *,
    sample_rate: int,
    silence_ms: int = 600,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    silence = b"\x00\x00" * int(sample_rate * silence_ms / 1000)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index, clip in enumerate(clips):
            if index:
                wav.writeframes(silence)
            wav.writeframes(clip)


async def synthesize_phrase(
    tts: smallestai.TTS,
    phrase: Phrase,
    *,
    token_interval_ms: int,
) -> tuple[bytes, dict[str, Any]]:
    audio_parts: list[bytes] = []
    started = time.perf_counter()
    first_audio_at: float | None = None

    async with tts.stream() as stream:
        async def produce() -> None:
            words = phrase.text.split()
            for index, word in enumerate(words):
                suffix = " " if index < len(words) - 1 else ""
                stream.push_text(word + suffix)
                if index < len(words) - 1:
                    await asyncio.sleep(token_interval_ms / 1000)
            stream.end_input()

        producer = asyncio.create_task(produce())
        async for event in stream:
            now = time.perf_counter()
            first_audio_at = first_audio_at or now
            audio_parts.append(event.frame.data.tobytes())
        await producer

    finished = time.perf_counter()
    audio = b"".join(audio_parts)
    return audio, {
        "ttfb_ms": (first_audio_at - started) * 1000 if first_audio_at else None,
        "total_ms": (finished - started) * 1000,
        "audio_bytes": len(audio),
        "error": None,
    }


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def summarize_config(
    records: list[dict[str, Any]],
    config: LightningConfig,
) -> dict[str, Any]:
    selected = [record for record in records if record["config_id"] == config.id]
    successes = [record for record in selected if record["error"] is None]
    return {
        "attempts": len(selected),
        "successes": len(successes),
        "median_ttfb_ms": median(
            [record["ttfb_ms"] for record in successes if record["ttfb_ms"] is not None]
        ),
        "median_total_ms": median([record["total_ms"] for record in successes]),
        "mean_audio_seconds": (
            round(statistics.mean(record["audio_seconds"] for record in successes), 3)
            if successes
            else None
        ),
    }


def write_report(
    path: Path,
    *,
    records: list[dict[str, Any]],
    configs: list[LightningConfig],
    agent_config: AgentConfig,
    token_interval_ms: int,
) -> None:
    summaries = {config.id: summarize_config(records, config) for config in configs}
    repetitions = max((record["repetition"] for record in records), default=0)
    lines = [
        "# Lightning v3.1 Pro Parameter Evaluation",
        "",
        "## Exact fixed configuration",
        "",
        "| Parameter | Value |",
        "|---|---:|",
        f"| Model | `{agent_config.tts_model}` |",
        f"| Voice | `{agent_config.tts_voice}` |",
        f"| Language | `{agent_config.tts_language}` |",
        f"| Sample rate | {agent_config.tts_sample_rate} Hz |",
        "| Encoding | PCM, 16-bit mono |",
        f"| Simulated Electron token interval | {token_interval_ms} ms |",
        f"| Repetitions | {repetitions} per phrase/configuration |",
        "",
        "## Automated result",
        "",
        "| ID | Speed | Buffer flush | Successful | Median TTFB | Median total | Mean audio duration |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for config in configs:
        summary = summaries[config.id]
        lines.append(
            f"| {config.id} | {config.speed} | {config.max_buffer_flush_ms} ms | "
            f"{summary['successes']}/{summary['attempts']} | "
            f"{summary['median_ttfb_ms']} ms | {summary['median_total_ms']} ms | "
            f"{summary['mean_audio_seconds']} s |"
        )

    lines.extend(
        [
            "",
            "TTFB is measured from the first simulated Electron text token until the first audio frame. It therefore includes the controlled token-feed interval and is caller-facing client latency, not server-only inference time.",
            "",
            "## Human listening gate",
            "",
            "Automated timing cannot determine naturalness or whether fast speech makes an identifier harder to understand. Listen to the three speed montages in order; each contains the same six phrases.",
            "",
        ]
    )
    for config in configs[:3]:
        filename = f"audio/lightning-{config.id}-speed-{config.speed}.wav"
        lines.append(f"- `{config.id}` speed {config.speed}: [{filename}]({filename})")

    lines.extend(["", "Score each speed from 1–5 on:", ""])
    for phrase in PHRASES:
        lines.append(f"- **{phrase.id}:** {phrase.listen_for}")

    lines.extend(
        [
            "",
            "## Provisional MVP decision",
            "",
            "Keep **L1, speed 1.0**, unless the listening gate shows that 1.1 is equally intelligible and more natural. Speed changes output duration by design, so shortest audio alone is not a quality win.",
            "",
            "Treat the 200 ms buffer result as a separate latency/streaming decision. Retain it only if it materially improves TTFB without synthesis errors or audible discontinuities; it should not decide the preferred speaking speed.",
            "",
            "## Evidence limits",
            "",
            "- These are clean synthetic phrases, not long conversational responses or noisy phone audio.",
            f"- {repetitions} repetition(s) per phrase support an MVP screening decision, not a provider-level latency claim.",
            "- Network conditions affect TTFB and total duration; relative results from this run are more useful than absolute values.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--token-interval-ms", type=int, default=20)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/evaluations"),
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    api_key = os.getenv("SMALLEST_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SMALLEST_API_KEY is missing from .env")

    agent_config = AgentConfig.from_env()
    configs = [
        LightningConfig("L0", 0.9, 0),
        LightningConfig("L1", 1.0, 0),
        LightningConfig("L2", 1.1, 0),
        LightningConfig("L3", 1.0, 200),
    ]
    records: list[dict[str, Any]] = []
    montage_clips: dict[str, list[bytes]] = {config.id: [] for config in configs}

    async with aiohttp.ClientSession() as http_session:
        for config in configs:
            print(
                f"Running {config.id}: speed={config.speed}, "
                f"max_buffer_flush_ms={config.max_buffer_flush_ms}"
            )
            tts = smallestai.TTS(
                api_key=api_key,
                model=agent_config.tts_model,
                voice_id=agent_config.tts_voice,
                language=agent_config.tts_language,
                speed=config.speed,
                sample_rate=agent_config.tts_sample_rate,
                max_buffer_flush_ms=config.max_buffer_flush_ms,
                word_timestamps=True,
                http_session=http_session,
            )
            tts.prewarm()
            await asyncio.sleep(0.5)
            for repetition in range(1, args.repetitions + 1):
                for phrase in PHRASES:
                    try:
                        audio, measurement = await synthesize_phrase(
                            tts,
                            phrase,
                            token_interval_ms=args.token_interval_ms,
                        )
                        measurement["audio_seconds"] = pcm_duration_seconds(
                            len(audio),
                            agent_config.tts_sample_rate,
                        )
                        if repetition == 1:
                            montage_clips[config.id].append(audio)
                    except Exception as error:  # noqa: BLE001
                        measurement = {
                            "ttfb_ms": None,
                            "total_ms": 0.0,
                            "audio_bytes": 0,
                            "audio_seconds": 0.0,
                            "error": f"{type(error).__name__}: {error}",
                        }
                    records.append(
                        {
                            "config_id": config.id,
                            "speed": config.speed,
                            "max_buffer_flush_ms": config.max_buffer_flush_ms,
                            "phrase_id": phrase.id,
                            "text": phrase.text,
                            "repetition": repetition,
                            **measurement,
                        }
                    )
                    status = "PASS" if measurement["error"] is None else "FAIL"
                    print(f"  {phrase.id} rep {repetition}: {status}")
            await tts.aclose()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = args.output_dir / "audio"
    for config in configs:
        write_montage(
            audio_dir / f"lightning-{config.id}-speed-{config.speed}.wav",
            montage_clips[config.id],
            sample_rate=agent_config.tts_sample_rate,
        )

    jsonl_path = args.output_dir / "lightning-parameter-runs.jsonl"
    report_path = args.output_dir / "lightning-parameter-comparison.md"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        metadata = {
            "record_type": "metadata",
            "created_at": datetime.now(UTC).isoformat(),
            "system_configuration": {
                "model": agent_config.tts_model,
                "voice": agent_config.tts_voice,
                "language": agent_config.tts_language,
                "sample_rate": agent_config.tts_sample_rate,
                "encoding": "pcm_s16le_mono",
                "token_interval_ms": args.token_interval_ms,
                "repetitions": args.repetitions,
            },
            "configs": [asdict(config) for config in configs],
            "phrases": [asdict(phrase) for phrase in PHRASES],
        }
        handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for record in records:
            handle.write(
                json.dumps({"record_type": "result", **record}, ensure_ascii=False)
                + "\n"
            )
    write_report(
        report_path,
        records=records,
        configs=configs,
        agent_config=agent_config,
        token_interval_ms=args.token_interval_ms,
    )
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {len(configs)} listening montages under {audio_dir}")
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
