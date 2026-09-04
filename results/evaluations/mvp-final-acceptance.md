# MVP Final Acceptance — LiveKit Call `console-1d4c1e3f`

## Decision

**MVP accepted.** This call completed an appointment booking with the final
R2/E3/L1 configuration and the deterministic phone validator. It generated a
complete JSONL event stream and readable report with no application errors.

## Exact submitted configuration

| Layer | Setting |
|---|---|
| Pulse | Endpointing on, EOU timeout 100 ms, English, 16 kHz |
| LiveKit | Semantic turn detector, endpointing delay 0.40–3.00 s |
| Electron | Temperature 0.0, maximum 80 tokens |
| Lightning | v3.1 Pro, `meher`, speed 1.0, 24 kHz, buffer 0 ms |
| Phone validation | Exactly 10 India-local digits; spoken English digit normalization |
| Availability | 30-day Asia/Kolkata mock calendar, two alternating daily slots |

## Acceptance evidence

| Check | Result | Evidence |
|---|---|---|
| Relative date resolution | Pass | “Tomorrow” became `2026-09-05` |
| Availability tool | Pass | Returned 10:00 and 14:30 with Dr. Mehta |
| Six-digit rejection | Pass | Reported 6 received and 10 required |
| Nine-digit rejection | Pass | Reported 9 received and 10 required |
| Complete-number validation | Pass | Accepted 10 digits and repeated only the last four (`6789`) |
| Explicit number confirmation | Pass | Booking waited for the caller to confirm the last four |
| Booking result | Pass | Confirmed 14:30 with Dr. Mehta; booking ID `APT-86A75937` |
| Application stability | Pass | Zero captured errors; normal participant-disconnect close marker |

## Observed timings

| Metric | Median | p95 |
|---|---:|---:|
| End-of-utterance delay | 0.849 s | 3.012 s |
| Transcription delay | 0.818 s | 0.897 s |
| Electron TTFT | 0.340 s | 0.608 s |
| Lightning TTFB | 0.292 s | 0.427 s |

These are single-call pipeline observations, not provider-level benchmarks.
The EOU tail occurred on uncertain speech while the median remained below the
1.2-second clean-turn target.

## Interruption observation

At the number confirmation, LiveKit's adaptive interruption detector paused
output at probability 0.662 and then logged `resumed false interrupted speech`
after two seconds. Pulse subsequently captured “Is that correct?”—words Aisha
had just spoken—as user input. The booking recovered when the caller confirmed
explicitly. This pattern is most consistent with local speaker-to-microphone
echo or echo-cancellation behavior, not enough evidence to attribute the
problem to network quality.

The closing “You're welcome” message was also marked interrupted immediately
before the participant disconnected and does not affect task completion.

## Known limitations retained for the report

- Phone validation is intentionally limited to individually spoken English
  digits and 10-digit India-local numbers; international formats are out of scope.
- Fixed audio does not reproduce acoustic echo, background noise, or interactive
  barge-in. Human calls provide only qualitative coverage of those conditions.
- WebRTC connection statistics such as packet loss and jitter are not captured by
  the current application logger, so provider/network attribution is not claimed.
- The mock scheduler is in memory and is not a production calendar integration.

## Evidence files

- Machine event stream: `results/jsonl/session-console-1d4c1e3f.jsonl`
- Human-readable report: `results/reports/session-console-1d4c1e3f.md`
