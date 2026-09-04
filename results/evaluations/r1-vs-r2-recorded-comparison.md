# Fixed-Audio Comparison — R1 vs R2

## Controlled change

Both configurations used identical audio, Pulse, Silero VAD, LiveKit turn
detector, Electron, Lightning, prompt and tools. The only changed parameter was
LiveKit's maximum endpointing delay.

| Parameter | R1 | R2 |
|---|---:|---:|
| Pulse endpointing | true | true |
| Pulse EOU timeout | 100 ms | 100 ms |
| LiveKit minimum endpointing delay | 0.40 s | 0.40 s |
| LiveKit maximum endpointing delay | **1.50 s** | **3.00 s** |

Each of the three recordings was run twice per configuration: twelve controlled
calls in total.

## Aggregate result

| Measure across six calls/configuration | R1 | R2 | Interpretation |
|---|---:|---:|---|
| Pulse final transcript segments | 15 | 15 | Expected: Pulse configuration was unchanged |
| LiveKit committed user turns | 11 | 9 | R2 reduced internal turn fragmentation by 18% |
| Clean-request mean EOU delay | 0.823 s | 0.844 s | No material clean-turn change in this small sample |
| Correct availability tools on request fixtures | 4/4 | 4/4 | Both preserved tool behavior |
| Application errors | 0 | 0 | Both operationally stable in these calls |

## Fixture-level result

| Fixture | Measured internal pause | R1 turns (rep 1 / 2) | R2 turns (rep 1 / 2) | Result |
|---|---:|---:|---:|---|
| Clean request | None | 1 / 1 | 1 / 1 | Stable in both |
| Hesitation request | 1.204 s | 1 / 2 | 1 / 2 | Both non-deterministic internally |
| Details request | 0.713 s, 1.519 s | 3 / 3 | 2 / 2 | R2 consistently reduced one split |

## User-visible behavior

Committed-message count is diagnostic, not the sole pass criterion. In the R2
hesitation repetition that produced two user messages, both were committed only
after the continuation had completed. Aisha did not speak and no tool executed
during the internal pause. The eventual availability lookup was correct.

Thus R2 improved internal turn grouping without introducing a premature spoken
response in this suite. It did not eliminate fragmentation.

## Latency tradeoff

When the semantic detector remained uncertain, R1 hit its 1.50-second maximum
and R2 hit its 3.00-second maximum. R2 can therefore add up to 1.5 seconds to an
uncertain turn. Clearly complete clean requests remained around 0.8 seconds in
both configurations, but the small sample cannot rule out broader latency cost.

## Accuracy observation

The identical details fixture produced “Test Caller” correctly in R1 but
“Test Coller” and “Test Collur” in the two R2 repetitions. Pulse parameters did
not change, so this is evidence of run-to-run STT variability, not evidence that
the LiveKit maximum delay changed recognition accuracy. The spoken digits were
preserved.

## Provisional decision

Prefer R2 over R1 for the MVP because it reduced details-fragmentation while
maintaining clean-turn latency, correct tool behavior, and no premature spoken
response in the tested fixtures. Describe it as the best of the two tested
LiveKit configurations, not a universal optimum.

The next high-value comparison is timeout-only Pulse endpointing (R3) on the
same audio. Explicit force-finalization should be evaluated at the Pulse layer;
it is not expected to fix LiveKit semantic grouping by itself.

## Evidence limits

- Two repetitions per fixture support a bounded MVP decision, not a reliable
  population failure rate.
- Replay does not test interactive barge-in, acoustic echo, or human-perceived
  conversational timing.
- The first R1 repetition used a shorter post-audio response window, but all
  turn-boundary and tool events used in this comparison occurred before that
  disconnect.
