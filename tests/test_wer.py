from src.wer import normalize_transcript, word_errors


def test_normalization_equates_spoken_and_written_ordinal() -> None:
    assert normalize_transcript("September sixth.") == ["september", "6"]
    assert normalize_transcript("September 6th") == ["september", "6"]


def test_word_errors_counts_name_substitution() -> None:
    errors = word_errors("My name is Test Caller", "My name is Test Coller")

    assert errors.substitutions == 1
    assert errors.deletions == 0
    assert errors.insertions == 0
    assert errors.reference_words == 5


def test_word_errors_counts_split_word_as_substitution_and_insertions() -> None:
    errors = word_errors("book an appointment", "book in a point")

    assert errors.errors == 3
    assert errors.reference_words == 3
