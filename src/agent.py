from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    inference,
)
from livekit.plugins import openai, silero, smallestai

from .appointment_store import (
    AVAILABILITY_TIMEZONE,
    PHONE_EXPECTED_DIGITS,
    STORE,
    validate_india_phone_number,
)
from .config import AgentConfig
from .metrics import JsonlMetricSink, MetricEvent
from .report import write_markdown_report

load_dotenv()
logger = logging.getLogger("voice-agent-eval")


INSTRUCTIONS = """
You are Aisha, the appointment coordinator for Stars Hollow.

Your job is administrative only: help callers check appointment availability
and book a general consultation. Never diagnose, recommend treatment, interpret
symptoms, or provide medical advice. For urgent symptoms, tell the caller to
contact local emergency services.

Voice behavior:
- Keep each response to one or two short spoken sentences.
- Ask one question at a time.
- Do not read JSON, internal tool names, or implementation details aloud.
- Confirm the date and time before booking.
- Collect the caller's name and phone number only when they choose a slot.
- This demo accepts 10-digit India-local phone numbers.
- Whenever the caller provides a phone number, call validate_phone_number before
  repeating digits or booking.
- If validation fails, state the received and expected digit counts returned by
  the tool and ask for the complete number.
- If validation succeeds, repeat only the last four digits and ask the caller to
  confirm them before booking.
- If a tool is taking time, use a short natural acknowledgement.

Tool rules:
- Use check_availability whenever the caller asks which slots are open.
- Use book_appointment only after the caller explicitly confirms a listed slot
  and a validated phone number.
- Never invent availability or a booking confirmation.
""".strip()


def build_agent_instructions(current_date: date | None = None) -> str:
    """Build the exact system prompt used by live calls and text evaluations."""
    if current_date is None:
        india_time = timezone(timedelta(hours=5, minutes=30))
        current_date = datetime.now(india_time).date()
    return (
        f"{INSTRUCTIONS}\n\n"
        f"Date context:\n- Today's date is {current_date.isoformat()} in Asia/Kolkata.\n"
        "- Resolve relative dates such as today and tomorrow against this date.\n"
        "- Pass resolved dates to tools in YYYY-MM-DD format."
    )


class ClinicAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=build_agent_instructions())

    async def on_enter(self) -> None:
        self.session.generate_reply(
            instructions=(
                "Greet the caller as Aisha from Stars Hollow and ask how you can "
                "help with an appointment. Keep it to one sentence."
            )
        )

    @function_tool
    async def check_availability(
        self,
        ctx: RunContext,
        requested_date: str | None = None,
    ) -> dict[str, Any]:
        """Check open general-consultation slots.

        Args:
            requested_date: Preferred date in YYYY-MM-DD format, if the caller gave one.
        """
        async with ctx.with_filler("Let me check the available times.", delay=0.15):
            await asyncio.sleep(0.35)
            slots = STORE.available_slots(requested_date)
        return {"status": "ok", "slots": slots}

    @function_tool
    async def validate_phone_number(
        self,
        phone_number: str,
    ) -> dict[str, Any]:
        """Count and validate a caller's 10-digit India-local phone number.

        Always call this after the caller supplies a phone number and before
        repeating digits or booking.

        Args:
            phone_number: Caller-provided callback number, as heard by Pulse.
        """
        return validate_india_phone_number(phone_number)

    @function_tool
    async def book_appointment(
        self,
        ctx: RunContext,
        patient_name: str,
        phone_number: str,
        requested_date: str,
        requested_time: str,
    ) -> dict[str, Any]:
        """Book a slot after the caller explicitly confirms it.

        Args:
            patient_name: Caller-provided patient name.
            phone_number: Caller-provided callback number.
            requested_date: Confirmed date in YYYY-MM-DD format.
            requested_time: Confirmed time in HH:MM 24-hour format.
        """
        async with ctx.with_filler("I’ll reserve that now.", delay=0.15):
            await asyncio.sleep(0.35)
            result = STORE.book(
                patient_name=patient_name,
                phone_number=phone_number,
                requested_date=requested_date,
                requested_time=requested_time,
            )
        return result


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


def _record_event(sink: JsonlMetricSink, name: str, attributes: dict[str, Any]) -> None:
    sink.write(
        MetricEvent(
            event=name,
            monotonic_ms=round(time.monotonic() * 1000, 3),
            attributes=attributes,
        )
    )


def build_session(*, config: AgentConfig, smallest_key: str, vad: Any) -> AgentSession:
    stt = smallestai.STT(
        api_key=smallest_key,
        model="pulse",
        language=config.stt_language,
        sample_rate=config.stt_sample_rate,
        diarize=config.stt_diarize,
        eou_timeout_ms=config.stt_eou_timeout_ms,
        endpointing=config.stt_endpointing,
        word_timestamps=True,
        format=True,
    )
    llm = openai.LLM(
        api_key=smallest_key,
        base_url="https://api.smallest.ai/waves/v1",
        model="electron",
        temperature=config.electron_temperature,
        max_completion_tokens=config.electron_max_tokens,
        parallel_tool_calls=False,
    )
    tts = smallestai.TTS(
        api_key=smallest_key,
        model=config.tts_model,
        voice_id=config.tts_voice,
        language=config.tts_language,
        speed=config.tts_speed,
        sample_rate=config.tts_sample_rate,
        max_buffer_flush_ms=config.tts_max_buffer_flush_ms,
        word_timestamps=True,
    )

    return AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
        turn_detection=inference.TurnDetector(),
        allow_interruptions=True,
        min_interruption_duration=config.min_interruption_duration,
        min_endpointing_delay=config.min_endpointing_delay,
        max_endpointing_delay=config.max_endpointing_delay,
        transcription_timeout=2.0,
        max_tool_steps=2,
        # Preserve Electron's original punctuation and spacing in conversation logs.
        # Smallest's word-aligned TTS transcript currently concatenates tokens.
        use_tts_aligned_transcript=False,
    )


async def entrypoint(ctx: JobContext) -> None:
    config = AgentConfig.from_env()
    smallest_key = os.environ["SMALLEST_API_KEY"]
    safe_room_name = "".join(c for c in ctx.room.name if c.isalnum() or c in "-_")
    result_root = Path("results")
    jsonl_path = result_root / "jsonl" / f"session-{safe_room_name}.jsonl"
    report_path = result_root / "reports" / f"session-{safe_room_name}.md"
    sink = JsonlMetricSink(jsonl_path)
    session = build_session(
        config=config,
        smallest_key=smallest_key,
        vad=ctx.proc.userdata["vad"],
    )
    if session.tts is not None:
        session.tts.prewarm()

    @session.on("user_state_changed")
    def on_user_state_changed(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("agent_state_changed")
    def on_agent_state_changed(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("function_tools_executed")
    def on_function_tools_executed(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("metrics_collected")
    def on_metrics_collected(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("error")
    def on_error(event: Any) -> None:
        _record_event(sink, event.type, event.model_dump(mode="json"))

    @session.on("close")
    def on_close(event: Any) -> None:
        _record_event(sink, "session_closed", event.model_dump(mode="json"))
        try:
            write_markdown_report(jsonl_path, report_path)
            logger.info("wrote session report", extra={"report_path": str(report_path)})
        except Exception:
            logger.exception("failed to write session report")

    _record_event(
        sink,
        "session_started",
        {
            "room_name": safe_room_name,
            "eval_run_label": config.eval_run_label,
        },
    )
    _record_event(
        sink,
        "configuration",
        {
            **config.__dict__,
            "availability_start_date": STORE.start_date.isoformat(),
            "availability_horizon_days": STORE.horizon_days,
            "availability_timezone": AVAILABILITY_TIMEZONE,
            "availability_pattern": "two daily slots; Mehta/Rao schedules alternate",
            "phone_number_scope": "India-local",
            "phone_number_expected_digits": PHONE_EXPECTED_DIGITS,
        },
    )
    await session.start(agent=ClinicAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
