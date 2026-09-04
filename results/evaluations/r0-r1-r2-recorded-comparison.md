# Fixed-Audio Comparison — R0, R1 and R2

## What changed

The same three recordings were replayed twice per configuration through the
complete LiveKit agent. Pulse, Silero VAD, Electron, Lightning, the prompt and
the tools stayed fixed except for the settings shown below.

| Parameter | R0 | R1 | R2 |
|---|---:|---:|---:|
| Pulse endpointing | true | true | **false** |
| Pulse EOU timeout | 100 ms | 100 ms | **800 ms** |
| LiveKit minimum endpointing delay | 0.40 s | 0.40 s | 0.40 s |
| LiveKit maximum endpointing delay | 1.50 s | 3.00 s | 3.00 s |

R0 versus R1 isolates LiveKit's maximum delay. R1 versus R2 changes the Pulse
finalization mode and timeout together, so it tests a documented timeout-only
strategy rather than estimating the effect of either setting independently.

## Aggregate result

| Measure across six calls/configuration | R0 | R1 | R2 |
|---|---:|---:|---:|
| Pulse final transcript segments | 15 | 15 | **12** |
| LiveKit committed user turns | 11 | 9 | **8** |
| Correct availability tools | 4/4 | 4/4 | 4/4 |
| Application errors | 0 | 0 | 0 |

R2 produced the fewest transcript segments and committed turns. That grouping
gain did not translate into the best user-facing configuration because clearly
complete requests were finalized much more slowly.

## Latency on the clean request

| Metric, mean of two repetitions | R0 | R1 | R2 |
|---|---:|---:|---:|
| LiveKit end-of-utterance delay | 0.823 s | 0.844 s | **2.660 s** |
| Transcription delay within EOU | — | 0.824 s | **2.377 s** |

The R2 clean-request EOU delay was about 3.2 times R1's in this small sample.
Its two clean turns measured 3.005 and 2.315 seconds. The 800 ms setting should
therefore not be interpreted as an observed 800 ms end-to-end finalization
promise: the measured pipeline includes Pulse emission and LiveKit turn
handling, and this experiment does not isolate which internal wait accounts for
the difference.

## Paused-speech behavior

| Fixture | Measured internal pause | R0 turns | R1 turns | R2 turns | R2 timing |
|---|---:|---:|---:|---:|---|
| Hesitation | 1.204 s | 1 / 2 | 1 / 2 | **1 / 1** | EOU 3.009 / 3.003 s |
| Details | 0.713 s, 1.519 s | 3 / 3 | 2 / 2 | **2 / 2** | Each run still split once |

R2 consistently merged the hesitation fixture, but the user then waited about
three seconds for turn commitment. It did not merge the longer details fixture
into one turn. No premature availability lookup or spoken response occurred in
the retained calls.

## Accuracy observation

One R2 clean repetition transcribed “appointment” as “in a point.” The other
clean repetition was correct. The details name varied between “Test Caller” and
“Test Coller.” With two repetitions and a configuration change that is not
intended to improve lexical recognition, these are observations of run-to-run
STT variability, not evidence that timeout-only endpointing reduced accuracy.

## MVP decision

Select **R1**: Pulse native endpointing on, Pulse EOU timeout 100 ms, and
LiveKit semantic endpointing at 0.40–3.00 seconds.

R1 is not perfect—it retained internal fragmentation and can still wait the
full three seconds when the semantic detector is uncertain. It is the best
tested balance because it reduced R0's fragmentation while keeping clean-turn
EOU around 0.8 seconds. Reject R2 for the MVP: one fewer committed turn across
six calls is not worth roughly 1.8 seconds of additional clean-turn latency.

## Evidence limits and next test

- Two repetitions per fixture support a bounded MVP choice, not a population
  estimate or a claim of universal optimality.
- Fixed replay controls the words, timing and acoustics, but does not test
  interactive barge-in, echo or the feel of a human conversation.
- An explicit Pulse `finalize` command remains a useful protocol-level
  feasibility test. The installed official LiveKit Smallest adapter does not
  expose that trigger publicly, so it should not delay freezing the MVP.
