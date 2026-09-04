# Pulse Fixed-Audio Word Error Rate

## Method

- 18 retained replays of three fixed human recordings
- Reference transcripts: `tests/audio/manifest.json`
- Hypotheses: Pulse `is_final=true` segments concatenated in event order
- Normalization: lowercase, punctuation removed, and equivalent single-digit
  forms normalized (for example, `sixth` and `6th` both become `6`)
- Formula: `(substitutions + deletions + insertions) / reference words`

## Result by endpointing configuration

| Config | Runs | Ref. words | Substitutions | Deletions | Insertions | WER |
|---|---:|---:|---:|---:|---:|---:|
| R1 | 6 | 74 | 0 | 0 | 0 | 0.00% |
| R2 | 6 | 74 | 2 | 0 | 0 | 2.70% |
| R3 | 6 | 74 | 3 | 0 | 1 | 5.41% |
| **Overall** | **18** | **222** | **5** | **0** | **1** | **2.70%** |

## Result by fixture

| Fixture | Runs | Ref. words | Errors | WER |
|---|---:|---:|---:|---:|
| `clean-request` | 6 | 54 | 3 | 5.56% |
| `details-request` | 6 | 114 | 3 | 2.63% |
| `hesitation-request` | 6 | 54 | 0 | 0.00% |

## Runs containing errors

- **R2 / `details-request` / repetition 1 — 5.26%:**
  reference: “My name is Test Caller and my number is zero one two three four five six seven eight nine.”
  Pulse: “My name is Test Coller and my number is zero one two three four five six seven eight nine”
- **R2 / `details-request` / repetition 2 — 5.26%:**
  reference: “My name is Test Caller and my number is zero one two three four five six seven eight nine.”
  Pulse: “My name is Test Collur and my number is zero one two three four five six seven eight nine”
- **R3 / `clean-request` / repetition 2 — 33.33%:**
  reference: “I want to book an appointment for September sixth.”
  Pulse: “I want to book in a point for September sixth”
- **R3 / `details-request` / repetition 1 — 5.26%:**
  reference: “My name is Test Caller and my number is zero one two three four five six seven eight nine.”
  Pulse: “My name is Test Coller and my number is zero one two three four five six seven eight nine”

## Interpretation

Pulse's descriptive normalized WER on this tiny fixed set was **2.70%** (6/222 word errors). Most runs were exact after normalization; retained errors were
name variation (`Caller` → `Coller`/`Collur`) and one `appointment` →
`in a point` recognition.

This table is an STT sanity check, not evidence that an endpointing setting
caused better or worse lexical accuracy. R1–R3 changed finalization behavior,
the sample has only two repetitions per fixture/configuration, and the same
Pulse model was used throughout. Endpointing selection therefore remains based
on turn fragmentation and latency.
