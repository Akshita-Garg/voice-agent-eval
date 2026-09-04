from scripts.evaluate_lightning import pcm_duration_seconds


def test_pcm_duration_for_one_second_of_mono_24khz_audio() -> None:
    assert pcm_duration_seconds(48_000, 24_000) == 1.0
