# MVP Final Acceptance — LiveKit Call `console-ad8cd19a`

## Decision

**MVP accepted.** This call completed an appointment booking with the final
combined R2/E3/L1 configuration, generated a complete JSONL event stream and
readable report, and recorded no application errors.

## Exact submitted configuration

| Layer | Setting |
|---|---|
| Pulse | Endpointing on, EOU timeout 100 ms, English, 16 kHz |
| LiveKit | Semantic turn detector, endpointing delay 0.40–3.00 s |
| Electron | Temperature 0.0, maximum 80 tokens |
| Lightning | v3.1 Pro, `meher`, speed 1.0, 24 kHz, buffer 0 ms |
| Availability | 30-day Asia/Kolkata mock calendar, two alternating daily slots |

## Acceptance evidence

| Check | Result | Evidence |
|---|---|---|
| Relative date resolution | Pass | “Tomorrow” became `2026-09-05` |
| Availability tool | Pass | Returned 10:00 and 14:30 with Dr. Mehta |
| Thinking/continuation handling | Pass with internal fragmentation | “Are there any slots a little later … in the day” became two user messages, but Aisha did not respond or act between them |
| Explicit slot selection | Pass | Caller said “book that one” after the 14:30 offer |
| Booking arguments | Pass | Name `Test`, date `2026-09-05`, time `14:30`; phone was redacted in stored arguments |
| Booking result | Pass | Backend returned `status=confirmed` and booking ID `APT-72B4D04A` |
| Application stability | Pass | Zero captured errors; normal participant-disconnect close marker |

## Observed timings

| Metric | Median | p95 |
|---|---:|---:|
| End-of-utterance delay | 0.936 s | 3.002 s |
| Transcription delay | 0.913 s | 1.184 s |
| Electron TTFT | 0.226 s | 0.740 s |
| Lightning TTFB | 0.285 s | 1.658 s |

The high EOU tail occurred on uncertain speech, while the median remained under
the 1.2-second clean-turn target. This one human call is acceptance evidence,
not a provider-level latency benchmark.

## Known limitations retained for the report

- The final call did not deliberately test barge-in or repeat the medical-safety
  question. Medical routing passed 8/8 controlled Electron attempts; barge-in
  remains a live-call follow-up rather than a reason to reopen the MVP sweep.
- The captured phone utterance contained nine digits and the mock backend
  accepted it. Production work should validate and reconfirm phone-number
  length; this assignment MVP intentionally keeps the booking backend narrow.
- Pulse emitted 12 final transcript segments and LiveKit committed seven user
  messages. The agent behaved correctly despite this internal fragmentation;
  the configuration reduces fragmentation but does not eliminate it.

## Post-acceptance hardening

A later human call (`console-b07d7f08`) successfully exercised repeated barge-in
and surfaced unreliable free-form phone reconstruction. The agent now calls a
deterministic validator that normalizes individually spoken English digits,
reports the exact received-versus-required count, and prevents an invalid number
from consuming a slot. The updated three-tool Electron contract passed 72/72
controlled attempts, including 32/32 phone-focused attempts, and the backend
path is unit-tested. The scope is explicitly 10-digit India-local numbers.

That later call also showed that interrupting speech does not automatically
cancel an already-running tool result; one obsolete availability response still
reached speech. Stale-tool cancellation remains a production follow-up.

## Evidence files

- Machine event stream: `results/jsonl/session-console-ad8cd19a.jsonl`
- Human-readable report: `results/reports/session-console-ad8cd19a.md`
