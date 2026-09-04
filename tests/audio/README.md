# Private fixed-audio fixtures

The original M4A recordings and normalized WAV copies are intentionally ignored
by Git because human voice recordings can be identifying. The public manifest
retains the intended transcripts, format, durations, and measured pause lengths
used for the reported evaluation.

To reproduce the suite, create these local files:

```text
tests/audio/clean-request.m4a
tests/audio/hesitation-request.m4a
tests/audio/details-request.m4a
tests/audio/processed/clean-request.wav
tests/audio/processed/hesitation-request.wav
tests/audio/processed/details-request.wav
```

Normalize each source with FFmpeg:

```powershell
ffmpeg -i tests/audio/clean-request.m4a -ar 16000 -ac 1 -c:a pcm_s16le tests/audio/processed/clean-request.wav
```

Repeat for the other two filenames. The replay script validates that each WAV
is mono, 16 kHz, and 16-bit PCM before publishing it to LiveKit.
