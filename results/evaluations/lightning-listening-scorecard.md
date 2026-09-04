# Lightning Listening Scorecard

Listen to each montage once with headphones. Score each dimension from 1
(poor) to 5 (excellent). Any ambiguity in the date, time, digits or booking ID
rejects that speed regardless of its total score.

| Dimension | L0: 0.9 | L1: 1.0 | L2: 1.1 | What to notice |
|---|---:|---:|---:|---|
| Overall naturalness |  |  |  | Does Aisha sound conversational rather than slowed down or rushed? |
| Date and times |  |  |  | Can you recover September 6th, 9:30 AM and 4:00 PM exactly? |
| Phone digits |  |  |  | Are 1, 2, 3 and 4 clearly separated? |
| Booking ID |  |  |  | Can you write down A P T 7 F 3 K 9 correctly on first listen? |
| Safety message |  |  |  | Does the emergency instruction sound clear and appropriately serious? |
| Short filler |  |  |  | Does “Let me check…” feel natural at this pace? |

## Decision

- Reject any speed with an intelligibility failure.
- Among the remaining speeds, choose the highest naturalness score.
- If L1 and L2 tie, keep L1 because the 6.7% audio-duration reduction observed
  for L2 is too small to outweigh uncertainty about real telephone conditions.

## Recorded listening outcome — 2026-09-04

- Listener selected **L1, speed 1.0**, as the best-sounding montage.
- Final MVP Lightning configuration: `lightning_v3.1_pro`, voice `meher`,
  English, 24 kHz, speed `1.0`, buffer flush `0 ms`.
