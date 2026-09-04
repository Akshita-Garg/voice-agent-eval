from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

BOOKING_HORIZON_DAYS = 30
AVAILABILITY_TIMEZONE = "Asia/Kolkata"
DAILY_SCHEDULES = (
    (("10:00", "Dr. Mehta"), ("14:30", "Dr. Mehta")),
    (("09:30", "Dr. Rao"), ("16:00", "Dr. Rao")),
)


@dataclass(frozen=True)
class Slot:
    date: str
    time: str
    clinician: str
    visit_type: str


class AppointmentStore:
    """Deterministic in-memory backend for auditable tool-use evaluations."""

    def __init__(
        self,
        *,
        start_date: date | None = None,
        horizon_days: int = BOOKING_HORIZON_DAYS,
    ) -> None:
        if horizon_days < 1:
            raise ValueError("horizon_days must be at least 1")
        india_time = timezone(timedelta(hours=5, minutes=30))
        self.start_date = start_date or datetime.now(india_time).date()
        self.horizon_days = horizon_days
        self._slots = []
        for day_offset in range(1, horizon_days + 1):
            slot_date = self.start_date + timedelta(days=day_offset)
            schedule = DAILY_SCHEDULES[(day_offset - 1) % len(DAILY_SCHEDULES)]
            self._slots.extend(
                Slot(
                    slot_date.isoformat(),
                    slot_time,
                    clinician,
                    "general consultation",
                )
                for slot_time, clinician in schedule
            )
        self._bookings: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def available_slots(self, requested_date: str | None = None) -> list[dict[str, Any]]:
        slots = self._slots
        if requested_date:
            slots = [slot for slot in slots if slot.date == requested_date]
        return [asdict(slot) for slot in slots]

    def book(
        self,
        *,
        patient_name: str,
        phone_number: str,
        requested_date: str,
        requested_time: str,
    ) -> dict[str, Any]:
        with self._lock:
            match = next(
                (
                    slot
                    for slot in self._slots
                    if slot.date == requested_date and slot.time == requested_time
                ),
                None,
            )
            if match is None:
                return {
                    "status": "unavailable",
                    "message": "That slot is no longer available.",
                    "alternatives": self.available_slots(requested_date)[:3],
                }

            self._slots.remove(match)
            booking_id = f"APT-{uuid4().hex[:8].upper()}"
            booking = {
                "status": "confirmed",
                "booking_id": booking_id,
                "patient_name": patient_name,
                "phone_number_last_four": phone_number[-4:],
                **asdict(match),
            }
            self._bookings[booking_id] = booking
            return booking


STORE = AppointmentStore()
