from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    eval_run_label: str = "baseline"
    stt_language: str = "en"
    stt_sample_rate: int = 16000
    stt_diarize: bool = False
    # Smallest's LiveKit integration defaults to 100 ms: Pulse should make
    # transcript segments available promptly while LiveKit owns turn commitment.
    stt_eou_timeout_ms: int = 100
    stt_endpointing: bool = True
    tts_model: str = "lightning_v3.1_pro"
    tts_voice: str = "meher"
    tts_language: str = "en"
    tts_speed: float = 1.0
    tts_sample_rate: int = 24000
    tts_max_buffer_flush_ms: int = 0
    electron_temperature: float = 0.0
    electron_max_tokens: int = 80
    # A little more patience than the initial 150 ms avoids committing common
    # thinking pauses; the semantic turn detector can still respond sooner when sure.
    min_endpointing_delay: float = 0.4
    max_endpointing_delay: float = 3.0
    min_interruption_duration: float = 0.2

    @classmethod
    def from_env(cls) -> AgentConfig:
        return cls(
            eval_run_label=os.getenv("EVAL_RUN_LABEL", cls.eval_run_label),
            stt_language=os.getenv("STT_LANGUAGE", cls.stt_language),
            stt_sample_rate=int(os.getenv("STT_SAMPLE_RATE", cls.stt_sample_rate)),
            stt_diarize=os.getenv("STT_DIARIZE", "false").lower() == "true",
            stt_eou_timeout_ms=int(
                os.getenv("STT_EOU_TIMEOUT_MS", cls.stt_eou_timeout_ms)
            ),
            stt_endpointing=os.getenv("STT_ENDPOINTING", "true").lower() == "true",
            tts_model=os.getenv("TTS_MODEL", cls.tts_model),
            tts_voice=os.getenv("TTS_VOICE", cls.tts_voice),
            tts_language=os.getenv("TTS_LANGUAGE", cls.tts_language),
            tts_speed=float(os.getenv("TTS_SPEED", cls.tts_speed)),
            tts_sample_rate=int(os.getenv("TTS_SAMPLE_RATE", cls.tts_sample_rate)),
            tts_max_buffer_flush_ms=int(
                os.getenv("TTS_MAX_BUFFER_FLUSH_MS", cls.tts_max_buffer_flush_ms)
            ),
            electron_temperature=float(
                os.getenv("ELECTRON_TEMPERATURE", cls.electron_temperature)
            ),
            electron_max_tokens=int(
                os.getenv("ELECTRON_MAX_TOKENS", cls.electron_max_tokens)
            ),
            min_endpointing_delay=float(
                os.getenv("MIN_ENDPOINTING_DELAY", cls.min_endpointing_delay)
            ),
            max_endpointing_delay=float(
                os.getenv("MAX_ENDPOINTING_DELAY", cls.max_endpointing_delay)
            ),
            min_interruption_duration=float(
                os.getenv("MIN_INTERRUPTION_DURATION", cls.min_interruption_duration)
            ),
        )
