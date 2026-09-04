"""Make a real, minimal request to Smallest AI's Electron model."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ENDPOINT = "https://api.smallest.ai/waves/v1/chat/completions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test Electron independently of LiveKit.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Reply with exactly: Electron is working.",
        help="Optional prompt to send to Electron.",
    )
    return parser.parse_args()


def load_api_key() -> str:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    api_key = os.getenv("SMALLEST_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SMALLEST_API_KEY is missing from .env")
    return api_key


def request_electron(api_key: str, prompt: str) -> tuple[dict[str, Any], str | None, float]:
    payload = json.dumps(
        {
            "model": "electron",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 40,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30) as response:
        elapsed_ms = (time.perf_counter() - started) * 1000
        body = json.loads(response.read().decode("utf-8"))
        return body, response.headers.get("X-Request-Id"), elapsed_ms


def describe_http_error(error: urllib.error.HTTPError) -> None:
    request_id = error.headers.get("X-Request-Id")
    try:
        body = json.loads(error.read().decode("utf-8"))
        detail = body.get("error", body)
        if isinstance(detail, dict):
            detail = detail.get("message", detail)
    except (UnicodeDecodeError, json.JSONDecodeError):
        detail = "The server returned a non-JSON error response."

    print(f"Electron request failed (HTTP {error.code}).", file=sys.stderr)
    print(f"Reason: {detail}", file=sys.stderr)
    if request_id:
        print(f"Request ID: {request_id}", file=sys.stderr)
    if error.code == 403:
        print(
            "Diagnosis: the API key is valid enough to reach Smallest, but this account "
            "may not have Electron access.",
            file=sys.stderr,
        )


def main() -> int:
    args = parse_args()
    try:
        api_key = load_api_key()
        response, request_id, elapsed_ms = request_electron(api_key, args.prompt)
    except RuntimeError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    except urllib.error.HTTPError as error:
        describe_http_error(error)
        return 1
    except urllib.error.URLError as error:
        print(f"Network error: {error.reason}", file=sys.stderr)
        return 1

    message = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})
    print("Electron request succeeded.")
    print(f"Response: {message}")
    print(f"Round-trip time: {elapsed_ms:.0f} ms")
    if usage:
        print(f"Token usage: {usage.get('total_tokens', 'unknown')} total")
    if request_id:
        print(f"Request ID: {request_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
