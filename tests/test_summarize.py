from pathlib import Path

from src.summarize import summarize_events


def test_summarize_events() -> None:
    path = Path(__file__).parent / "fixtures" / "run.jsonl"
    summary = summarize_events(path)

    assert summary["configuration"]["stt_eou_timeout_ms"] == 300
    assert summary["counters"]["final_transcripts"] == 1
    assert summary["counters"]["tool_batches"] == 1
    assert summary["metrics_seconds"]["llm_metrics"]["ttft"]["p50"] == 0.2
