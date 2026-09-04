# Evaluation Method

This document records the experiment design. The
[final report](final-report.md) is the authoritative narrative and contains the
decisions and interpreted results. Run-level evidence remains under
[`results/evaluations/`](../results/evaluations/).

## Objective and decision rule

Select the lowest-latency configuration that completes the appointment task
without premature speech, an incorrect tool call, a lost correction, failed
barge-in, or unclear synthesized speech. A faster setting loses if it crosses
one of those guardrails.

The sweep is sequential rather than Cartesian: change one component's parameter
family, choose a setting, hold it fixed, and then evaluate the next component.

## Fixed controls

| Layer | Fixed control |
|---|---|
| Transport and orchestration | LiveKit Agents over WebRTC |
| Pulse input | English, mono linear PCM, 16 kHz |
| VAD | Silero plugin defaults |
| Turn model | LiveKit `turn-detector-v1` |
| TTS model and voice | Lightning v3.1 Pro, `meher`, 24 kHz |
| Application | Identical prompt, tool schemas, mock calendar, and booking logic within each comparison |

Every retained run records its exact configuration. Pulse transcript finals and
LiveKit committed user turns are counted separately because a stable transcript
segment is not, by itself, permission for the agent to respond.

## Stage 1: turn finalization

Three normalized 16 kHz WAV fixtures are published in real time into fresh
LiveKit rooms. Each fixture is replayed twice per configuration.

| Fixture | Purpose | Measured internal pauses |
|---|---|---:|
| Clean request | Clearly complete request and latency baseline | None |
| Hesitation request | Mid-sentence thinking pause | 1.204 s |
| Details request | Name and number grouping | 0.713 s and 1.519 s |

| ID | Pulse endpointing / EOU | LiveKit minimum / maximum |
|---|---|---:|
| R0 | Native / 100 ms | 0.40 / 1.50 s |
| R1 | Native / 100 ms | 0.40 / 3.00 s |
| R2 | Timeout-only / 800 ms | 0.40 / 3.00 s |

Primary measures are committed-turn count, premature response or tool use, clean
end-of-utterance delay, and behavior around the measured pauses. The same
hypotheses are also scored for normalized WER using the reference transcripts in
`tests/audio/manifest.json`; WER is descriptive and is not used to rank the
endpointing configurations.

Pulse can accept an explicit `finalize` message while native endpointing stays
enabled, with the first trigger winning. That hybrid was treated as an adapter
feasibility follow-up because the installed official LiveKit Smallest adapter
does not expose a public trigger.

Detailed outputs:

- [Turn-finalization comparison](../results/evaluations/r0-r1-r2-recorded-comparison.md)
- [Pulse WER](../results/evaluations/pulse-wer-summary.md)

## Stage 2: Electron

Audio, STT, VAD, and TTS are removed so every Electron configuration receives
the same prompt, live-derived tool schemas, and nine text-level cases twice.
Cases cover date resolution, availability, confirmation gating, incomplete and
complete phone validation, booking arguments, urgent-medical routing, and
concise post-tool speech.

| ID | Temperature | Maximum completion tokens |
|---|---:|---:|
| E0 | 0.0 | 120 |
| E1 | 0.2 | 120 |
| E2 | 0.6 | 120 |
| E3 | 0.0 | 80 |

Exact tool name and arguments, guardrail behavior, truncation, and TTFT are
recorded. Correct behavior outranks small client-observed latency differences.

Detailed output: [Electron comparison](../results/evaluations/electron-parameter-comparison.md).

## Stage 3: Lightning

Six fixed phrases cover names, dates, times, phone digits, a booking ID, an
emergency instruction, and a short tool filler.

| ID | Speed | Forced buffer flush |
|---|---:|---:|
| L0 | 0.9 | 0 ms |
| L1 | 1.0 | 0 ms |
| L2 | 1.1 | 0 ms |
| L3 | 1.0 | 200 ms |

The harness records success, client-observed TTFB, and audio duration. Human
listening is the final gate for naturalness and identifier intelligibility.

Detailed output: [Lightning comparison](../results/evaluations/lightning-parameter-comparison.md).

## Integrated acceptance and evidence standard

After selecting one setting from each stage, a human LiveKit call must complete
the workflow with the combined configuration. The
[standard call script](standard-call-script.md) covers pauses, interruption,
correction, confirmation, phone capture, booking, and medical-advice refusal.

A retained conclusion must include the configuration label, JSONL evidence,
automated summary, and any human annotation. One-call observations are labelled
as observations rather than general performance claims. Fixed audio controls
input wording and timing but does not substitute for live tests of barge-in,
echo, branching dialogue, or perceived naturalness.

Final integrated evidence: [MVP acceptance](../results/evaluations/mvp-final-acceptance.md).
