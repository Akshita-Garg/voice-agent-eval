"""Small, dependency-free word-error-rate helpers for the fixed STT fixtures."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_NUMBER_WORDS = {
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "first": "1",
    "second": "2",
    "third": "3",
    "fourth": "4",
    "fifth": "5",
    "sixth": "6",
    "seventh": "7",
    "eighth": "8",
    "ninth": "9",
}


@dataclass(frozen=True)
class WordErrors:
    substitutions: int
    deletions: int
    insertions: int
    reference_words: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def wer(self) -> float:
        return self.errors / self.reference_words if self.reference_words else 0.0


def normalize_transcript(text: str) -> list[str]:
    """Normalize case, punctuation and equivalent spoken/written single digits."""
    normalized: list[str] = []
    for token in _TOKEN_PATTERN.findall(text.lower()):
        ordinal = re.fullmatch(r"(\d+)(?:st|nd|rd|th)", token)
        if ordinal:
            normalized.append(ordinal.group(1))
        else:
            normalized.append(_NUMBER_WORDS.get(token, token))
    return normalized


def word_errors(reference: str, hypothesis: str) -> WordErrors:
    """Calculate minimum-edit substitutions, deletions and insertions."""
    reference_tokens = normalize_transcript(reference)
    hypothesis_tokens = normalize_transcript(hypothesis)
    # Each cell is (total errors, substitutions, deletions, insertions).
    matrix: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(len(hypothesis_tokens) + 1)]
        for _ in range(len(reference_tokens) + 1)
    ]
    for ref_index in range(1, len(reference_tokens) + 1):
        matrix[ref_index][0] = (ref_index, 0, ref_index, 0)
    for hyp_index in range(1, len(hypothesis_tokens) + 1):
        matrix[0][hyp_index] = (hyp_index, 0, 0, hyp_index)

    for ref_index, reference_token in enumerate(reference_tokens, start=1):
        for hyp_index, hypothesis_token in enumerate(hypothesis_tokens, start=1):
            diagonal = matrix[ref_index - 1][hyp_index - 1]
            if reference_token == hypothesis_token:
                matrix[ref_index][hyp_index] = diagonal
                continue
            deletion = matrix[ref_index - 1][hyp_index]
            insertion = matrix[ref_index][hyp_index - 1]
            candidates = [
                (diagonal[0] + 1, diagonal[1] + 1, diagonal[2], diagonal[3]),
                (deletion[0] + 1, deletion[1], deletion[2] + 1, deletion[3]),
                (insertion[0] + 1, insertion[1], insertion[2], insertion[3] + 1),
            ]
            matrix[ref_index][hyp_index] = min(
                candidates,
                key=lambda item: (item[0], item[2] + item[3], -item[1]),
            )

    _, substitutions, deletions, insertions = matrix[-1][-1]
    return WordErrors(
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
        reference_words=len(reference_tokens),
    )
