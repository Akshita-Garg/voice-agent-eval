from pathlib import Path

import pytest

from scripts.replay_livekit_audio import SAMPLE_RATE, validate_wav


@pytest.mark.parametrize(
    "name",
    ["clean-request.wav", "hesitation-request.wav", "details-request.wav"],
)
def test_processed_audio_is_valid_for_pulse(name: str) -> None:
    path = Path("tests/audio/processed") / name
    if not path.exists():
        pytest.skip("private human-voice fixture is not included in the repository")
    info = validate_wav(path)

    assert info.frames > 0
    assert info.duration_seconds > 1
    assert SAMPLE_RATE == 16_000
