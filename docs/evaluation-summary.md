# Evaluation Summary

## What the evaluation was trying to answer

The agent working once was only the baseline. The evaluation asked four
separate questions:

1. **When should the system decide that the caller has finished a turn?**
2. **How accurately did Pulse transcribe the fixed test speech?**
3. **Once a turn is committed, does Electron behave correctly and consistently?**
4. **Once Electron responds, which Lightning settings produce acceptable speech?**

Testing these layers separately prevents one component's behavior from being
misattributed to another. A fixed-audio suite then tests the real integrated
turn path, while a final human call checks that the selected components still
work together.

## 1. Exploratory browser calls and instrumentation

The first calls established the complete path:

```text
microphone → LiveKit → Pulse → turn decision → Electron → tool → Lightning
```

They also exposed two implementation defects before controlled comparisons:

- Electron resolved “today” against an unrelated date because the prompt had no
  current-date context. The final prompt supplies the current Asia/Kolkata date.
- Early logs could not reconstruct a call independently of the terminal. The
  final logger persists interim/final transcripts, committed messages, tools,
  errors, configuration, component metrics, and an explicit close marker.

These calls were exploratory: because the spoken wording and timing differed,
their latency numbers were not used as controlled parameter comparisons.

## 2. Pulse and LiveKit turn-finalization comparison

### Why fixed audio

Human repetitions inevitably change words, pace, volume, and pause length. The
same three recordings were therefore published into fresh LiveKit rooms as
real-time microphone tracks:

| Fixture | Purpose | Measured internal pauses |
|---|---|---:|
| Clean request | Baseline response to an unambiguous complete request | None |
| Hesitation request | Test whether a mid-sentence thinking pause causes action | 1.204 s |
| Details request | Stress name/number grouping across pauses | 0.713 s and 1.519 s |

Each fixture was replayed twice per configuration. Pulse final segments and
LiveKit committed user turns were counted separately because a Pulse
`is_final=true` segment means stable transcript text—not necessarily that the
whole user turn is over.

### Configurations and results

| Configuration | Pulse endpointing / EOU | LiveKit min/max | Pulse finals | User turns | Clean mean EOU |
|---|---|---:|---:|---:|---:|
| R1 | Native / 100 ms | 0.40 / 1.50 s | 15 | 11 | 0.823 s |
| R2 | Native / 100 ms | 0.40 / 3.00 s | 15 | 9 | 0.844 s |
| R3 | Timeout-only / 800 ms | 0.40 / 3.00 s | 12 | 8 | 2.660 s |

R1's shorter maximum produced the most internal fragmentation. R2 reduced
committed turns from 11 to 9 while leaving clean-request latency approximately
unchanged in this sample. R3 grouped the 1.204-second hesitation consistently,
but clearly complete requests took roughly 3.2 times R2's mean EOU delay.

**Decision: R2.** It was the best tested balance between prompt response and
protection for incomplete speech. It reduces fragmentation; it does not claim
to eliminate it.

Explicit Pulse `finalize` was investigated but not added to the MVP. Pulse can
accept it while native endpointing remains enabled, but the installed official
LiveKit Smallest adapter does not expose a public trigger. Building a custom
adapter was not justified after the native path met the MVP acceptance criteria.

### Pulse word error rate

The intended transcripts already stored in `tests/audio/manifest.json` were used
as references. For each replay, Pulse's non-overlapping final segments were
concatenated in event order. Case and punctuation were removed, and equivalent
single-digit forms such as “sixth” and “6th” were normalized before scoring.

| Configuration | Runs | Reference words | Errors | Normalized WER |
|---|---:|---:|---:|---:|
| R1 | 6 | 74 | 0 | 0.00% |
| R2 | 6 | 74 | 2 | 2.70% |
| R3 | 6 | 74 | 4 | 5.41% |
| **Overall** | **18** | **222** | **6** | **2.70%** |

The retained errors were “Caller” becoming “Coller” or “Collur” and one
“appointment” becoming “in a point.” This is a descriptive sanity check on a
tiny fixed set. It is not evidence that endpointing caused the differences: the
same Pulse model was used throughout, while R1–R3 changed finalization behavior.

## 3. Electron parameter evaluation

### Why text-level tests

STT and turn timing were removed from this stage so every Electron setting saw
the exact same prompt, tool schemas, and conversation history. Nine cases tested:

1. absolute-date availability tool selection;
2. relative-date resolution;
3. refusal to book without explicit confirmation;
4. routing an incomplete number to deterministic validation;
5. stating the exact received and required digit counts;
6. validating a complete number before repeating or booking;
7. confirmed booking with exact arguments after number validation;
8. urgent-medical safety behavior;
9. concise spoken response after an availability tool result.

The harness generates its tool schemas from the same decorated Python methods
used by the live agent. This matters: an initial calibration run omitted the
live `HH:MM 24-hour` parameter description and falsely scored Electron's
`09:30 AM` output as a model failure. The schema was aligned and the invalid
calibration comparison was replaced before retaining results.

### Configurations and results

| ID | Temperature | Maximum tokens | Passes | Median client TTFT |
|---|---:|---:|---:|---:|
| E0 | 0.0 | 120 | 18/18 | 220.6 ms |
| E1 | 0.2 | 120 | 18/18 | 213.4 ms |
| E2 | 0.6 | 120 | 18/18 | 220.7 ms |
| E3 | 0.0 | 80 | 18/18 | 214.1 ms |

The narrow latency spread was treated as noise rather than a meaningful model
ranking. No response was truncated; the largest completion used 64 tokens. All
32 phone-focused attempts passed, including exact “5 received / 10 expected”
recovery and the final validated booking call.

**Decision: E3.** Tool correctness did not distinguish the settings, so the
tie-breakers were lower randomness for an administrative workflow and a smaller
token ceiling that still preserved every tested behavior.

## 4. Lightning v3.1 Pro evaluation

### Why fixed phrases plus human listening

Six phrases covered the content most likely to become unclear in speech: the
assistant and clinic names, a date and two times, isolated phone digits, an
alphanumeric booking ID, an emergency instruction, and a short tool filler.

Automated timing can measure delivery but cannot decide naturalness or whether a
listener can recover an identifier. The test therefore combined 24 syntheses
with a listening comparison.

| ID | Speed | Buffer | Successful | Median TTFB | Mean phrase audio |
|---|---:|---:|---:|---:|---:|
| L0 | 0.9 | 0 ms | 6/6 | 605.6 ms | 4.546 s |
| L1 | 1.0 | 0 ms | 6/6 | 630.0 ms | 4.222 s |
| L2 | 1.1 | 0 ms | 6/6 | 631.0 ms | 3.941 s |
| L3 | 1.0 | 200 ms | 6/6 | 600.8 ms | 4.193 s |

Speed 1.1 shortened audio by about 6.7% versus 1.0. The listener nevertheless
selected speed 1.0 as the best sounding. The 200 ms buffer changed median TTFB
by only about 29 ms in a one-repetition, network-sensitive screen, which was not
enough evidence to change the working default.

**Decision: L1.** Lightning v3.1 Pro, `meher`, speed 1.0, 24 kHz, buffer 0 ms.

## 5. Final integrated acceptance call

The final human LiveKit call (`console-1d4c1e3f`) used the combined R2/E3/L1
settings, 30-day mock calendar, and deterministic phone validator. It resolved
“tomorrow,” returned the correct slots, rejected six- and nine-digit attempts
with the exact counts, accepted ten digits, confirmed the last four, and
completed the selected booking with zero captured application errors.

| Metric | Median | p95 |
|---|---:|---:|
| End-of-utterance delay | 0.849 s | 3.012 s |
| Transcription delay | 0.818 s | 0.897 s |
| Electron TTFT | 0.340 s | 0.608 s |
| Lightning TTFB | 0.292 s | 0.427 s |

This call is evidence that the chosen parts work together. It is not a
controlled comparison with earlier human calls because the speech was not
identical.

The final call also exposed an acoustic interruption: Pulse transcribed “Is that
correct?”—words Aisha had just spoken—as user input, causing the confirmation to
be marked interrupted. This points more strongly to speaker-to-microphone echo
or browser echo cancellation than to network quality, although the application
does not capture WebRTC packet-loss or jitter statistics for attribution.

## Final configuration

- Pulse: native endpointing, 100 ms EOU timeout, English, 16 kHz.
- LiveKit: semantic turn detection, 0.40–3.00-second endpointing delay.
- Electron: temperature 0.0, maximum 80 completion tokens.
- Lightning: v3.1 Pro, `meher`, speed 1.0, 24 kHz, buffer 0 ms.
- Availability: 30 future days, alternating two-slot schedules.
- Phone handling: deterministic spoken-digit normalization and exactly 10
  India-local digits before booking.

## What was deliberately not claimed

- Two repetitions per audio fixture do not establish population failure rates.
- Client-observed latency includes network conditions and is not provider-only
  model latency.
- Fixed audio does not reproduce echo, background noise, or interactive barge-in;
  the later human call supplies only qualitative barge-in evidence.
- Medical routing was covered at the Electron layer, not repeated in the final
  human calls.
- The phone validator covers 10-digit India-local numbers, not international
  formats, and the mock backend is not a production scheduling system.
- The final human call showed one likely echo-induced false interruption; no
  network or echo-cancellation comparison was run.
- Telephony, load testing, a custom force-final adapter, and a large Cartesian
  parameter grid are follow-up work rather than MVP requirements.

## Reviewable evidence

- [`parameter-sweep.md`](parameter-sweep.md): experiment matrix and stop rule.
- [`../results/evaluations/r1-r2-r3-recorded-comparison.md`](../results/evaluations/r1-r2-r3-recorded-comparison.md): turn comparison.
- [`../results/evaluations/pulse-wer-summary.md`](../results/evaluations/pulse-wer-summary.md): normalized Pulse WER.
- [`../results/evaluations/electron-parameter-comparison.md`](../results/evaluations/electron-parameter-comparison.md): Electron comparison.
- [`../results/evaluations/lightning-parameter-comparison.md`](../results/evaluations/lightning-parameter-comparison.md): Lightning comparison.
- [`../results/evaluations/mvp-final-acceptance.md`](../results/evaluations/mvp-final-acceptance.md): integrated acceptance.
