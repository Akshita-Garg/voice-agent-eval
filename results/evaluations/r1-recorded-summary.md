# R1 Recorded-Audio Evaluation

## Configuration

| Parameter | Value |
|---|---:|
| Pulse model | `pulse` |
| Pulse endpointing | `true` |
| Pulse EOU timeout | 100 ms |
| LiveKit minimum endpointing delay | 0.40 s |
| LiveKit maximum endpointing delay | 1.50 s |
| LiveKit turn detector | `turn-detector-v1` |
| Silero VAD | Defaults; 0.55 s minimum silence |
| Electron | temperature 0.2, maximum 120 tokens |
| Lightning | v3.1 Pro, `meher`, speed 1.0, 24 kHz |

All three normalized recordings were streamed through a LiveKit microphone
track in real time. Each fixture was run twice. The first repetition used an
eight-second response window and is retained as turn-boundary evidence only;
the second used a fifteen-second response window and retained complete agent
responses.

## Fixed fixture results

| Fixture | Measured internal pause | Repetition | Pulse finals | LiveKit committed user turns | EOU delay(s) | Tool behavior | App errors |
|---|---:|---:|---:|---:|---|---|---:|
| Clean request | None | 1 | 1 | 1 | 0.850 | Correct availability lookup | 0 |
| Clean request | None | 2 | 1 | 1 | 0.796 | Correct availability lookup | 0 |
| Hesitation request | 1.204 s | 1 | 2 | 1 | 1.501 | Correct availability lookup | 0 |
| Hesitation request | 1.204 s | 2 | 2 | 2 | 0.578, 0.000 | Correct availability lookup after continuation | 0 |
| Details request | 0.713 s, 1.519 s | 1 | 5 | 3 | 1.501, 0.578, 0.000 | No tool expected | 0 |
| Details request | 0.713 s, 1.519 s | 2 | 4 | 3 | 1.501, 0.578, 0.000 | No tool expected | 0 |

## Interpretation

R1 passes clean speech but fails the strict single-logical-turn guardrail. It was
non-deterministic on the identical 1.204-second hesitation and consistently
split the details recording into three committed user turns around a measured
1.519-second pause. The 1.50-second maximum is therefore acting as a brittle
safety ceiling near ordinary thinking-pause duration.

Pulse final segments and LiveKit user turns must remain separate in the
interpretation. Multiple Pulse finals are acceptable, but multiple committed
turns can trigger speculative Electron work and can cause premature speech or
tool use. In the retained recordings Aisha did not produce an incorrect tool
call, and no application error occurred. Electron recovered correctly in these
narrow fixtures; that resilience does not make the internal boundary reliable.

## Decision

Reject R1 as the production candidate. Test R2 with the same audio and two
repetitions, changing only LiveKit's maximum endpointing delay from 1.50 to
3.00 seconds. The hypothesis is that the semantic detector will continue to
commit clearly complete turns promptly while preserving these incomplete
pauses.

## Evidence limits

- Six calls are enough to reject this configuration on the tested fixtures,
  not to estimate population-level failure rates.
- The amplitude-based pause measurements use a -35 dB threshold and 0.3-second
  minimum; they are waveform measurements, not exact VAD state transitions.
- Recorded replay does not evaluate interactive barge-in, echo, or subjective
  conversational naturalness.
