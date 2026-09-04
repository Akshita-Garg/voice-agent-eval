import shutil
from pathlib import Path

from src.report import render_markdown_report, write_markdown_report


def test_report_contains_configuration_metrics_and_evidence() -> None:
    path = Path(__file__).parent / "fixtures" / "run.jsonl"
    report = render_markdown_report(path)

    assert "## Exact system configuration" in report
    assert "`stt_eou_timeout_ms` | 300" in report
    assert "## Calculated metrics" in report
    assert "LLM | ttft" in report
    assert "## Conversation" in report
    assert "## Tool executions" in report


def test_write_markdown_report_creates_parent_directory() -> None:
    source = Path(__file__).parent / "fixtures" / "run.jsonl"
    test_root = Path(".test-tmp") / "report-test"
    output = test_root / "reports" / "run.md"

    try:
        result = write_markdown_report(source, output)

        assert result == output
        assert output.exists()
        assert "## Exact system configuration" in output.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(test_root, ignore_errors=True)
