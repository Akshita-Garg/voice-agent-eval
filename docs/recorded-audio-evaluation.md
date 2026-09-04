# Recorded-Audio Evaluation

## Fixture layout

- `tests/audio/*.m4a`: immutable original recordings.
- `tests/audio/processed/*.wav`: normalized 16 kHz, mono, PCM16 copies used by tests.
- `tests/audio/manifest.json`: intended transcript and measured silence metadata.

The replay participant joins a fresh LiveKit room, publishes each WAV as a
microphone track in real time, waits for the agent response, and disconnects.
The worker then writes the raw JSONL and readable Markdown report automatically.

## Run the fixed suite

Keep the worker running with the intended `EVAL_RUN_LABEL` and parameters, then run:

```powershell
uv run python scripts/replay_livekit_audio.py `
  tests/audio/processed/clean-request.wav `
  tests/audio/processed/hesitation-request.wav `
  tests/audio/processed/details-request.wav `
  --run-label recorded-r1
```

`--run-label` identifies the room names; the worker's `EVAL_RUN_LABEL` remains
the authoritative configuration label stored inside each report. These two
labels should match.

## Controlled evidence

Hold the WAV files, prompt, availability store, Electron settings, Lightning
settings and VAD fixed. Change only the parameter family named by the run.

Each fixture gets a fresh room and therefore an independent pair:

- `results/jsonl/session-recorded-....jsonl`
- `results/reports/session-recorded-....md`

Recorded replay controls the input audio but does not replace human evaluation
of barge-in, perceived naturalness, echo, or branching conversations.

## Measured fixture properties

The recordings' silence lengths are measured from the normalized waveform with
an amplitude-based detector; they are not assumed from the intended speaking
script. The hesitation fixture's internal pause is about 1.20 seconds, while the
details fixture contains internal pauses of about 0.71 and 1.52 seconds. These
measured values must be used when interpreting endpointing behavior.
