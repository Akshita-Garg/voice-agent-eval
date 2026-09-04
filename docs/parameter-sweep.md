# MVP Parameter Sweep

## Decision rule

Choose the lowest-latency configuration that completes the task without a
premature spoken response, incorrect tool call, lost correction, or failed
barge-in. A faster configuration loses if it crosses any of those guardrails.

This is a sequential sweep, not a Cartesian product. Change one parameter
family, select a winner, and hold it fixed for the next family.

## Fixed controls

| Layer | Fixed setting | Reason |
|---|---|---|
| Transport | LiveKit WebRTC console | Same end-to-end surface for every call |
| Pulse audio | English, linear PCM, 16 kHz | Recommended streaming input; not a tuning variable |
| Pulse formatting | Enabled | Keep transcript presentation constant |
| Silero VAD | Plugin defaults: 50 ms minimum speech, 550 ms minimum silence, 0.5 activation threshold | Avoid confounding VAD and turn-finalization changes |
| LiveKit turn detector | `turn-detector-v1` | Required semantic protection for thinking pauses |
| Electron | Temperature 0.0, maximum 80 tokens | Selected after 72 controlled text-level attempts |
| Lightning | v3.1 Pro, `meher`, speed 1.0, 24 kHz, buffer 0 ms | Selected after automated timing and human listening |
| Prompt, tools, availability data | Byte-identical | Prevent scenario or business-logic drift |

## Stage 1 — transcript and turn finalization (must run)

| ID | Pulse endpointing | Pulse EOU | LiveKit min/max | Status | Hypothesis / decision value |
|---|---:|---:|---:|---|---|
| T0 | On | 300 ms | 0.15 / 1.0 s | Collected: two exploratory calls | Original baseline; repeatedly split incomplete thoughts |
| T1 / R1 | On | 100 ms | 0.40 / 1.5 s | Collected: one exploratory call + two fixed-audio repetitions per fixture | Reduced transcript delay, but fixed audio was inconsistent at a 1.204 s pause and split both 1.519 s details runs into three committed turns; rejected |
| T2 / R2 | On | 100 ms | 0.40 / 3.0 s | Collected: two fixed-audio repetitions per fixture | Reduced total committed turns from 11 to 9 versus R1 and held clean EOU near 0.8 s; still inconsistent on the 1.204 s hesitation and may wait 3 s when uncertain; provisional preference |
| T3 / R3 | Off | 800 ms | 0.40 / 3.0 s | Collected: two fixed-audio repetitions per fixture; rejected | Produced 12 Pulse finals and 8 committed turns versus R2's 15 and 9, but clean EOU rose from 0.844 s to 2.660 s and hesitation EOU was about 3 s |
| T4 | On fallback + explicit `finalize` | 100 ms fallback | 0.40 / winning max | Feasibility experiment | Tests whether an external finalization request adds value when native Pulse finals are already prompt |

### Stage 1 acceptance criteria

- No agent speech during the scripted one- and two-second thinking pauses.
- No incorrect or premature tool call.
- A barge-in cancels obsolete speech and the correction reaches the next tool call.
- Spoken number remains recoverable as one logical field even if Pulse emits
  multiple final transcript segments.
- Median end-of-turn delay target: at most 1.2 seconds for clearly complete turns.
- Report transcript segments and committed user turns separately.

### Force-finalization scope

Pulse accepts `{"type":"finalize"}` while native endpointing remains enabled;
the first trigger wins. The installed LiveKit Smallest plugin acknowledges this
wire command but does not expose a public method or external-VAD hook for it.
Therefore T4 is an adapter feasibility test, not a requirement to replace the
official integration. Retain it only if it improves measured behavior without
duplicating Pulse's native endpointing.

## Stage 2 — Electron behavior (must run, cheap scripted calls)

Use the winning T configuration. Run the same text-level cases without changing
the prompt or tool backend.

| ID | Temperature | Max tokens | Purpose |
|---|---:|---:|---|
| E0 | 0.0 | 120 | Deterministic tool selection and arguments |
| E1 | 0.2 | 120 | Current baseline; allows small phrasing variation |
| E2 | 0.6 | 120 | Stress test for behavioral drift; not presumed to be a production candidate |
| E3 | Winning temperature | 80 | Test whether a lower ceiling prevents verbosity without truncating confirmations |

Score exact tool name, required arguments, date resolution, confirmation gate,
medical-advice refusal, unnecessary questions, TTFT, and truncation. Tool
correctness outranks small TTFT differences.

### Stage 2 result

Each configuration received the same nine cases twice. E0, E1, E2 and E3 all
passed 18/18 attempts: exact availability and booking tools, absolute and
relative dates, the confirmation gate, incomplete and complete phone handling,
urgent-medical routing and concise post-tool speech. Median client-observed TTFT
ranged from 213.4 to 220.7 ms, which is too narrow and noisy to distinguish
these settings. No response hit a length stop; the largest completion used 64
tokens.

Select **E3: temperature 0.0, maximum 80 tokens**. The lower temperature is the
appropriate tie-breaker for a constrained administrative workflow, and the
80-token cap reduced headroom without truncating any fixed case. This is a
bounded task-specific selection, not evidence that temperature 0.0 is generally
better for Electron.

## Stage 3 — Lightning delivery (must run, no full conversations required)

Use a fixed set of six agent sentences containing dates, times, names, digits,
and the booking identifier.

| ID | Speed | Buffer flush | Purpose |
|---|---:|---:|---|
| L0 | 0.9 | 0 ms | Naturalness / slower control |
| L1 | 1.0 | 0 ms | Current baseline |
| L2 | 1.1 | 0 ms | Shorter calls versus intelligibility |
| L3 | Winning speed | 200 ms | Test smoothness versus first-audio latency |

Measure TTFB and audio duration. Human-score intelligibility and naturalness
from 1–5. Reject a setting if dates, times, or booking IDs become harder to
understand, even if it is faster.

### Stage 3 screening result

One controlled synthesis per phrase/configuration produced 24 successful audio
results and four listening montages with no API errors. Mean phrase duration was
4.546 s at speed 0.9, 4.222 s at
1.0 and 3.941 s at 1.1; speed 1.1 was about 6.7% shorter than 1.0. Median
client-observed TTFB was 605.6, 630.0 and 631.0 ms respectively, too close and
network-sensitive to rank the speeds.

At speed 1.0, a 200 ms forced-buffer setting measured 600.8 ms median TTFB
versus 630.0 ms with the 0 ms default. Keep **buffer 0 ms**: a roughly 29 ms
one-run difference is not material evidence for adding forced partial flushes.
The listening gate selected **speed 1.0** as the best-sounding montage. Final
Lightning MVP settings are therefore speed 1.0 and buffer 0 ms.

## Conditional tests (only if a failure is observed)

| Family | Current value | Candidate | Trigger for testing |
|---|---:|---:|---|
| Silero minimum silence | 0.55 s | 0.35 / 0.75 s | Missed or over-eager speech-end detection |
| Silero activation threshold | 0.5 | 0.4 / 0.6 | Quiet speech missed or background noise treated as speech |
| LiveKit minimum interruption duration | 0.2 s | 0.1 / 0.4 s | Barge-in missed or backchannels falsely interrupt |

Do not sweep these merely to increase the number of experiments.

## Repetition and evidence standard

- The fixed recordings were replayed twice per fixture for R1, R2 and R3.
- T0 and T1 are exploratory because their spoken inputs were not identical.
- Label a one-call result as an observation, not a general performance claim.
- Preserve the JSONL run, configuration label, automated summary, and a short
  human annotation for every retained result.

## MVP stop condition

Freeze the agent when:

1. One turn configuration passes the fixed script without a premature spoken
   response or incorrect tool call.
2. Electron passes every deterministic tool/guardrail case at the selected
   temperature and token ceiling.
3. One Lightning setting is intelligible and has acceptable TTFB.
4. The final clean end-to-end booking produces a labelled JSONL file with no
   application errors.

Current Stage 1 selection: **R2** (`endpointing=true`, Pulse EOU 100 ms,
LiveKit minimum/maximum 0.40/3.00 s). R3 improved grouping slightly but imposed
an unacceptable clean-turn latency cost for the MVP.

Current Stage 2 selection: **E3** (Electron temperature 0.0, maximum 80
tokens). Current Stage 3 selection: **L1** (Lightning v3.1 Pro, `meher`, speed
1.0, 24 kHz, buffer 0 ms).

Telephone integration, a large parameter grid, statistical significance, and
production-scale load testing belong in next steps, not the MVP.

## MVP acceptance result — 2026-09-04

| Stop condition | Status | Evidence |
|---|---|---|
| Selected turn configuration | Passed | R2 fixed-audio suite; no premature tool or spoken response in retained calls |
| Electron tool and guardrail cases | Passed | E3 and every comparison configuration passed 18/18 attempts |
| Lightning intelligibility and timing | Passed | All 24 syntheses succeeded; listener selected L1 speed 1.0 |
| Final labelled booking | Passed | `console-1d4c1e3f`, final R2/E3/L1 plus phone validator, confirmed booking, zero application errors |

The MVP is frozen. Deterministic 10-digit India-local phone validation was added
after a human edge-case call and passed backend tests plus 32/32 focused Electron
attempts. Retain stale-tool cancellation, broader phone formats, explicit Pulse
force-finalization and telephony as clearly labelled follow-up work rather than
extending the parameter sweep.
