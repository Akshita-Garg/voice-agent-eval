from datetime import date

from src.appointment_store import AppointmentStore


def test_booking_removes_slot() -> None:
    store = AppointmentStore()
    slot = store.available_slots()[0]

    result = store.book(
        patient_name="Test User",
        phone_number="9876543210",
        requested_date=slot["date"],
        requested_time=slot["time"],
    )

    assert result["status"] == "confirmed"
    assert result["phone_number_last_four"] == "3210"
    assert slot not in store.available_slots()


def test_unavailable_slot_returns_alternatives() -> None:
    store = AppointmentStore()

    result = store.book(
        patient_name="Test User",
        phone_number="9876543210",
        requested_date="2099-01-01",
        requested_time="10:00",
    )

    assert result["status"] == "unavailable"
    assert "alternatives" in result


def test_calendar_alternates_the_two_schedules_for_thirty_days() -> None:
    store = AppointmentStore(start_date=date(2026, 9, 4))

    assert [slot["time"] for slot in store.available_slots("2026-09-05")] == [
        "10:00",
        "14:30",
    ]
    assert [slot["time"] for slot in store.available_slots("2026-09-06")] == [
        "09:30",
        "16:00",
    ]
    assert [slot["time"] for slot in store.available_slots("2026-09-15")] == [
        "10:00",
        "14:30",
    ]


def test_calendar_stops_after_the_explicit_horizon() -> None:
    store = AppointmentStore(start_date=date(2026, 9, 4), horizon_days=30)

    assert store.available_slots("2026-10-04")
    assert store.available_slots("2026-10-05") == []
