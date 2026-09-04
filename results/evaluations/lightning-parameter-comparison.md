# Lightning v3.1 Pro Parameter Evaluation

## Exact fixed configuration

| Parameter | Value |
|---|---:|
| Model | `lightning_v3.1_pro` |
| Voice | `meher` |
| Language | `en` |
| Sample rate | 24000 Hz |
| Encoding | PCM, 16-bit mono |
| Simulated Electron token interval | 20 ms |
| Repetitions | 1 per phrase/configuration |

## Automated result

| ID | Speed | Buffer flush | Successful | Median TTFB | Median total | Mean audio duration |
|---|---:|---:|---:|---:|---:|---:|
| L0 | 0.9 | 0 ms | 6/6 | 605.6 ms | 5323.3 ms | 4.546 s |
| L1 | 1.0 | 0 ms | 6/6 | 630.0 ms | 5293.8 ms | 4.222 s |
| L2 | 1.1 | 0 ms | 6/6 | 631.0 ms | 5302.6 ms | 3.941 s |
| L3 | 1.0 | 200 ms | 6/6 | 600.8 ms | 5294.7 ms | 4.193 s |

TTFB is measured from the first simulated Electron text token until the first audio frame. It therefore includes the controlled token-feed interval and is caller-facing client latency, not server-only inference time.

## Human listening gate

Automated timing cannot determine naturalness or whether fast speech makes an identifier harder to understand. Listen to the three speed montages in order; each contains the same six phrases.

- `L0` speed 0.9: [audio/lightning-L0-speed-0.9.wav](audio/lightning-L0-speed-0.9.wav)
- `L1` speed 1.0: [audio/lightning-L1-speed-1.0.wav](audio/lightning-L1-speed-1.0.wav)
- `L2` speed 1.1: [audio/lightning-L2-speed-1.1.wav](audio/lightning-L2-speed-1.1.wav)

Score each speed from 1–5 on:

- **greeting:** Aisha and Stars Hollow sound natural.
- **date_and_times:** September 6th, 9:30 AM, and 4:00 PM are unambiguous.
- **phone_digits:** The four digits remain distinct rather than running together.
- **booking_id:** Every letter and digit in A P T 7 F 3 K 9 is recoverable.
- **emergency:** The safety message is clear and appropriately paced.
- **tool_filler:** The short filler does not sound rushed or sluggish.

## Final MVP decision

The listener selected **L1, speed 1.0**, as the best-sounding montage. Speed
changes output duration by design, so L2's shorter audio is not treated as a
quality win.

L2 shortened mean phrase audio by about 6.7% versus L1. Retain that speed only
if the spoken date, times, digits and booking ID remain equally intelligible.

Keep the buffer at **0 ms** for the MVP. At speed 1.0, the 200 ms setting changed
median TTFB from 630.0 to 600.8 ms—a roughly 29 ms difference in a one-run
network-sensitive screen. That is not material evidence for changing the
working default.

## Evidence limits

- These are clean synthetic phrases, not long conversational responses or noisy phone audio.
- One repetition per phrase supports an MVP screening decision, not a provider-level latency claim.
- Network conditions affect TTFB and total duration; relative results from this run are more useful than absolute values.
