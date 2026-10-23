"""Unit tests for Durable Reminders, Timers, and Calendar Engine."""

import datetime
from edith.tasks.reminders import (
    create_reminder,
    list_reminders,
    snooze_reminder,
    complete_reminder,
    dismiss_reminder,
    delete_reminder,
    fire_arrival,
    create_event,
    list_events,
    delete_event,
    to_ics,
    parse_ics,
    get_profile,
    set_profile,
    get_tutorial_state,
    set_tutorial_state,
)


def test_create_and_list_reminder():
    """Verify reminder creation, storage, and retrieval."""
    due = (datetime.datetime.now() + datetime.timedelta(hours=2)).isoformat()
    rem = create_reminder(title="Wash clothes", due_at=due, priority="high")
    assert rem["id"] is not None
    assert rem["title"] == "Wash clothes"
    assert rem["status"] == "pending"

    rems = list_reminders(include_all=True)
    found = [r for r in rems if r["id"] == rem["id"]]
    assert len(found) == 1
    assert found[0]["title"] == "Wash clothes"


def test_snooze_and_complete_reminder():
    """Verify snooze, complete, and recurrence advance."""
    due = datetime.datetime.now().isoformat()
    rem = create_reminder(title="Take vitamins", due_at=due, recurrence="daily")
    rem_id = rem["id"]

    snoozed = snooze_reminder(rem_id, minutes=15)
    assert snoozed is not None
    assert snoozed["status"] == "snoozed"

    completed = complete_reminder(rem_id)
    assert completed is not None
    # Daily recurring reminder should advance and stay active (pending)
    rems = list_reminders(include_all=True)
    updated = next(r for r in rems if r["id"] == rem_id)
    assert updated["status"] == "pending"
    assert updated["due_at"] > due

    # Complete a non-recurring reminder
    one_off = create_reminder(title="One off task", due_at=due, recurrence="none")
    comp_one_off = complete_reminder(one_off["id"])
    assert comp_one_off["status"] == "completed"


def test_manual_arrival_trigger():
    """Verify manual arrival triggers fire correctly."""
    rem = create_reminder(title="Water plants", due_at="2099-01-01T00:00:00", trigger="manual_arrival")
    assert rem["trigger"] == "manual_arrival"

    fired = fire_arrival()
    matched = [r for r in fired if r["id"] == rem["id"]]
    assert len(matched) == 1


def test_calendar_event_yearly_expansion():
    """Verify calendar events expand yearly recurrences across year boundaries."""
    ev = create_event(
        title="Spidey Birthday",
        date="2020-08-10",
        category="birthday",
        recurrence="yearly",
    )
    assert ev["recurrence"] == "yearly"

    # Query 2026-08
    events_2026 = list_events("2026-01-01", "2026-12-31")
    bday_2026 = [e for e in events_2026 if e["id"] == ev["id"]]
    assert len(bday_2026) == 1
    assert bday_2026[0]["occurs"] == "2026-08-10"

    # Query 2027
    events_2027 = list_events("2027-01-01", "2027-12-31")
    bday_2027 = [e for e in events_2027 if e["id"] == ev["id"]]
    assert len(bday_2027) == 1
    assert bday_2027[0]["occurs"] == "2027-08-10"

    delete_event(ev["id"])


def test_ics_export_and_import():
    """Verify ICS serialization and round-trip parsing."""
    ev = create_event(title="Midtown Science Fair", date="2026-04-15", time="14:00")
    ics_text = to_ics([ev])
    assert "BEGIN:VCALENDAR" in ics_text
    assert "SUMMARY:Midtown Science Fair" in ics_text
    assert "DTSTART" in ics_text

    parsed = parse_ics(ics_text)
    assert len(parsed) >= 1
    found = next(p for p in parsed if p["title"] == "Midtown Science Fair")
    assert found["date"] == "2026-04-15"
    assert found["time"] == "14:00"

    delete_event(ev["id"])


def test_profile_and_tutorial_storage():
    """Verify user profile and tutorial checkpoint persistence."""
    orig = get_profile()
    assert "timezone" in orig

    updated = set_profile({"city": "Mumbai", "resourceProfile": "4gb"})
    assert updated["city"] == "Mumbai"
    assert updated["resourceProfile"] == "4gb"

    set_tutorial_state({"lesson_1": True, "lesson_2": True})
    tut = get_tutorial_state()
    assert tut.get("lesson_1") is True
    assert tut.get("lesson_2") is True
