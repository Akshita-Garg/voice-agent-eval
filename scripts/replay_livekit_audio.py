from __future__ import annotations

import argparse
import asyncio
import os
import re
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from livekit import api, rtc

SAMPLE_RATE = 16_000
NUM_CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
FRAME_DURATION_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_DURATION_MS // 1000


@dataclass(frozen=True)
class WavInfo:
    path: Path
    frames: int
    duration_seconds: float


def validate_wav(path: Path) -> WavInfo:
    if not path.exists():
        raise FileNotFoundError(path)
    with wave.open(str(path), "rb") as audio:
        if audio.getframerate() != SAMPLE_RATE:
            raise ValueError(f"{path}: expected {SAMPLE_RATE} Hz")
        if audio.getnchannels() != NUM_CHANNELS:
            raise ValueError(f"{path}: expected mono audio")
        if audio.getsampwidth() != SAMPLE_WIDTH_BYTES:
            raise ValueError(f"{path}: expected 16-bit PCM")
        if audio.getcomptype() != "NONE":
            raise ValueError(f"{path}: expected uncompressed PCM")
        frames = audio.getnframes()
    return WavInfo(path=path, frames=frames, duration_seconds=frames / SAMPLE_RATE)


def _safe_label(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return cleaned[:40] or "audio"


async def _wait_for_agent(room: rtc.Room, timeout_seconds: float) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        participants = list(room.remote_participants.values())
        if participants:
            return participants[0].identity
        await asyncio.sleep(0.1)
    raise TimeoutError("No agent participant joined the room")


async def _publish_wav(source: rtc.AudioSource, info: WavInfo) -> None:
    with wave.open(str(info.path), "rb") as audio:
        while data := audio.readframes(SAMPLES_PER_FRAME):
            samples = len(data) // (SAMPLE_WIDTH_BYTES * NUM_CHANNELS)
            frame = rtc.AudioFrame(
                data=data,
                sample_rate=SAMPLE_RATE,
                num_channels=NUM_CHANNELS,
                samples_per_channel=samples,
            )
            await source.capture_frame(frame)
            await asyncio.sleep(samples / SAMPLE_RATE)
    await source.wait_for_playout()


async def replay_one(
    info: WavInfo,
    *,
    livekit_url: str,
    api_key: str,
    api_secret: str,
    run_label: str,
    greeting_wait_seconds: float,
    response_wait_seconds: float,
) -> str:
    fixture = _safe_label(info.path.stem)
    room_name = f"recorded-{_safe_label(run_label)}-{fixture}-{uuid.uuid4().hex[:6]}"
    identity = f"fixture-{fixture}-{uuid.uuid4().hex[:6]}"
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(f"Recorded fixture: {info.path.name}")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    room = rtc.Room()
    source = rtc.AudioSource(SAMPLE_RATE, NUM_CHANNELS, queue_size_ms=100)
    try:
        await room.connect(livekit_url, token)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        track = rtc.LocalAudioTrack.create_audio_track("recorded-microphone", source)
        await room.local_participant.publish_track(track, options)
        agent_identity = await _wait_for_agent(room, timeout_seconds=15.0)
        print(f"[{info.path.name}] room={room_name} agent={agent_identity}")
        print(f"[{info.path.name}] waiting {greeting_wait_seconds:.1f}s for greeting")
        await asyncio.sleep(greeting_wait_seconds)
        print(f"[{info.path.name}] publishing {info.duration_seconds:.2f}s in real time")
        await _publish_wav(source, info)
        print(f"[{info.path.name}] waiting {response_wait_seconds:.1f}s for response")
        await asyncio.sleep(response_wait_seconds)
    finally:
        await source.aclose()
        await room.disconnect()

    print(f"[{info.path.name}] completed room={room_name}")
    return room_name


async def run(args: argparse.Namespace) -> None:
    load_dotenv()
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]
    fixtures = [validate_wav(path) for path in args.inputs]

    print(f"Run label: {args.run_label}")
    print(f"Fixtures: {len(fixtures)}")
    completed_rooms: list[str] = []
    for fixture in fixtures:
        room = await replay_one(
            fixture,
            livekit_url=livekit_url,
            api_key=api_key,
            api_secret=api_secret,
            run_label=args.run_label,
            greeting_wait_seconds=args.greeting_wait,
            response_wait_seconds=args.response_wait,
        )
        completed_rooms.append(room)
        await asyncio.sleep(2.0)

    print("Completed rooms:")
    for room in completed_rooms:
        print(f"- {room}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish fixed PCM WAV fixtures to fresh LiveKit rooms in real time"
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--greeting-wait", type=float, default=7.0)
    parser.add_argument("--response-wait", type=float, default=15.0)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
